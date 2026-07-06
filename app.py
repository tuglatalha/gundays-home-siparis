from __future__ import annotations

import re
import uuid
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Tuple

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# =============================
# GÜNDAY'S CARİ TAKİP - STREAMLIT
# Google Sheet ID: Kullanıcının oluşturduğu "CARİ TAKİPP" dosyası
# =============================

DEFAULT_SPREADSHEET_ID = "1vIWF8SNBxS1pt47bmnvmsbxh0r-4q-5HweIkIDT0aZw"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WORKSHEETS = {
    "hareketler": "CARI_HAREKETLER",
    "firmalar": "FIRMALAR",
    "urunler": "URUNLER",
    "ayarlar": "AYARLAR",
    "notlar": "CARI_NOTLARI",
}

HAREKET_COLUMNS = [
    "ID",
    "Tarih",
    "Cari",
    "Islem_Tipi",
    "Urun",
    "Renk",
    "Adet",
    "Birim_Fiyat",
    "Tutar",
    "Odeme_Turu",
    "Tahsil_Edilen",
    "Kalan",
    "Odeme_Tarihi",
    "Not",
    "Ek_Not",
    "Kayit_Zamani",
    "Kullanici",
]

NOT_COLUMNS = [
    "ID",
    "Tarih",
    "Cari",
    "Not_Tipi",
    "Not_Detayi",
    "Hatirlatma_Tarihi",
    "Durum",
    "Kullanici",
    "Kayit_Zamani",
]

FIRMA_COLUMNS = [
    "Firma_ID",
    "Firma_Adi",
    "Tip",
    "Telefon",
    "Adres",
    "Vergi_No",
    "Vergi_Dairesi",
    "Durum",
    "Not",
]

URUN_COLUMNS = [
    "Urun_ID",
    "Urun_Adi",
    "Renk",
    "Varsayilan_Fiyat",
    "Durum",
    "Not",
]

AYAR_DEFAULTS = {
    "Odeme_Turu": ["Açık Cari", "Nakit", "Kart", "Havale/EFT", "Çek/Senet"],
    "Islem_Tipi": ["Satış", "Tahsilat", "İade", "Düzeltme"],
    "Not_Tipi": ["Genel Not", "Tahsilat Notu", "Vade Hatırlatma", "Sevkiyat", "Problem", "İade", "Özel Not"],
    "Durum": ["Açık", "Tamamlandı", "İptal"],
}

# ---------- Genel yardımcılar ----------

def normalize_key(value: Any) -> str:
    """Türkçe karakter, boşluk ve özel karakter farklarını kaldırıp kolonları eşleştirir."""
    if value is None:
        return ""
    text = str(value).strip()
    replacements = {
        "İ": "I",
        "I": "I",
        "ı": "i",
        "Ğ": "G",
        "ğ": "g",
        "Ü": "U",
        "ü": "u",
        "Ş": "S",
        "ş": "s",
        "Ö": "O",
        "ö": "o",
        "Ç": "C",
        "ç": "c",
    }
    for src, target in replacements.items():
        text = text.replace(src, target)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


def to_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    text = text.replace("TL", "").replace("₺", "").replace(" ", "")
    text = re.sub(r"[^0-9,.-]", "", text)
    if text.count(",") == 1 and text.count(".") >= 1:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def money(value: Any) -> str:
    amount = to_float(value)
    return f"{amount:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


# ---------- Google Sheets bağlantısı ----------

@st.cache_resource(show_spinner=False)
def get_client() -> gspread.Client:
    if "gcp_service_account" not in st.secrets:
        st.error("Google servis hesabı bilgisi bulunamadı. `.streamlit/secrets.toml` veya Streamlit Cloud Secrets içine eklemen gerekiyor.")
        st.stop()
    creds_info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_spreadsheet() -> gspread.Spreadsheet:
    spreadsheet_id = st.secrets.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
    client = get_client()
    return client.open_by_key(spreadsheet_id)


def get_or_create_ws(name: str, required_cols: List[str], rows: int = 1000, cols: int = 30) -> gspread.Worksheet:
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=rows, cols=cols)
        ws.update("A1", [required_cols])
        return ws
    ensure_columns(ws, required_cols)
    return ws


