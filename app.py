from __future__ import annotations

import re
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from google.oauth2.service_account import Credentials

# =====================================================
# GÜNDAYS HOME - SİPARİŞ TAKİP SİSTEMİ
# Tek dosya Streamlit uygulaması.
# Google Sheets okuma mantığı: tek batch read + cache.
# =====================================================

DEFAULT_SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
APP_TITLE = "Gündays Home Sipariş Takip"
CACHE_TTL_SECONDS = 120
MAX_ROWS_PER_SHEET = 10000

SCHEMA: Dict[str, List[str]] = {
    "Dashboard": [
        "Metrik", "Deger", "Aciklama"
    ],
    "Firmalar": [
        "Firma_ID", "Firma_Adi", "Yetkili", "Telefon", "Email", "Adres", "Il", "Ilce",
        "Vergi_Dairesi", "VKN_TCKN", "Durum", "Kayit_Tarihi", "Not"
    ],
    "Urunler": [
        "Urun_ID", "Urun_Adi", "Kategori", "Renk", "Birim", "Birim_Fiyat", "KDV_Orani",
        "Durum", "Stok_Kodu", "Not"
    ],
    "Siparisler": [
        "Siparis_ID", "Tarih", "Firma_ID", "Firma_Adi", "Durum", "Teslim_Tarihi", "Sevk_Adresi",
        "Ara_Toplam", "KDV_Tutari", "Genel_Toplam", "Odenen", "Kalan", "Odeme_Durumu",
        "Not", "Olusturma_Tarihi"
    ],
    "Siparis_Kalemleri": [
        "Kalem_ID", "Siparis_ID", "Urun_ID", "Urun_Adi", "Miktar", "Birim_Fiyat", "KDV_Orani",
        "Ara_Toplam", "KDV_Tutari", "Satir_Toplami", "Not"
    ],
    "Odemeler": [
        "Odeme_ID", "Tarih", "Siparis_ID", "Firma_ID", "Firma_Adi", "Odeme_Tipi", "Tutar", "Aciklama"
    ],
    "Listeler": [
        "Durum_Tipleri", "Odeme_Tipleri", "Urun_Kategorileri", "Birimler"
    ],
    "Kullanim": [
        "Tarih", "Islem", "Kullanici", "Detay"
    ],
    "Kullanicilar": [
        "Kullanici_ID", "Ad_Soyad", "Email", "Rol", "Durum"
    ],
}

DEFAULT_LIST_ROWS = [
    ["Hazırlanıyor", "Nakit", "Dilsiz Uşak", "Adet"],
    ["Onaylandı", "Havale/EFT", "Mobilya", "Takım"],
    ["Üretimde", "Kredi Kartı", "Aksesuar", "Paket"],
    ["Sevke Hazır", "Çek/Senet", "Diğer", "Koli"],
    ["Teslim Edildi", "Diğer", "", "Metre"],
    ["İptal", "", "", "Kg"],
]

ALIASES: Dict[str, List[str]] = {
    "Firma_ID": ["firma id", "firma_id", "firma kodu", "firma no", "id"],
    "Firma_Adi": ["firma adı", "firma adi", "firma_adi", "firma", "cari", "cari adı", "cari adi", "müşteri", "musteri"],
    "Urun_ID": ["ürün id", "urun id", "urun_id", "ürün_id", "ürün kodu", "urun kodu", "stok kodu"],
    "Urun_Adi": ["ürün adı", "urun adi", "urun_adi", "ürün", "urun", "ürün ismi", "urun ismi"],
    "Siparis_ID": ["sipariş id", "siparis id", "siparis_id", "sipariş_id", "sipariş no", "siparis no"],
    "Kalem_ID": ["kalem id", "kalem_id", "satır id", "satir id"],
    "Odeme_ID": ["ödeme id", "odeme id", "odeme_id", "ödeme_id"],
    "Tarih": ["tarih", "sipariş tarihi", "siparis tarihi"],
    "Durum": ["durum", "status", "sipariş durumu", "siparis durumu"],
    "Birim_Fiyat": ["birim fiyat", "birim_fiyat", "fiyat", "satış fiyatı", "satis fiyati"],
    "KDV_Orani": ["kdv", "kdv oranı", "kdv orani", "kdv_orani", "kdv %"],
    "Genel_Toplam": ["genel toplam", "genel_toplam", "toplam", "toplam tutar", "toplam_tutar", "ciro"],
    "Satir_Toplami": ["satır toplamı", "satir toplami", "satir_toplami", "satır_toplamı", "toplam"],
    "Odenen": ["ödenen", "odenen", "odenmiş", "ödenmiş"],
    "Kalan": ["kalan", "bakiye"],
    "Tutar": ["tutar", "ödeme tutarı", "odeme tutari"],
}

# -------------------------------
# Genel yardımcılar
# -------------------------------

def normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    tr_map = str.maketrans("çğıöşüİ", "cgiosui")
    text = text.translate(tr_map)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def date_text(d: Any) -> str:
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    return str(d or "")


def money(value: Any) -> str:
    n = to_float(value)
    return f"{n:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace("TL", "").replace("₺", "").replace("%", "").strip()
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return 0.0
    # Türkçe sayı: 12.345,67 -> 12345.67
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def clean_empty_rows(df: pd.DataFrame, required_col: Optional[str] = None) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy().fillna("")
    if required_col and required_col in df.columns:
        df = df[df[required_col].astype(str).str.strip() != ""]
    else:
        df = df[df.apply(lambda row: any(str(x).strip() for x in row), axis=1)]
    return df.reset_index(drop=True)


def col_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def next_id(df: pd.DataFrame, column: str, prefix: str) -> str:
    max_num = 0
    if column in df.columns:
        for raw in df[column].astype(str).tolist():
            nums = re.findall(r"\d+", raw)
            if nums:
                max_num = max(max_num, int(nums[-1]))
    return f"{prefix}-{max_num + 1:05d}"


def find_header_alias_map(actual_headers: List[str], expected_headers: List[str]) -> Dict[str, str]:
    actual_norm_to_name = {normalize_key(h): h for h in actual_headers if str(h).strip()}
    rename_map: Dict[str, str] = {}
    for expected in expected_headers:
        candidates = [expected] + ALIASES.get(expected, [])
        for candidate in candidates:
            key = normalize_key(candidate)
            if key in actual_norm_to_name:
                rename_map[actual_norm_to_name[key]] = expected
                break
    return rename_map


# -------------------------------
# Google Sheets bağlantısı
# -------------------------------