def ensure_columns(ws: gspread.Worksheet, required_cols: List[str]) -> None:
    headers = ws.row_values(1)
    if not headers:
        ws.update("A1", [required_cols])
        return

    existing_norm = {normalize_key(h): h for h in headers if clean_str(h)}
    final_headers = list(headers)
    changed = False
    for col in required_cols:
        if normalize_key(col) not in existing_norm:
            final_headers.append(col)
            changed = True
    if changed:
        ws.update("A1", [final_headers])


def worksheet_headers(ws: gspread.Worksheet) -> List[str]:
    headers = ws.row_values(1)
    return [h for h in headers if clean_str(h)]


def read_sheet(name: str, required_cols: List[str]) -> pd.DataFrame:
    ws = get_or_create_ws(name, required_cols)
    values = ws.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame(columns=[normalize_key(c) for c in required_cols])

    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Boş satırları sil
    df = df.dropna(how="all")
    if not df.empty:
        non_empty_mask = df.apply(lambda r: any(clean_str(x) for x in r), axis=1)
        df = df[non_empty_mask]

    # Kolonları normalize et, tekrar eden isim varsa suffix ver
    normalized_cols = []
    used = {}
    for col in df.columns:
        key = normalize_key(col)
        if not key:
            key = "bos_kolon"
        if key in used:
            used[key] += 1
            key = f"{key}_{used[key]}"
        else:
            used[key] = 1
        normalized_cols.append(key)
    df.columns = normalized_cols
    return df


def append_record(name: str, required_cols: List[str], record: Dict[str, Any]) -> None:
    ws = get_or_create_ws(name, required_cols)
    headers = worksheet_headers(ws)
    normalized_record = {normalize_key(k): v for k, v in record.items()}
    row = [normalized_record.get(normalize_key(h), "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")
    clear_cached_data()


def clear_cached_data() -> None:
    read_hareketler.clear()
    read_firmalar.clear()
    read_urunler.clear()
    read_notlar.clear()


# ---------- Veri okuma ----------

@st.cache_data(ttl=30, show_spinner=False)
def read_hareketler() -> pd.DataFrame:
    df = read_sheet(WORKSHEETS["hareketler"], HAREKET_COLUMNS)
    return prepare_hareketler(df)


@st.cache_data(ttl=60, show_spinner=False)
def read_firmalar() -> pd.DataFrame:
    return read_sheet(WORKSHEETS["firmalar"], FIRMA_COLUMNS)


@st.cache_data(ttl=60, show_spinner=False)
def read_urunler() -> pd.DataFrame:
    return read_sheet(WORKSHEETS["urunler"], URUN_COLUMNS)


@st.cache_data(ttl=30, show_spinner=False)
def read_notlar() -> pd.DataFrame:
    return read_sheet(WORKSHEETS["notlar"], NOT_COLUMNS)


def get_ayar_list(key: str) -> List[str]:
    # Ayarlar sayfasında farklı formatlar olabilir; güvenli varsayılan kullanıyoruz.
    defaults = AYAR_DEFAULTS.get(key, [])
    try:
        df = read_sheet(WORKSHEETS["ayarlar"], [key])
        nkey = normalize_key(key)
        if nkey in df.columns:
            values = [clean_str(x) for x in df[nkey].tolist() if clean_str(x)]
            return values or defaults
    except Exception:
        pass
    return defaults


def prepare_hareketler(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        for col in ["tarih", "cari", "islem_tipi", "urun", "renk", "adet", "birim_fiyat", "tutar", "tahsil_edilen", "kalan"]:
            if col not in df.columns:
                df[col] = []
        return df

    # Olası eski kolon adlarını yakala
    aliases = {
        "tarih": ["tarih"],
        "cari": ["cari", "firma", "firma_adi", "sube", "musteri", "odeme_tarihi"],
        "islem_tipi": ["islem_tipi", "islem_turu", "tip"],
        "urun": ["urun", "cinsi", "urun_adi"],
        "renk": ["renk"],
        "adet": ["adet"],
        "birim_fiyat": ["birim_fiyat", "fiyat"],
        "tutar": ["tutar", "toplam_tutar", "toplam"],
        "tahsil_edilen": ["tahsil_edilen", "tahsilat", "odenen", "nakit", "kart"],
        "kalan": ["kalan", "bakiye"],
    }

    for target, possible in aliases.items():
        if target not in df.columns:
            for p in possible:
                if p in df.columns:
                    df[target] = df[p]
                    break
        if target not in df.columns:
            df[target] = ""

    df["adet_num"] = df["adet"].apply(to_float)
    df["birim_fiyat_num"] = df["birim_fiyat"].apply(to_float)
    df["tutar_num"] = df["tutar"].apply(to_float)
    df["tahsil_edilen_num"] = df["tahsil_edilen"].apply(to_float)

    # Tutar boşsa adet x birim fiyat hesapla
    empty_tutar = df["tutar_num"].eq(0) & df["adet_num"].gt(0) & df["birim_fiyat_num"].gt(0)
    df.loc[empty_tutar, "tutar_num"] = df.loc[empty_tutar, "adet_num"] * df.loc[empty_tutar, "birim_fiyat_num"]

    tip = df["islem_tipi"].fillna("").astype(str).map(normalize_key)
    is_sale = tip.str.contains("satis", na=False) | tip.eq("")
    is_collection = tip.str.contains("tahsil", na=False)
    is_return = tip.str.contains("iade", na=False)
    is_adjustment = tip.str.contains("duzelt", na=False)

    df["satis_tutari"] = 0.0
    df.loc[is_sale, "satis_tutari"] = df.loc[is_sale, "tutar_num"]
    df.loc[is_return, "satis_tutari"] = -df.loc[is_return, "tutar_num"].abs()
    df.loc[is_adjustment, "satis_tutari"] = df.loc[is_adjustment, "tutar_num"]

    df["tahsilat_tutari"] = 0.0
    df.loc[is_sale, "tahsilat_tutari"] = df.loc[is_sale, "tahsil_edilen_num"]
    df.loc[is_collection, "tahsilat_tutari"] = df.loc[is_collection, "tahsil_edilen_num"]

    df["net_bakiye"] = df["satis_tutari"] - df["tahsilat_tutari"]
    df["tarih_dt"] = parse_date_series(df["tarih"])
    df["ay"] = df["tarih_dt"].dt.to_period("M").astype(str)
    return df


def active_firma_names() -> List[str]:
    df = read_firmalar()
    if df.empty:
        return []
    name_col = "firma_adi" if "firma_adi" in df.columns else "cari"
    if name_col not in df.columns:
        return []
    if "durum" in df.columns:
        df = df[df["durum"].astype(str).str.lower().ne("pasif")]
    return sorted({clean_str(x) for x in df[name_col].tolist() if clean_str(x)})


def active_products() -> pd.DataFrame:
    df = read_urunler()
    if df.empty:
        return pd.DataFrame(columns=["urun_adi", "renk", "varsayilan_fiyat"])
    if "durum" in df.columns:
        df = df[df["durum"].astype(str).str.lower().ne("pasif")]
    for col in ["urun_adi", "renk", "varsayilan_fiyat"]:
        if col not in df.columns:
            df[col] = ""
    return df


def cari_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "cari" not in df.columns:
        return pd.DataFrame(columns=["Cari", "Toplam Satış", "Toplam Tahsilat", "Açık Bakiye"])
    summary = (
        df.groupby("cari", dropna=False)
        .agg(
            Toplam_Satis=("satis_tutari", "sum"),
            Toplam_Tahsilat=("tahsilat_tutari", "sum"),
            Acik_Bakiye=("net_bakiye", "sum"),
        )
        .reset_index()
    )
    summary = summary.rename(columns={"cari": "Cari"})
    summary = summary.sort_values("Acik_Bakiye", ascending=False)
    return summary


def display_df_money(df: pd.DataFrame, money_cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(money)
    return out


# ---------- UI ----------

st.set_page_config(
    page_title="Günday's Cari Takip",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {background: rgba(128,128,128,0.08); border: 1px solid rgba(128,128,128,0.16); padding: 14px; border-radius: 14px;}
    .small-muted {color: #777; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("💼 Günday's Cari")
page = st.sidebar.radio(
    "Menü",
    ["Dashboard", "Satış Girişi", "Tahsilat Girişi", "Cari Detay", "Notlar", "Raporlar", "Yönetim"],
)

try:
    # Bağlantıyı erken test et
    _ = get_spreadsheet()
except Exception as exc:
    st.error("Google Sheet bağlantısı kurulamadı.")
    st.info("Servis hesabı mailini Sheet'e Düzenleyici olarak eklediğinden ve secrets bilgilerini doğru girdiğinden emin ol.")
    st.exception(exc)
    st.stop()

hareketler = read_hareketler()
firmalar = active_firma_names()
urunler_df = active_products()

# ---------- Dashboard ----------
if page == "Dashboard":
    st.title("Dashboard")
    st.caption("Google Sheets verilerinden canlı cari özet.")

    total_sales = hareketler["satis_tutari"].sum() if not hareketler.empty else 0
    total_collections = hareketler["tahsilat_tutari"].sum() if not hareketler.empty else 0
    open_balance = hareketler["net_bakiye"].sum() if not hareketler.empty else 0
    record_count = len(hareketler)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Satış", money(total_sales))
    c2.metric("Toplam Tahsilat", money(total_collections))
    c3.metric("Açık Cari", money(open_balance))
    c4.metric("Kayıt Sayısı", f"{record_count}")

    st.divider()

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Cari Bazlı Bakiye")
        summary = cari_summary(hareketler)
        if summary.empty:
            st.info("Henüz hareket yok.")
        else:
            view = display_df_money(summary, ["Toplam_Satis", "Toplam_Tahsilat", "Acik_Bakiye"])
            st.dataframe(view, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Aylık Satış")
        if hareketler.empty or "ay" not in hareketler.columns:
            st.info("Grafik için yeterli veri yok.")
        else:
            monthly = hareketler.dropna(subset=["tarih_dt"]).groupby("ay", as_index=False)["satis_tutari"].sum()
            if monthly.empty:
                st.info("Tarih bilgisi okunamadı.")
            else:
                st.bar_chart(monthly, x="ay", y="satis_tutari")

    st.subheader("Son Hareketler")
    if hareketler.empty:
        st.info("Henüz hareket yok.")
    else:
        cols = [c for c in ["tarih", "cari", "islem_tipi", "urun", "renk", "adet", "tutar_num", "tahsil_edilen_num", "net_bakiye", "not"] if c in hareketler.columns]
        recent = hareketler.sort_values("tarih_dt", ascending=False, na_position="last").head(15)[cols]
        recent = recent.rename(columns={
            "tarih": "Tarih",
            "cari": "Cari",
            "islem_tipi": "İşlem Tipi",
            "urun": "Ürün",
            "renk": "Renk",
            "adet": "Adet",
            "tutar_num": "Tutar",
            "tahsil_edilen_num": "Tahsil Edilen",
            "net_bakiye": "Net Bakiye",
            "not": "Not",
        })
        recent = display_df_money(recent, ["Tutar", "Tahsil Edilen", "Net Bakiye"])
        st.dataframe(recent, use_container_width=True, hide_index=True)

# ---------- Satış Girişi ----------
elif page == "Satış Girişi":
    st.title("Satış Girişi")
    st.caption("Yeni satış kaydı Google Sheets > CARI_HAREKETLER sayfasına işlenir.")

    with st.form("sales_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            tarih = st.date_input("Tarih", value=date.today(), format="DD.MM.YYYY")
            cari = st.selectbox("Cari / Firma", options=firmalar + ["+ Yeni cari yaz"], index=0 if firmalar else None)
            if cari == "+ Yeni cari yaz" or not firmalar:
                cari = st.text_input("Yeni Cari / Firma Adı")
        with c2:
            product_options = []
            if not urunler_df.empty:
                for _, row in urunler_df.iterrows():
                    label = clean_str(row.get("urun_adi", ""))
                    renk = clean_str(row.get("renk", ""))
                    if renk:
                        label = f"{label} - {renk}"
                    if label:
                        product_options.append(label)
            product_options = sorted(set(product_options))
            urun_secim = st.selectbox("Ürün", options=product_options + ["+ Yeni ürün yaz"], index=0 if product_options else None)
            if urun_secim == "+ Yeni ürün yaz" or not product_options:
                urun = st.text_input("Yeni Ürün Adı")
                renk = st.text_input("Renk")
                default_price = 0.0
            else:
                parts = urun_secim.split(" - ")
                urun = parts[0]
                renk = parts[1] if len(parts) > 1 else ""
                matching = urunler_df[
                    (urunler_df["urun_adi"].astype(str).str.strip() == urun)
                    & (urunler_df["renk"].astype(str).str.strip() == renk)
                ]
                default_price = to_float(matching.iloc[0].get("varsayilan_fiyat", 0)) if not matching.empty else 0.0
        with c3:
            adet = st.number_input("Adet", min_value=1, step=1, value=1)
            birim_fiyat = st.number_input("Birim Fiyat", min_value=0.0, step=100.0, value=float(default_price))
            tutar = adet * birim_fiyat
            st.metric("Tutar", money(tutar))

        c4, c5, c6 = st.columns(3)
        with c4:
            odeme_turu = st.selectbox("Ödeme Türü", options=get_ayar_list("Odeme_Turu"))
        with c5:
            tahsil_edilen = st.number_input("Tahsil Edilen", min_value=0.0, step=100.0, value=0.0)
            kalan = tutar - tahsil_edilen
            st.metric("Kalan", money(kalan))
        with c6:
            odeme_tarihi = st.date_input("Ödeme / Vade Tarihi", value=date.today(), format="DD.MM.YYYY")

        not_text = st.text_area("İşlem Notu", placeholder="Örn: 3 adet sevk edildi, kalan ödeme cuma alınacak...")
        ek_not = st.text_input("Ek Not / Kısa Etiket", placeholder="Örn: acil, vade, sevkiyat")
        kullanici = st.text_input("Kullanıcı", value="Talha")
        submitted = st.form_submit_button("Satışı Kaydet", type="primary")

    if submitted:
        if not clean_str(cari):
            st.error("Cari / Firma adı boş olamaz.")
        elif not clean_str(urun):
            st.error("Ürün adı boş olamaz.")
        elif tutar <= 0:
            st.error("Tutar 0 olamaz. Adet ve fiyatı kontrol et.")
        else:
            append_record(
                WORKSHEETS["hareketler"],
                HAREKET_COLUMNS,
                {
                    "ID": new_id("SAT"),
                    "Tarih": tarih.strftime("%d.%m.%Y"),
                    "Cari": cari,
                    "Islem_Tipi": "Satış",
                    "Urun": urun,
                    "Renk": renk,
                    "Adet": adet,
                    "Birim_Fiyat": birim_fiyat,
                    "Tutar": tutar,
                    "Odeme_Turu": odeme_turu,
                    "Tahsil_Edilen": tahsil_edilen,
                    "Kalan": kalan,
                    "Odeme_Tarihi": odeme_tarihi.strftime("%d.%m.%Y"),
                    "Not": not_text,
                    "Ek_Not": ek_not,
                    "Kayit_Zamani": now_str(),
                    "Kullanici": kullanici,
                },
            )
            st.success(f"Satış kaydedildi: {cari} / {money(tutar)}")
            st.rerun()

# ---------- Tahsilat Girişi ----------
elif page == "Tahsilat Girişi":
    st.title("Tahsilat Girişi")
    st.caption("Cari ödeme/tahsilat hareketi ekle.")

    summary = cari_summary(hareketler)
    with st.form("collection_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            cari = st.selectbox("Cari / Firma", options=firmalar + ["+ Yeni cari yaz"], index=0 if firmalar else None)
            if cari == "+ Yeni cari yaz" or not firmalar:
                cari = st.text_input("Yeni Cari / Firma Adı")
        with c2:
            tarih = st.date_input("Tahsilat Tarihi", value=date.today(), format="DD.MM.YYYY")
            odeme_turu = st.selectbox("Ödeme Türü", options=[x for x in get_ayar_list("Odeme_Turu") if x != "Açık Cari"] or get_ayar_list("Odeme_Turu"))
        with c3:
            current_balance = 0.0
            if not summary.empty and clean_str(cari):
                row = summary[summary["Cari"].astype(str).str.strip() == clean_str(cari)]
                if not row.empty:
                    current_balance = float(row.iloc[0]["Acik_Bakiye"])
            st.metric("Mevcut Açık Bakiye", money(current_balance))
            tahsil_edilen = st.number_input("Tahsilat Tutarı", min_value=0.0, step=100.0, value=0.0)
            st.metric("İşlem Sonrası Tahmini Bakiye", money(current_balance - tahsil_edilen))

        not_text = st.text_area("Tahsilat Notu", placeholder="Örn: Nakit alındı, dekont bekleniyor...")
        kullanici = st.text_input("Kullanıcı", value="Talha")
        submitted = st.form_submit_button("Tahsilatı Kaydet", type="primary")

    if submitted:
        if not clean_str(cari):
            st.error("Cari / Firma adı boş olamaz.")
        elif tahsil_edilen <= 0:
            st.error("Tahsilat tutarı 0 olamaz.")
        else:
            append_record(
                WORKSHEETS["hareketler"],
                HAREKET_COLUMNS,
                {
                    "ID": new_id("TAH"),
                    "Tarih": tarih.strftime("%d.%m.%Y"),
                    "Cari": cari,
                    "Islem_Tipi": "Tahsilat",
                    "Urun": "",
                    "Renk": "",
                    "Adet": "",
                    "Birim_Fiyat": "",
                    "Tutar": 0,
                    "Odeme_Turu": odeme_turu,
                    "Tahsil_Edilen": tahsil_edilen,
                    "Kalan": -tahsil_edilen,
                    "Odeme_Tarihi": tarih.strftime("%d.%m.%Y"),
                    "Not": not_text,
                    "Ek_Not": "Tahsilat",
                    "Kayit_Zamani": now_str(),
                    "Kullanici": kullanici,
                },
            )
            st.success(f"Tahsilat kaydedildi: {cari} / {money(tahsil_edilen)}")
            st.rerun()

# ---------- Cari Detay ----------
elif page == "Cari Detay":
    st.title("Cari Detay")
    if not firmalar:
        st.warning("Firma listesi boş görünüyor. Yönetim ekranından firma ekleyebilirsin.")
        st.stop()

    cari = st.selectbox("Cari Seç", options=firmalar)
    df = hareketler[hareketler["cari"].astype(str).str.strip() == clean_str(cari)] if not hareketler.empty else pd.DataFrame()

    total_sales = df["satis_tutari"].sum() if not df.empty else 0
    total_collections = df["tahsilat_tutari"].sum() if not df.empty else 0
    open_balance = df["net_bakiye"].sum() if not df.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Satış", money(total_sales))
    c2.metric("Toplam Tahsilat", money(total_collections))
    c3.metric("Açık Bakiye", money(open_balance))

    st.subheader("Hareket Dökümü")
    if df.empty:
        st.info("Bu cariye ait hareket yok.")
    else:
        cols = [c for c in ["tarih", "islem_tipi", "urun", "renk", "adet", "tutar_num", "tahsil_edilen_num", "net_bakiye", "odeme_turu", "not"] if c in df.columns]
        view = df.sort_values("tarih_dt", ascending=False, na_position="last")[cols]
        view = view.rename(columns={
            "tarih": "Tarih",
            "islem_tipi": "İşlem Tipi",
            "urun": "Ürün",
            "renk": "Renk",
            "adet": "Adet",
            "tutar_num": "Tutar",
            "tahsil_edilen_num": "Tahsil Edilen",
            "net_bakiye": "Net Bakiye",
            "odeme_turu": "Ödeme Türü",
            "not": "Not",
        })
        view = display_df_money(view, ["Tutar", "Tahsil Edilen", "Net Bakiye"])
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Cari Notları")
    notes = read_notlar()
    if notes.empty or "cari" not in notes.columns:
        st.info("Bu cariye ait not yok.")
    else:
        notes = notes[notes["cari"].astype(str).str.strip() == clean_str(cari)]
        if notes.empty:
            st.info("Bu cariye ait not yok.")
        else:
            show_cols = [c for c in ["tarih", "not_tipi", "not_detayi", "hatirlatma_tarihi", "durum", "kullanici"] if c in notes.columns]
            st.dataframe(notes[show_cols].tail(20), use_container_width=True, hide_index=True)

# ---------- Notlar ----------
elif page == "Notlar":
    st.title("Notlar & Hatırlatmalar")
    st.caption("Cari bazlı not, problem, vade ve sevkiyat hatırlatmaları.")

    with st.form("note_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            tarih = st.date_input("Not Tarihi", value=date.today(), format="DD.MM.YYYY")
            cari = st.selectbox("Cari / Firma", options=firmalar + ["+ Yeni cari yaz"], index=0 if firmalar else None)
            if cari == "+ Yeni cari yaz" or not firmalar:
                cari = st.text_input("Yeni Cari / Firma Adı")
        with c2:
            not_tipi = st.selectbox("Not Tipi", options=get_ayar_list("Not_Tipi"))
            hatirlatma_tarihi = st.date_input("Hatırlatma Tarihi", value=date.today(), format="DD.MM.YYYY")
        with c3:
            durum = st.selectbox("Durum", options=get_ayar_list("Durum"))
            kullanici = st.text_input("Kullanıcı", value="Talha")

        not_detayi = st.text_area("Not Detayı", placeholder="Örn: Cuma günü ödeme için aranacak...")
        submitted = st.form_submit_button("Notu Kaydet", type="primary")

    if submitted:
        if not clean_str(cari):
            st.error("Cari / Firma adı boş olamaz.")
        elif not clean_str(not_detayi):
            st.error("Not detayı boş olamaz.")
        else:
            append_record(
                WORKSHEETS["notlar"],
                NOT_COLUMNS,
                {
                    "ID": new_id("NOT"),
                    "Tarih": tarih.strftime("%d.%m.%Y"),
                    "Cari": cari,
                    "Not_Tipi": not_tipi,
                    "Not_Detayi": not_detayi,
                    "Hatirlatma_Tarihi": hatirlatma_tarihi.strftime("%d.%m.%Y"),
                    "Durum": durum,
                    "Kullanici": kullanici,
                    "Kayit_Zamani": now_str(),
                },
            )
            st.success("Not kaydedildi.")
            st.rerun()

    st.subheader("Açık Notlar")
    notes = read_notlar()
    if notes.empty:
        st.info("Henüz not yok.")
    else:
        if "durum" in notes.columns:
            notes = notes[notes["durum"].astype(str).str.lower().ne("tamamlandı")]
        show_cols = [c for c in ["tarih", "cari", "not_tipi", "not_detayi", "hatirlatma_tarihi", "durum", "kullanici"] if c in notes.columns]
        st.dataframe(notes[show_cols], use_container_width=True, hide_index=True)

# ---------- Raporlar ----------
elif page == "Raporlar":
    st.title("Raporlar")
    st.caption("Tarih, cari ve ürün bazlı filtreleme.")

    if hareketler.empty:
        st.info("Henüz raporlanacak hareket yok.")
        st.stop()

    min_date = hareketler["tarih_dt"].min()
    max_date = hareketler["tarih_dt"].max()
    default_start = min_date.date() if pd.notna(min_date) else date.today()
    default_end = max_date.date() if pd.notna(max_date) else date.today()

    c1, c2, c3 = st.columns(3)
    with c1:
        start_date = st.date_input("Başlangıç", value=default_start, format="DD.MM.YYYY")
    with c2:
        end_date = st.date_input("Bitiş", value=default_end, format="DD.MM.YYYY")
    with c3:
        selected_cari = st.multiselect("Cari", options=firmalar)

    products = sorted({clean_str(x) for x in hareketler.get("urun", pd.Series(dtype=str)).tolist() if clean_str(x)})
    selected_products = st.multiselect("Ürün", options=products)

    filtered = hareketler.copy()
    if "tarih_dt" in filtered.columns:
        filtered = filtered[(filtered["tarih_dt"].dt.date >= start_date) & (filtered["tarih_dt"].dt.date <= end_date)]
    if selected_cari:
        filtered = filtered[filtered["cari"].isin(selected_cari)]
    if selected_products:
        filtered = filtered[filtered["urun"].isin(selected_products)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Filtreli Satış", money(filtered["satis_tutari"].sum()))
    c2.metric("Filtreli Tahsilat", money(filtered["tahsilat_tutari"].sum()))
    c3.metric("Filtreli Bakiye", money(filtered["net_bakiye"].sum()))

    show_cols = [c for c in ["tarih", "cari", "islem_tipi", "urun", "renk", "adet", "tutar_num", "tahsil_edilen_num", "net_bakiye", "odeme_turu", "not"] if c in filtered.columns]
    report = filtered[show_cols].rename(columns={
        "tarih": "Tarih",
        "cari": "Cari",
        "islem_tipi": "İşlem Tipi",
        "urun": "Ürün",
        "renk": "Renk",
        "adet": "Adet",
        "tutar_num": "Tutar",
        "tahsil_edilen_num": "Tahsil Edilen",
        "net_bakiye": "Net Bakiye",
        "odeme_turu": "Ödeme Türü",
        "not": "Not",
    })
    st.dataframe(display_df_money(report, ["Tutar", "Tahsil Edilen", "Net Bakiye"]), use_container_width=True, hide_index=True)

    csv = report.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSV İndir", data=csv, file_name="gundays_cari_rapor.csv", mime="text/csv")

# ---------- Yönetim ----------
elif page == "Yönetim":
    st.title("Yönetim")
    tab1, tab2 = st.tabs(["Firma Ekle", "Ürün Ekle"])

    with tab1:
        st.subheader("Yeni Firma / Cari")
        with st.form("firma_form"):
            c1, c2 = st.columns(2)
            with c1:
                firma_adi = st.text_input("Firma Adı")
                tip = st.text_input("Tip", placeholder="AVM, Pazaryeri, Şube...")
                telefon = st.text_input("Telefon")
            with c2:
                adres = st.text_area("Adres")
                vergi_no = st.text_input("Vergi No")
                vergi_dairesi = st.text_input("Vergi Dairesi")
            not_text = st.text_area("Not")
            submitted = st.form_submit_button("Firmayı Kaydet", type="primary")
        if submitted:
            if not clean_str(firma_adi):
                st.error("Firma adı boş olamaz.")
            else:
                append_record(
                    WORKSHEETS["firmalar"],
                    FIRMA_COLUMNS,
                    {
                        "Firma_ID": new_id("FIR"),
                        "Firma_Adi": firma_adi,
                        "Tip": tip,
                        "Telefon": telefon,
                        "Adres": adres,
                        "Vergi_No": vergi_no,
                        "Vergi_Dairesi": vergi_dairesi,
                        "Durum": "Aktif",
                        "Not": not_text,
                    },
                )
                st.success("Firma kaydedildi.")
                st.rerun()

        st.subheader("Firma Listesi")
        fdf = read_firmalar()
        if fdf.empty:
            st.info("Firma listesi boş.")
        else:
            st.dataframe(fdf, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Yeni Ürün")
        with st.form("urun_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                urun_adi = st.text_input("Ürün Adı")
            with c2:
                renk = st.text_input("Renk")
            with c3:
                varsayilan_fiyat = st.number_input("Varsayılan Fiyat", min_value=0.0, step=100.0, value=0.0)
            not_text = st.text_area("Not")
            submitted = st.form_submit_button("Ürünü Kaydet", type="primary")
        if submitted:
            if not clean_str(urun_adi):
                st.error("Ürün adı boş olamaz.")
            else:
                append_record(
                    WORKSHEETS["urunler"],
                    URUN_COLUMNS,
                    {
                        "Urun_ID": new_id("URN"),
                        "Urun_Adi": urun_adi,
                        "Renk": renk,
                        "Varsayilan_Fiyat": varsayilan_fiyat,
                        "Durum": "Aktif",
                        "Not": not_text,
                    },
                )
                st.success("Ürün kaydedildi.")
                st.rerun()

        st.subheader("Ürün Listesi")
        udf = read_urunler()
        if udf.empty:
            st.info("Ürün listesi boş.")
        else:
            st.dataframe(udf, use_container_width=True, hide_index=True)