def get_secret_value(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        try:
            val = st.secrets.get(name)
        except Exception:
            val = None
        if val:
            return str(val)
    return default


def get_spreadsheet_id() -> str:
    return get_secret_value("SPREADSHEET_ID", "spreadsheet_id", default=DEFAULT_SPREADSHEET_ID) or DEFAULT_SPREADSHEET_ID


def get_service_account_info() -> Dict[str, Any]:
    # Streamlit Cloud secrets içinde en sağlıklı format:
    # [gcp_service_account]
    # type = "service_account"
    for section_name in ["gcp_service_account", "service_account", "google_service_account"]:
        try:
            if section_name in st.secrets:
                return dict(st.secrets[section_name])
        except Exception:
            pass

    # Alternatif: tüm servis hesabı alanları root seviyede ise.
    required = [
        "type", "project_id", "private_key_id", "private_key", "client_email", "client_id",
        "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    info = {}
    for key in required:
        try:
            if key in st.secrets:
                info[key] = st.secrets[key]
        except Exception:
            pass
    if all(k in info for k in required):
        return dict(info)

    raise RuntimeError("Streamlit Secrets içinde Google service account bilgisi bulunamadı.")


@st.cache_resource(show_spinner=False)
def get_gspread_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = get_service_account_info()
    if "private_key" in info:
        # Streamlit secrets bazen \n karakterlerini düz metin saklar.
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n")
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_spreadsheet() -> gspread.Spreadsheet:
    client = get_gspread_client()
    return client.open_by_key(get_spreadsheet_id())


def run_google_call(fn, *args, retries: int = 4, **kwargs):
    delay = 1.0
    last_error = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except APIError as exc:
            last_error = exc
            msg = str(exc)
            # 429 quota veya 5xx geçici hatalarda bekle.
            if "429" in msg or "Quota exceeded" in msg or "500" in msg or "503" in msg:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise last_error


# -------------------------------
# Sheet okuma/yazma
# -------------------------------

def dataframe_from_values(sheet_name: str, values: List[List[Any]]) -> pd.DataFrame:
    expected = SCHEMA[sheet_name]
    if not values:
        return pd.DataFrame(columns=expected)

    header = [str(x).strip() for x in values[0]]
    rows = values[1:]
    width = max(len(header), len(expected))
    header = header + [f"Ek_{i}" for i in range(len(header) + 1, width + 1)]

    normalized_rows = []
    for row in rows:
        row = list(row) + [""] * (width - len(row))
        normalized_rows.append(row[:width])

    df = pd.DataFrame(normalized_rows, columns=header[:width])
    rename_map = find_header_alias_map(list(df.columns), expected)
    df = df.rename(columns=rename_map)

    for col in expected:
        if col not in df.columns:
            df[col] = ""

    # Beklenen kolonları öne al, ekstra kolonları sona bırak.
    extra_cols = [c for c in df.columns if c not in expected]
    df = df[expected + extra_cols]
    return clean_empty_rows(df)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Google Sheets verileri okunuyor...")
def load_all_tables(cache_buster: int = 0) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
    ss = get_spreadsheet()
    ranges = [f"'{sheet}'!A1:Z{MAX_ROWS_PER_SHEET}" for sheet in SCHEMA]
    errors: Dict[str, str] = {}
    tables: Dict[str, pd.DataFrame] = {name: pd.DataFrame(columns=cols) for name, cols in SCHEMA.items()}

    try:
        response = run_google_call(ss.values_batch_get, ranges=ranges)
        value_ranges = response.get("valueRanges", [])
    except Exception as exc:
        # Batch tamamen patlarsa ekranı düşürmeyelim.
        for name in SCHEMA:
            errors[name] = str(exc)
        return tables, errors

    for sheet_name, vr in zip(SCHEMA.keys(), value_ranges):
        try:
            tables[sheet_name] = dataframe_from_values(sheet_name, vr.get("values", []))
        except Exception as exc:
            errors[sheet_name] = str(exc)
            tables[sheet_name] = pd.DataFrame(columns=SCHEMA[sheet_name])
    return tables, errors


def get_tables() -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
    return load_all_tables(st.session_state.get("cache_buster", 0))


def refresh_data() -> None:
    st.session_state["cache_buster"] = st.session_state.get("cache_buster", 0) + 1
    load_all_tables.clear()


def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    ss = get_spreadsheet()
    return run_google_call(ss.worksheet, sheet_name)


def append_rows(sheet_name: str, row_dicts: List[Dict[str, Any]]) -> None:
    if not row_dicts:
        return
    ws = get_worksheet(sheet_name)
    headers = SCHEMA[sheet_name]
    rows = [[row.get(col, "") for col in headers] for row in row_dicts]
    run_google_call(ws.append_rows, rows, value_input_option="USER_ENTERED")


def append_row(sheet_name: str, row_dict: Dict[str, Any]) -> None:
    append_rows(sheet_name, [row_dict])


def update_order_payment_status(order_id: str, new_paid_total: float, order_total: float) -> None:
    tables, _ = get_tables()
    orders = tables["Siparisler"].copy()
    if orders.empty or "Siparis_ID" not in orders.columns:
        return
    match = orders.index[orders["Siparis_ID"].astype(str) == str(order_id)].tolist()
    if not match:
        return
    df_index = match[0]
    sheet_row = df_index + 2  # 1. satır header, dataframe index 0 => sheet row 2
    kalan = max(order_total - new_paid_total, 0)
    odeme_durumu = "Ödendi" if kalan <= 0.01 else ("Kısmi Ödendi" if new_paid_total > 0 else "Ödenmedi")

    headers = SCHEMA["Siparisler"]
    c_odenen = col_letter(headers.index("Odenen") + 1)
    c_kalan = col_letter(headers.index("Kalan") + 1)
    c_odeme = col_letter(headers.index("Odeme_Durumu") + 1)
    ws = get_worksheet("Siparisler")
    run_google_call(
        ws.update,
        f"{c_odenen}{sheet_row}:{c_odeme}{sheet_row}",
        [[round(new_paid_total, 2), round(kalan, 2), odeme_durumu]],
        value_input_option="USER_ENTERED",
    )


def ensure_sheet_structure() -> Tuple[List[str], List[str]]:
    """Eksik sekmeleri oluşturur, headerları sabitler. Butonla manuel çalışır."""
    ss = get_spreadsheet()
    existing_titles = [ws.title for ws in run_google_call(ss.worksheets)]
    created: List[str] = []
    updated: List[str] = []

    for sheet_name, headers in SCHEMA.items():
        if sheet_name not in existing_titles:
            ws = run_google_call(ss.add_worksheet, title=sheet_name, rows=MAX_ROWS_PER_SHEET, cols=max(26, len(headers)))
            created.append(sheet_name)
        else:
            ws = run_google_call(ss.worksheet, sheet_name)

        # Headerları her zaman A1'den itibaren net yazıyoruz.
        end_col = col_letter(len(headers))
        run_google_call(ws.update, f"A1:{end_col}1", [headers], value_input_option="USER_ENTERED")
        updated.append(sheet_name)

        if sheet_name == "Listeler":
            current = run_google_call(ws.get, f"A2:D20")
            has_any = any(any(str(cell).strip() for cell in row) for row in current)
            if not has_any:
                run_google_call(ws.update, "A2:D7", DEFAULT_LIST_ROWS, value_input_option="USER_ENTERED")

    refresh_data()
    return created, updated


# -------------------------------
# İş mantığı
# -------------------------------

def active_options(df: pd.DataFrame, id_col: str, name_col: str, durum_col: str = "Durum") -> List[str]:
    if df.empty or id_col not in df.columns or name_col not in df.columns:
        return []
    d = df.copy().fillna("")
    if durum_col in d.columns:
        d = d[~d[durum_col].astype(str).str.lower().str.contains("pasif|iptal", na=False)]
    options = []
    for _, row in d.iterrows():
        rid = str(row.get(id_col, "")).strip()
        name = str(row.get(name_col, "")).strip()
        if rid and name:
            options.append(f"{rid} | {name}")
    return options


def parse_option_id(option: str) -> str:
    return str(option).split(" | ")[0].strip() if option else ""


def get_row_by_id(df: pd.DataFrame, id_col: str, id_value: str) -> Optional[pd.Series]:
    if df.empty or id_col not in df.columns:
        return None
    found = df[df[id_col].astype(str) == str(id_value)]
    if found.empty:
        return None
    return found.iloc[0]


def orders_with_live_payments(orders: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    if orders.empty:
        return orders.copy()
    out = orders.copy().fillna("")
    out["Genel_Toplam_Num"] = out["Genel_Toplam"].apply(to_float) if "Genel_Toplam" in out.columns else 0.0

    paid_map: Dict[str, float] = {}
    if not payments.empty and "Siparis_ID" in payments.columns and "Tutar" in payments.columns:
        temp = payments.copy()
        temp["Tutar_Num"] = temp["Tutar"].apply(to_float)
        paid_map = temp.groupby("Siparis_ID")["Tutar_Num"].sum().to_dict()

    out["Odenen_Canli"] = out["Siparis_ID"].map(lambda x: paid_map.get(str(x), 0.0))
    out["Kalan_Canli"] = out["Genel_Toplam_Num"] - out["Odenen_Canli"]
    out["Odeme_Durumu_Canli"] = out.apply(
        lambda r: "Ödendi" if r["Kalan_Canli"] <= 0.01 else ("Kısmi Ödendi" if r["Odenen_Canli"] > 0 else "Ödenmedi"),
        axis=1,
    )
    return out


# -------------------------------
# UI
# -------------------------------

st.set_page_config(page_title=APP_TITLE, page_icon="📦", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
    div[data-testid="stMetric"] {background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 14px; border-radius: 14px;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "cache_buster" not in st.session_state:
    st.session_state["cache_buster"] = 0

with st.sidebar:
    st.title("📦 Gündays Home")
    st.caption("Sipariş takip sistemi")
    page = st.radio(
        "Menü",
        ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Ödemeler", "Sheet Kurulum"],
        label_visibility="collapsed",
    )
    if st.button("🔄 Verileri yenile", use_container_width=True):
        refresh_data()
        st.rerun()
    st.caption(f"Cache: {CACHE_TTL_SECONDS} sn | Tek batch okuma")

st.title(APP_TITLE)

tables, errors = get_tables()

if errors:
    with st.expander("⚠️ Google Sheets okuma uyarıları", expanded=True):
        st.warning("Bazı sekmeler okunamadı. 429 görüyorsan 1-2 dakika bekleyip Verileri yenile butonuna bas. Bu sürüm eski koddaki sürekli okuma sorununu azaltmak için tek batch okuma kullanır.")
        for sheet_name, err in errors.items():
            st.code(f"{sheet_name}: {err}")

firmalar = tables["Firmalar"]
products = tables["Urunler"]
orders = tables["Siparisler"]
lines = tables["Siparis_Kalemleri"]
payments = tables["Odemeler"]

# ---------- Dashboard ----------
if page == "Dashboard":
    st.subheader("Genel Durum")

    live_orders = orders_with_live_payments(orders, payments)
    total_revenue = 0.0
    if not live_orders.empty and "Genel_Toplam_Num" in live_orders.columns:
        total_revenue = live_orders["Genel_Toplam_Num"].sum()
    elif not lines.empty and "Satir_Toplami" in lines.columns:
        total_revenue = lines["Satir_Toplami"].apply(to_float).sum()

    total_paid = payments["Tutar"].apply(to_float).sum() if not payments.empty and "Tutar" in payments.columns else 0.0
    total_balance = max(total_revenue - total_paid, 0)
    active_order_count = 0
    if not orders.empty and "Durum" in orders.columns:
        active_order_count = len(orders[~orders["Durum"].astype(str).str.lower().str.contains("teslim|iptal", na=False)])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro", money(total_revenue))
    c2.metric("Tahsilat", money(total_paid))
    c3.metric("Kalan Bakiye", money(total_balance))
    c4.metric("Aktif Sipariş", active_order_count)

    st.divider()
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown("### Son Siparişler")
        if live_orders.empty:
            st.info("Henüz sipariş yok.")
        else:
            show_cols = [c for c in ["Siparis_ID", "Tarih", "Firma_Adi", "Durum", "Genel_Toplam", "Odenen_Canli", "Kalan_Canli", "Odeme_Durumu_Canli"] if c in live_orders.columns]
            display = live_orders[show_cols].tail(20).iloc[::-1].copy()
            if "Odenen_Canli" in display.columns:
                display["Odenen_Canli"] = display["Odenen_Canli"].apply(money)
            if "Kalan_Canli" in display.columns:
                display["Kalan_Canli"] = display["Kalan_Canli"].apply(money)
            st.dataframe(display, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Durum Dağılımı")
        if not orders.empty and "Durum" in orders.columns:
            status_counts = orders["Durum"].replace("", "Boş").value_counts().reset_index()
            status_counts.columns = ["Durum", "Adet"]
            st.bar_chart(status_counts.set_index("Durum"))
        else:
            st.info("Durum verisi yok.")

# ---------- Yeni Sipariş ----------
elif page == "Yeni Sipariş":
    st.subheader("Yeni Sipariş Oluştur")

    firma_options = active_options(firmalar, "Firma_ID", "Firma_Adi")
    product_options = active_options(products, "Urun_ID", "Urun_Adi")

    if not firma_options:
        st.error("Önce Firmalar sekmesine aktif firma eklemen gerekiyor.")
    elif not product_options:
        st.error("Önce Ürünler sekmesine aktif ürün eklemen gerekiyor.")
    else:
        with st.form("new_order_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            sip_tarih = c1.date_input("Sipariş Tarihi", value=date.today())
            selected_firma = c2.selectbox("Firma", firma_options)
            durum = c3.selectbox("Durum", ["Hazırlanıyor", "Onaylandı", "Üretimde", "Sevke Hazır", "Teslim Edildi", "İptal"])

            c4, c5 = st.columns([1, 2])
            teslim_tarihi = c4.date_input("Teslim Tarihi", value=date.today())
            sevk_adresi = c5.text_input("Sevk Adresi")
            note = st.text_area("Sipariş Notu", height=80)

            line_count = st.number_input("Sipariş kalem sayısı", min_value=1, max_value=20, value=1, step=1)
            kalem_rows = []
            st.markdown("#### Ürün Kalemleri")
            for i in range(int(line_count)):
                cols = st.columns([2.4, 0.8, 1, 0.8, 1.2])
                selected_product = cols[0].selectbox(f"Ürün {i+1}", product_options, key=f"prod_{i}")
                product_id = parse_option_id(selected_product)
                prod_row = get_row_by_id(products, "Urun_ID", product_id)
                default_price = to_float(prod_row.get("Birim_Fiyat", 0)) if prod_row is not None else 0.0
                default_kdv = to_float(prod_row.get("KDV_Orani", 20)) if prod_row is not None else 20.0

                qty = cols[1].number_input("Miktar", min_value=0.0, value=1.0, step=1.0, key=f"qty_{i}")
                price = cols[2].number_input("Birim Fiyat", min_value=0.0, value=float(default_price), step=100.0, key=f"price_{i}")
                kdv = cols[3].number_input("KDV %", min_value=0.0, max_value=100.0, value=float(default_kdv), step=1.0, key=f"kdv_{i}")
                line_note = cols[4].text_input("Not", key=f"line_note_{i}")

                product_name = str(prod_row.get("Urun_Adi", "")) if prod_row is not None else ""
                ara = qty * price
                kdv_tutari = ara * (kdv / 100)
                toplam = ara + kdv_tutari
                kalem_rows.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "qty": qty,
                    "price": price,
                    "kdv": kdv,
                    "ara": ara,
                    "kdv_tutari": kdv_tutari,
                    "toplam": toplam,
                    "note": line_note,
                })

            ara_toplam = sum(x["ara"] for x in kalem_rows)
            kdv_toplam = sum(x["kdv_tutari"] for x in kalem_rows)
            genel_toplam = sum(x["toplam"] for x in kalem_rows)

            st.info(f"Ara Toplam: {money(ara_toplam)} | KDV: {money(kdv_toplam)} | Genel Toplam: {money(genel_toplam)}")
            submitted = st.form_submit_button("✅ Siparişi Kaydet", use_container_width=True)

        if submitted:
            valid_lines = [x for x in kalem_rows if x["product_id"] and x["qty"] > 0]
            firma_id = parse_option_id(selected_firma)
            firma_row = get_row_by_id(firmalar, "Firma_ID", firma_id)
            firma_name = str(firma_row.get("Firma_Adi", "")) if firma_row is not None else ""

            if not valid_lines:
                st.error("En az 1 ürün kalemi girmelisin.")
            else:
                try:
                    siparis_id = next_id(orders, "Siparis_ID", "SIP")
                    order_row = {
                        "Siparis_ID": siparis_id,
                        "Tarih": date_text(sip_tarih),
                        "Firma_ID": firma_id,
                        "Firma_Adi": firma_name,
                        "Durum": durum,
                        "Teslim_Tarihi": date_text(teslim_tarihi),
                        "Sevk_Adresi": sevk_adresi,
                        "Ara_Toplam": round(ara_toplam, 2),
                        "KDV_Tutari": round(kdv_toplam, 2),
                        "Genel_Toplam": round(genel_toplam, 2),
                        "Odenen": 0,
                        "Kalan": round(genel_toplam, 2),
                        "Odeme_Durumu": "Ödenmedi",
                        "Not": note,
                        "Olusturma_Tarihi": now_text(),
                    }
                    line_rows = []
                    next_line_num_base = next_id(lines, "Kalem_ID", "KLM")
                    base_num = int(re.findall(r"\d+", next_line_num_base)[-1])
                    for offset, item in enumerate(valid_lines):
                        line_rows.append({
                            "Kalem_ID": f"KLM-{base_num + offset:05d}",
                            "Siparis_ID": siparis_id,
                            "Urun_ID": item["product_id"],
                            "Urun_Adi": item["product_name"],
                            "Miktar": item["qty"],
                            "Birim_Fiyat": round(item["price"], 2),
                            "KDV_Orani": item["kdv"],
                            "Ara_Toplam": round(item["ara"], 2),
                            "KDV_Tutari": round(item["kdv_tutari"], 2),
                            "Satir_Toplami": round(item["toplam"], 2),
                            "Not": item["note"],
                        })
                    append_row("Siparisler", order_row)
                    append_rows("Siparis_Kalemleri", line_rows)
                    append_row("Kullanim", {"Tarih": now_text(), "Islem": "Sipariş oluşturuldu", "Kullanici": "Streamlit", "Detay": siparis_id})
                    refresh_data()
                    st.success(f"Sipariş kaydedildi: {siparis_id}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Sipariş kaydedilemedi: {exc}")

# ---------- Siparişler ----------
elif page == "Siparişler":
    st.subheader("Sipariş Listesi")
    live_orders = orders_with_live_payments(orders, payments)

    if live_orders.empty:
        st.info("Henüz sipariş yok.")
    else:
        c1, c2, c3 = st.columns(3)
        search = c1.text_input("Firma / Sipariş Ara")
        status = c2.selectbox("Durum", ["Tümü"] + sorted([x for x in live_orders["Durum"].dropna().astype(str).unique() if x]))
        pay_status = c3.selectbox("Ödeme", ["Tümü", "Ödenmedi", "Kısmi Ödendi", "Ödendi"])

        df = live_orders.copy()
        if search:
            s = search.lower()
            df = df[df.apply(lambda r: s in " ".join([str(r.get("Siparis_ID", "")), str(r.get("Firma_Adi", ""))]).lower(), axis=1)]
        if status != "Tümü":
            df = df[df["Durum"].astype(str) == status]
        if pay_status != "Tümü":
            df = df[df["Odeme_Durumu_Canli"].astype(str) == pay_status]

        display = df.copy()
        for col in ["Genel_Toplam_Num", "Odenen_Canli", "Kalan_Canli"]:
            if col in display.columns:
                display[col] = display[col].apply(money)
        show_cols = [c for c in ["Siparis_ID", "Tarih", "Firma_Adi", "Durum", "Genel_Toplam_Num", "Odenen_Canli", "Kalan_Canli", "Odeme_Durumu_Canli", "Not"] if c in display.columns]
        st.dataframe(display[show_cols].iloc[::-1], use_container_width=True, hide_index=True)

        st.markdown("### Sipariş Detayı")
        selected_order = st.selectbox("Sipariş seç", df["Siparis_ID"].astype(str).tolist() if not df.empty else [])
        if selected_order:
            detail_lines = lines[lines["Siparis_ID"].astype(str) == selected_order].copy() if not lines.empty else pd.DataFrame()
            detail_payments = payments[payments["Siparis_ID"].astype(str) == selected_order].copy() if not payments.empty else pd.DataFrame()
            st.markdown("#### Kalemler")
            st.dataframe(detail_lines, use_container_width=True, hide_index=True)
            st.markdown("#### Ödemeler")
            st.dataframe(detail_payments, use_container_width=True, hide_index=True)

# ---------- Firmalar ----------
elif page == "Firmalar":
    st.subheader("Firmalar")
    with st.expander("➕ Yeni firma ekle", expanded=False):
        with st.form("firma_form"):
            c1, c2, c3 = st.columns(3)
            firma_adi = c1.text_input("Firma Adı *")
            yetkili = c2.text_input("Yetkili")
            telefon = c3.text_input("Telefon")
            c4, c5, c6 = st.columns(3)
            email = c4.text_input("Email")
            il = c5.text_input("İl")
            ilce = c6.text_input("İlçe")
            adres = st.text_area("Adres")
            c7, c8, c9 = st.columns(3)
            vergi_dairesi = c7.text_input("Vergi Dairesi")
            vkn = c8.text_input("VKN/TCKN")
            durum = c9.selectbox("Durum", ["Aktif", "Pasif"])
            note = st.text_area("Not", key="firma_note")
            if st.form_submit_button("Firmayı kaydet", use_container_width=True):
                if not firma_adi.strip():
                    st.error("Firma adı zorunlu.")
                else:
                    try:
                        firma_id = next_id(firmalar, "Firma_ID", "F")
                        append_row("Firmalar", {
                            "Firma_ID": firma_id,
                            "Firma_Adi": firma_adi,
                            "Yetkili": yetkili,
                            "Telefon": telefon,
                            "Email": email,
                            "Adres": adres,
                            "Il": il,
                            "Ilce": ilce,
                            "Vergi_Dairesi": vergi_dairesi,
                            "VKN_TCKN": vkn,
                            "Durum": durum,
                            "Kayit_Tarihi": now_text(),
                            "Not": note,
                        })
                        append_row("Kullanim", {"Tarih": now_text(), "Islem": "Firma eklendi", "Kullanici": "Streamlit", "Detay": firma_id})
                        refresh_data()
                        st.success(f"Firma eklendi: {firma_id}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Firma eklenemedi: {exc}")
    st.dataframe(firmalar.iloc[::-1] if not firmalar.empty else firmalar, use_container_width=True, hide_index=True)

# ---------- Ürünler ----------
elif page == "Ürünler":
    st.subheader("Ürünler")
    with st.expander("➕ Yeni ürün ekle", expanded=False):
        with st.form("urun_form"):
            c1, c2, c3 = st.columns(3)
            urun_adi = c1.text_input("Ürün Adı *")
            kategori = c2.text_input("Kategori", value="Dilsiz Uşak")
            renk = c3.text_input("Renk")
            c4, c5, c6, c7 = st.columns(4)
            birim = c4.selectbox("Birim", ["Adet", "Takım", "Paket", "Koli", "Metre", "Kg"])
            fiyat = c5.number_input("Birim Fiyat", min_value=0.0, value=0.0, step=100.0)
            kdv = c6.number_input("KDV %", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
            durum = c7.selectbox("Durum", ["Aktif", "Pasif"])
            stok = st.text_input("Stok Kodu")
            note = st.text_area("Not", key="urun_note")
            if st.form_submit_button("Ürünü kaydet", use_container_width=True):
                if not urun_adi.strip():
                    st.error("Ürün adı zorunlu.")
                else:
                    try:
                        urun_id = next_id(products, "Urun_ID", "U")
                        append_row("Urunler", {
                            "Urun_ID": urun_id,
                            "Urun_Adi": urun_adi,
                            "Kategori": kategori,
                            "Renk": renk,
                            "Birim": birim,
                            "Birim_Fiyat": round(fiyat, 2),
                            "KDV_Orani": kdv,
                            "Durum": durum,
                            "Stok_Kodu": stok,
                            "Not": note,
                        })
                        append_row("Kullanim", {"Tarih": now_text(), "Islem": "Ürün eklendi", "Kullanici": "Streamlit", "Detay": urun_id})
                        refresh_data()
                        st.success(f"Ürün eklendi: {urun_id}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Ürün eklenemedi: {exc}")
    st.dataframe(products.iloc[::-1] if not products.empty else products, use_container_width=True, hide_index=True)

# ---------- Ödemeler ----------
elif page == "Ödemeler":
    st.subheader("Ödemeler")
    live_orders = orders_with_live_payments(orders, payments)
    if live_orders.empty:
        st.info("Ödeme girmek için önce sipariş oluşturmalısın.")
    else:
        open_df = live_orders[live_orders["Kalan_Canli"] > 0.01].copy()
        if open_df.empty:
            open_df = live_orders.copy()
        open_df["Option"] = open_df.apply(lambda r: f"{r['Siparis_ID']} | {r['Firma_Adi']} | Kalan: {money(r['Kalan_Canli'])}", axis=1)
        with st.form("payment_form"):
            c1, c2, c3 = st.columns(3)
            odeme_tarihi = c1.date_input("Ödeme Tarihi", value=date.today())
            selected_order = c2.selectbox("Sipariş", open_df["Option"].tolist())
            odeme_tipi = c3.selectbox("Ödeme Tipi", ["Nakit", "Havale/EFT", "Kredi Kartı", "Çek/Senet", "Diğer"])
            tutar = st.number_input("Tutar", min_value=0.0, value=0.0, step=100.0)
            aciklama = st.text_area("Açıklama")
            if st.form_submit_button("Ödemeyi Kaydet", use_container_width=True):
                if tutar <= 0:
                    st.error("Tutar 0'dan büyük olmalı.")
                else:
                    try:
                        siparis_id = parse_option_id(selected_order)
                        order_row = get_row_by_id(live_orders, "Siparis_ID", siparis_id)
                        firma_id = str(order_row.get("Firma_ID", "")) if order_row is not None else ""
                        firma_name = str(order_row.get("Firma_Adi", "")) if order_row is not None else ""
                        order_total = to_float(order_row.get("Genel_Toplam", 0)) if order_row is not None else 0.0
                        current_paid = to_float(order_row.get("Odenen_Canli", 0)) if order_row is not None else 0.0
                        new_paid_total = current_paid + tutar
                        odeme_id = next_id(payments, "Odeme_ID", "ODE")
                        append_row("Odemeler", {
                            "Odeme_ID": odeme_id,
                            "Tarih": date_text(odeme_tarihi),
                            "Siparis_ID": siparis_id,
                            "Firma_ID": firma_id,
                            "Firma_Adi": firma_name,
                            "Odeme_Tipi": odeme_tipi,
                            "Tutar": round(tutar, 2),
                            "Aciklama": aciklama,
                        })
                        update_order_payment_status(siparis_id, new_paid_total, order_total)
                        append_row("Kullanim", {"Tarih": now_text(), "Islem": "Ödeme eklendi", "Kullanici": "Streamlit", "Detay": f"{odeme_id} / {siparis_id}"})
                        refresh_data()
                        st.success(f"Ödeme kaydedildi: {odeme_id}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Ödeme kaydedilemedi: {exc}")
        st.dataframe(payments.iloc[::-1] if not payments.empty else payments, use_container_width=True, hide_index=True)

# ---------- Sheet Kurulum ----------
elif page == "Sheet Kurulum":
    st.subheader("Google Sheets Kurulum ve Kontrol")
    st.markdown(
        """
        Bu sayfa sistemi sıfırdan sabitlemek için var. Eski otomatik başlık arama mantığı kaldırıldı.
        Kod artık aşağıdaki sabit sekme ve kolon şemasına göre çalışıyor.
        """
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("🧱 Sheet yapısını oluştur / onar", type="primary", use_container_width=True):
            try:
                created, updated = ensure_sheet_structure()
                st.success("Sheet yapısı hazırlandı.")
                if created:
                    st.write("Oluşturulan sekmeler:", ", ".join(created))
                st.write("Güncellenen sekmeler:", ", ".join(updated))
            except Exception as exc:
                st.error(f"Sheet yapısı hazırlanamadı: {exc}")
    with c2:
        st.info("Bu işlem sekmelerin 1. satırına doğru başlıkları yazar. Alt satırlardaki kayıtları silmez. Yine de büyük değişiklikten önce Google Sheet'in bir kopyasını almak mantıklı.")

    st.markdown("### Beklenen sekme ve kolonlar")
    for sheet_name, headers in SCHEMA.items():
        with st.expander(sheet_name, expanded=False):
            st.code(" | ".join(headers))

    st.markdown("### Mevcut veri sayıları")
    counts = []
    for sheet_name, df in tables.items():
        counts.append({"Sekme": sheet_name, "Satır Sayısı": len(df), "Kolon Sayısı": len(df.columns)})
    st.dataframe(pd.DataFrame(counts), use_container_width=True, hide_index=True)
