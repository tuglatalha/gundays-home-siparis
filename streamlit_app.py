# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
from io import BytesIO
import hashlib
import re
import unicodedata
from typing import Dict, List, Tuple, Any

# ============================================================
# GÜNDAY'S HOME SİPARİŞ TAKİP - GOOGLE SHEETS SABİT ŞEMA SÜRÜMÜ
# ============================================================

st.set_page_config(
    page_title="Günday's Home Sipariş Takip",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Günday's Home Sipariş Takip"
SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# -------------------------
# SABİT SHEET ŞEMASI
# -------------------------
SCHEMAS: Dict[str, List[str]] = {
    "Firmalar": [
        "Firma_ID", "Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres",
        "Vergi_No", "Vergi_Dairesi", "Not", "Aktif", "Kayit_Tarihi"
    ],
    "Urunler": [
        "Urun_ID", "Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat",
        "Stok", "Durum", "Not", "Kayit_Tarihi"
    ],
    "Siparisler": [
        "Siparis_No", "Firma_ID", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi",
        "Durum", "Odeme_Durumu", "Sevkiyat_Notu", "Genel_Not", "Olusturan",
        "Toplam_Tutar", "Kayit_Tarihi"
    ],
    "Siparis_Kalemleri": [
        "Kalem_ID", "Siparis_No", "Urun_ID", "Urun_Adi", "Model", "Renk",
        "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"
    ],
    "Odemeler": [
        "Odeme_ID", "Siparis_No", "Firma_Adi", "Odeme_Tarihi", "Tutar", "Odeme_Tipi",
        "Aciklama", "Kayit_Tarihi"
    ],
    "Kullanicilar": [
        "Kullanici_Adi", "Sifre_Hash", "Rol", "Aktif", "Kayit_Tarihi"
    ],
}

# Başlık/kolon aliasları: Eski bozuk şablonlardan gelen adları sabit kolona bağlar.
ALIASES: Dict[str, Dict[str, str]] = {
    "Firmalar": {
        "firma id": "Firma_ID", "firma_id": "Firma_ID", "firmaid": "Firma_ID",
        "firma adi": "Firma_Adi", "firma adı": "Firma_Adi", "firma_adi": "Firma_Adi", "firma adı *": "Firma_Adi",
        "şube": "Sube", "sube": "Sube",
        "yetkili kisi": "Yetkili_Kisi", "yetkili kişi": "Yetkili_Kisi", "yetkili_kisi": "Yetkili_Kisi",
        "telefon": "Telefon", "adres": "Adres", "vergi no": "Vergi_No", "vkn": "Vergi_No", "vergi_no": "Vergi_No",
        "vergi dairesi": "Vergi_Dairesi", "vergi_dairesi": "Vergi_Dairesi", "not": "Not",
        "aktif": "Aktif", "durum": "Aktif", "kayıt tarihi": "Kayit_Tarihi", "kayit_tarihi": "Kayit_Tarihi",
    },
    "Urunler": {
        "urun id": "Urun_ID", "ürün id": "Urun_ID", "urun_id": "Urun_ID", "ürün_id": "Urun_ID",
        "kategori": "Kategori",
        "urun adi": "Urun_Adi", "ürün adı": "Urun_Adi", "urun_adi": "Urun_Adi", "ürün": "Urun_Adi",
        "model": "Model", "renk": "Renk",
        "birim fiyat": "Birim_Fiyat", "birim_fiyat": "Birim_Fiyat", "fiyat": "Birim_Fiyat",
        "stok": "Stok", "aktif": "Durum", "durum": "Durum", "not": "Not",
        "kayıt tarihi": "Kayit_Tarihi", "kayit_tarihi": "Kayit_Tarihi",
    },
    "Siparisler": {
        "siparis no": "Siparis_No", "sipariş no": "Siparis_No", "siparis_no": "Siparis_No",
        "firma id": "Firma_ID", "firma_id": "Firma_ID",
        "firma adi": "Firma_Adi", "firma adı": "Firma_Adi", "firma_adi": "Firma_Adi", "firma": "Firma_Adi",
        "şube": "Sube", "sube": "Sube",
        "siparis tarihi": "Siparis_Tarihi", "sipariş tarihi": "Siparis_Tarihi", "siparis_tarihi": "Siparis_Tarihi",
        "teslim tarihi": "Teslim_Tarihi", "teslim_tarihi": "Teslim_Tarihi",
        "durum": "Durum", "odeme durumu": "Odeme_Durumu", "ödeme durumu": "Odeme_Durumu", "odeme_durumu": "Odeme_Durumu",
        "sevkiyat notu": "Sevkiyat_Notu", "sevkiyat_notu": "Sevkiyat_Notu",
        "genel not": "Genel_Not", "genel_not": "Genel_Not", "not": "Genel_Not",
        "oluşturan": "Olusturan", "olusturan": "Olusturan",
        "toplam tutar": "Toplam_Tutar", "toplam_tutar": "Toplam_Tutar", "toplam": "Toplam_Tutar",
        "kayıt tarihi": "Kayit_Tarihi", "kayit_tarihi": "Kayit_Tarihi",
    },
    "Siparis_Kalemleri": {
        "kalem id": "Kalem_ID", "kalem_id": "Kalem_ID",
        "siparis no": "Siparis_No", "sipariş no": "Siparis_No", "siparis_no": "Siparis_No",
        "urun id": "Urun_ID", "ürün id": "Urun_ID", "urun_id": "Urun_ID",
        "urun adi": "Urun_Adi", "ürün adı": "Urun_Adi", "urun_adi": "Urun_Adi", "ürün": "Urun_Adi",
        "model": "Model", "renk": "Renk", "adet": "Adet",
        "birim fiyat": "Birim_Fiyat", "birim_fiyat": "Birim_Fiyat",
        "satir toplam": "Satir_Toplam", "satır toplam": "Satir_Toplam", "satir_toplam": "Satir_Toplam", "toplam": "Satir_Toplam",
        "not": "Not",
    },
    "Odemeler": {
        "odeme id": "Odeme_ID", "ödeme id": "Odeme_ID", "odeme_id": "Odeme_ID",
        "siparis no": "Siparis_No", "sipariş no": "Siparis_No", "siparis_no": "Siparis_No",
        "firma adi": "Firma_Adi", "firma adı": "Firma_Adi", "firma_adi": "Firma_Adi",
        "odeme tarihi": "Odeme_Tarihi", "ödeme tarihi": "Odeme_Tarihi", "odeme_tarihi": "Odeme_Tarihi",
        "tutar": "Tutar", "odeme tipi": "Odeme_Tipi", "ödeme tipi": "Odeme_Tipi", "odeme_tipi": "Odeme_Tipi",
        "aciklama": "Aciklama", "açıklama": "Aciklama", "not": "Aciklama",
        "kayıt tarihi": "Kayit_Tarihi", "kayit_tarihi": "Kayit_Tarihi",
    },
    "Kullanicilar": {
        "kullanici adi": "Kullanici_Adi", "kullanıcı adı": "Kullanici_Adi", "kullanici_adi": "Kullanici_Adi",
        "sifre hash": "Sifre_Hash", "şifre hash": "Sifre_Hash", "sifre_hash": "Sifre_Hash",
        "rol": "Rol", "aktif": "Aktif", "durum": "Aktif", "kayit_tarihi": "Kayit_Tarihi", "kayıt tarihi": "Kayit_Tarihi",
    },
}

ORDER_STATUS = ["Sipariş Alındı", "Üretimde", "Hazır", "Sevkiyat Bekliyor", "Gönderildi", "Teslim Edildi", "İptal Edildi"]
PAYMENT_STATUS = ["Bekliyor", "Kısmi Ödendi", "Ödendi", "Vadeli", "İptal"]
PAYMENT_TYPES = ["Nakit", "Havale/EFT", "Kredi Kartı", "Çek/Senet", "Mahsup", "Diğer"]

# -------------------------
# CSS
# -------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: radial-gradient(circle at 10% 10%, rgba(246,186,69,0.10), transparent 22%), linear-gradient(135deg, #050b14 0%, #07111f 45%, #0b1a33 100%); }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #081326 0%, #101827 100%); border-right: 1px solid rgba(244,185,66,0.25); }
        h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; }
        label, p, span, div { color: #ffffff; }
        .small-muted { color:#aeb8c8; font-size:0.9rem; }
        .gh-card { background: linear-gradient(145deg, #0c1728 0%, #121d31 100%); border: 1px solid rgba(244,185,66,0.55); border-radius: 18px; padding: 22px; box-shadow: 0 10px 30px rgba(0,0,0,.25); min-height: 128px; }
        .gh-card .label { color:#f4d58c; font-size:0.9rem; font-weight:800; }
        .gh-card .value { color:#ffffff; font-size:2rem; font-weight:900; margin-top:10px; }
        .gh-card .hint { color:#f4b942; font-size:.85rem; margin-top:6px; font-weight:700; }
        .success-box { background:#0d3b2a; border:1px solid rgba(62, 207, 142, .35); color:#58ef9f; padding:14px; border-radius:12px; font-weight:700; }
        .warn-box { background:#3b2610; border:1px solid rgba(244,185,66,.35); color:#ffd27a; padding:14px; border-radius:12px; font-weight:700; }
        .error-box { background:#3a1721; border:1px solid rgba(255,90,110,.35); color:#ff6b7a; padding:14px; border-radius:12px; font-weight:700; }
        .stButton button { border:1px solid rgba(244,185,66,.75); border-radius:12px; background:linear-gradient(90deg, rgba(244,185,66,.24), rgba(255,255,255,.05)); color:#fff; font-weight:800; }
        .stButton button:hover { border-color:#ffd36b; color:#ffd36b; }
        div[data-testid="stDataFrame"] { border:1px solid rgba(255,255,255,.12); border-radius:12px; overflow:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# Yardımcılar
# -------------------------
def norm_text(x: Any) -> str:
    s = "" if x is None else str(x)
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("ı", "i")
    s = re.sub(r"[^a-z0-9_ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def today_str() -> str:
    return date.today().isoformat()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money_to_float(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return 0.0
    s = s.replace("TL", "").replace("₺", "").replace(" ", "")
    # TR format: 12.850,50 -> 12850.50
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def fmt_money(v: Any) -> str:
    n = money_to_float(v)
    return f"{n:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def hash_pw(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()


def make_id(prefix: str, existing: pd.Series) -> str:
    max_no = 0
    for val in existing.dropna().astype(str).tolist():
        m = re.search(r"(\d+)$", val)
        if m:
            max_no = max(max_no, int(m.group(1)))
    return f"{prefix}-{max_no + 1:04d}"


def make_order_no(existing: pd.Series) -> str:
    year = date.today().year
    prefix = f"GH-{year}"
    max_no = 0
    for val in existing.dropna().astype(str).tolist():
        if str(val).startswith(prefix):
            m = re.search(r"(\d+)$", str(val))
            if m:
                max_no = max(max_no, int(m.group(1)))
    return f"{prefix}-{max_no + 1:04d}"


def empty_df(sheet_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMAS[sheet_name])


def normalize_df(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    schema = SCHEMAS[sheet_name]
    aliases = ALIASES.get(sheet_name, {})
    if df is None or df.empty:
        return empty_df(sheet_name)

    df = df.copy()
    # Kolonları temizle ve aliasları uygula
    rename = {}
    seen = set()
    for col in df.columns:
        base = norm_text(col)
        target = aliases.get(base)
        if target and target not in seen:
            rename[col] = target
            seen.add(target)
        elif col in schema and col not in seen:
            rename[col] = col
            seen.add(col)
        else:
            # şema dışı veya tekrar kolonları atılacak
            rename[col] = None
    df = df.rename(columns={k: v for k, v in rename.items() if v})
    keep = [c for c in df.columns if c in schema]
    df = df[keep] if keep else pd.DataFrame()
    for col in schema:
        if col not in df.columns:
            df[col] = ""
    df = df[schema]

    # Header satırları ve boş satırlar temizlensin
    key_col = schema[0]
    name_col = schema[1] if len(schema) > 1 else key_col
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Eski şablonlarda başlıklar veri satırı gibi gelebiliyor: urun_id/kategori/firma_id gibi.
    bad_tokens = {norm_text(c) for c in schema} | {"urun kartlari", "firma kartlari", "siparis kartlari", "odeme kartlari"}
    mask_not_header = ~df.apply(lambda row: norm_text(row.get(key_col, "")) in bad_tokens or norm_text(row.get(name_col, "")) in bad_tokens, axis=1)
    df = df[mask_not_header]

    # tamamen boş satırlar
    df = df[~df.apply(lambda r: all(str(x).strip() == "" for x in r.tolist()), axis=1)]

    # ID yok ama ad varsa ID üret
    if key_col in df.columns:
        for idx in df.index:
            if not str(df.at[idx, key_col]).strip():
                if sheet_name == "Firmalar" and str(df.at[idx, "Firma_Adi"]).strip():
                    df.at[idx, key_col] = make_id("F", df[key_col])
                elif sheet_name == "Urunler" and str(df.at[idx, "Urun_Adi"]).strip():
                    df.at[idx, key_col] = make_id("U", df[key_col])
                elif sheet_name == "Siparisler" and str(df.at[idx, "Firma_Adi"]).strip():
                    df.at[idx, key_col] = make_order_no(df[key_col])
                elif sheet_name == "Siparis_Kalemleri" and str(df.at[idx, "Siparis_No"]).strip():
                    df.at[idx, key_col] = make_id("K", df[key_col])
                elif sheet_name == "Odemeler" and str(df.at[idx, "Siparis_No"]).strip():
                    df.at[idx, key_col] = make_id("O", df[key_col])

    # Varsayılan durumlar
    if sheet_name == "Firmalar":
        df.loc[df["Aktif"].eq(""), "Aktif"] = "Aktif"
        df = df[df["Firma_Adi"].astype(str).str.strip().ne("")]
    if sheet_name == "Urunler":
        df.loc[df["Durum"].eq(""), "Durum"] = "Aktif"
        df = df[df["Urun_Adi"].astype(str).str.strip().ne("")]
    if sheet_name == "Kullanicilar":
        df.loc[df["Aktif"].eq(""), "Aktif"] = "Aktif"
        df.loc[df["Rol"].eq(""), "Rol"] = "Admin"

    # Numerik kolonları standart stringe çevir
    for col in ["Birim_Fiyat", "Stok", "Toplam_Tutar", "Adet", "Satir_Toplam", "Tutar"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: str(money_to_float(x)).rstrip("0").rstrip(".") if str(x).strip() != "" else "0")

    df = df.drop_duplicates(subset=[key_col], keep="last") if key_col in df.columns else df
    df = df.reset_index(drop=True)
    return df[schema]


def parse_values_to_df(values: List[List[Any]], sheet_name: str) -> pd.DataFrame:
    schema = SCHEMAS[sheet_name]
    if not values:
        return empty_df(sheet_name)

    # İlk 15 satır içinde şemaya en çok benzeyen başlık satırını bul
    best_idx = 0
    best_score = -1
    aliases = ALIASES.get(sheet_name, {})
    schema_norm = {norm_text(c) for c in schema}
    alias_norm = set(aliases.keys())
    for i, row in enumerate(values[:15]):
        score = 0
        for cell in row:
            n = norm_text(cell)
            if n in schema_norm or n in alias_norm:
                score += 1
        if score > best_score:
            best_idx = i
            best_score = score

    if best_score < 2:
        # Sheet bozuksa standart başlık kabul et; veri yok sayılır
        return empty_df(sheet_name)

    headers_raw = values[best_idx]
    # Tekrarlı veya boş kolon adlarını benzersiz yap
    headers = []
    seen = {}
    for j, h in enumerate(headers_raw):
        h = str(h).strip() or f"Bos_{j+1}"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 1
        headers.append(h)
    rows = values[best_idx + 1:]
    width = len(headers)
    normalized_rows = []
    for r in rows:
        r = list(r)
        if len(r) < width:
            r = r + [""] * (width - len(r))
        elif len(r) > width:
            r = r[:width]
        normalized_rows.append(r)
    raw_df = pd.DataFrame(normalized_rows, columns=headers)
    return normalize_df(raw_df, sheet_name)

# -------------------------
# Google Sheets Bağlantısı
# -------------------------
@st.cache_resource(show_spinner=False)
def get_client():
    if not SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID Streamlit Secrets içinde bulunamadı.")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("gcp_service_account Streamlit Secrets içinde bulunamadı.")
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    return get_client().open_by_key(SPREADSHEET_ID)


def get_or_create_ws(sheet_name: str, rows: int = 1000, cols: int = 30):
    ss = get_spreadsheet()
    try:
        return ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=sheet_name, rows=rows, cols=cols)
        ws.update(values=[SCHEMAS[sheet_name]], range_name="A1")
        return ws


@st.cache_data(ttl=30, show_spinner=False)
def load_all_data_cached() -> Dict[str, pd.DataFrame]:
    ss = get_spreadsheet()
    result: Dict[str, pd.DataFrame] = {}
    for sheet_name in SCHEMAS:
        try:
            ws = get_or_create_ws(sheet_name)
            values = ws.get_all_values()
            result[sheet_name] = parse_values_to_df(values, sheet_name)
        except Exception:
            result[sheet_name] = empty_df(sheet_name)
    # admin yoksa bellekte ekle; Settings'te onar veya ilk şifre değişiminde Sheet'e yazılır.
    users = result.get("Kullanicilar", empty_df("Kullanicilar"))
    if users.empty:
        users = pd.DataFrame([{
            "Kullanici_Adi": "admin",
            "Sifre_Hash": hash_pw("admin123"),
            "Rol": "Admin",
            "Aktif": "Aktif",
            "Kayit_Tarihi": today_str(),
        }], columns=SCHEMAS["Kullanicilar"])
        result["Kullanicilar"] = users
    return result


def load_all_data() -> Dict[str, pd.DataFrame]:
    return load_all_data_cached()


def clear_data_cache() -> None:
    try:
        load_all_data_cached.clear()
    except Exception:
        st.cache_data.clear()


def write_df(sheet_name: str, df: pd.DataFrame) -> None:
    df = normalize_df(df, sheet_name)
    ws = get_or_create_ws(sheet_name)
    values = [SCHEMAS[sheet_name]] + df.fillna("").astype(str).values.tolist()
    ws.clear()
    ws.update(values=values, range_name="A1")
    clear_data_cache()


def repair_all_sheets() -> None:
    data = load_all_data()
    for name in SCHEMAS:
        df = data.get(name, empty_df(name))
        if name == "Kullanicilar" and df.empty:
            df = pd.DataFrame([{
                "Kullanici_Adi": "admin",
                "Sifre_Hash": hash_pw("admin123"),
                "Rol": "Admin",
                "Aktif": "Aktif",
                "Kayit_Tarihi": today_str(),
            }], columns=SCHEMAS[name])
        write_df(name, df)
    clear_data_cache()

# -------------------------
# UI Yardımcıları
# -------------------------
def show_df(df: pd.DataFrame, height: int = 340) -> None:
    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        st.info("Kayıt yok.")
    else:
        st.dataframe(df.fillna(""), use_container_width=True, hide_index=True, height=height)


def metric_card(label: str, value: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div class='gh-card'>
            <div class='label'>{label}</div>
            <div class='value'>{value}</div>
            <div class='hint'>{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def success(msg: str):
    st.markdown(f"<div class='success-box'>{msg}</div>", unsafe_allow_html=True)


def warn(msg: str):
    st.markdown(f"<div class='warn-box'>{msg}</div>", unsafe_allow_html=True)


def error_box(msg: str):
    st.markdown(f"<div class='error-box'>{msg}</div>", unsafe_allow_html=True)


def active_firms(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Firmalar"].copy()
    if df.empty:
        return df
    return df[df["Aktif"].astype(str).str.lower().eq("aktif")].reset_index(drop=True)


def active_products(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Urunler"].copy()
    if df.empty:
        return df
    return df[df["Durum"].astype(str).str.lower().eq("aktif")].reset_index(drop=True)

# -------------------------
# Auth
# -------------------------
def authenticate(data: Dict[str, pd.DataFrame], username: str, password: str) -> Tuple[bool, str]:
    users = data["Kullanicilar"].copy()
    if users.empty:
        return username == "admin" and password == "admin123", "Admin"
    u = users[(users["Kullanici_Adi"].astype(str) == username) & (users["Aktif"].astype(str).str.lower() == "aktif")]
    if u.empty:
        return False, ""
    row = u.iloc[0]
    return str(row["Sifre_Hash"]) == hash_pw(password), str(row.get("Rol", "Admin"))


def login_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown(f"# {APP_TITLE}")
    st.markdown("<span class='small-muted'>Sipariş, firma, ürün, ödeme ve sevkiyat durumlarını tek panelden yönetin.</span>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("## Yönetim Paneli Girişi")
        with st.form("login_form"):
            username = st.text_input("Kullanıcı adı", value="")
            password = st.text_input("Şifre", type="password", value="")
            submitted = st.form_submit_button("Giriş yap", use_container_width=True)
        if submitted:
            ok, role = authenticate(data, username.strip(), password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")
        st.info("İlk kurulum bilgisi: admin / admin123. Yayına almadan önce şifreyi değiştirin.")

# -------------------------
# Sayfalar
# -------------------------
def dashboard_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Dashboard")
    st.caption("Günday's Home genel sipariş özeti")
    orders = data["Siparisler"].copy()
    payments = data["Odemeler"].copy()
    orders["Toplam_Tutar_Num"] = orders["Toplam_Tutar"].apply(money_to_float) if not orders.empty else []
    payments["Tutar_Num"] = payments["Tutar"].apply(money_to_float) if not payments.empty else []
    total_orders = len(orders)
    active_orders = len(orders[~orders["Durum"].astype(str).isin(["Teslim Edildi", "İptal Edildi"])]) if not orders.empty else 0
    total_revenue = orders["Toplam_Tutar_Num"].sum() if not orders.empty else 0.0
    total_paid = payments["Tutar_Num"].sum() if not payments.empty else 0.0
    unpaid = max(total_revenue - total_paid, 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Toplam Sipariş", str(total_orders), "Tüm kayıtlar")
    with c2: metric_card("Aktif Sipariş", str(active_orders), "Teslim/iptal hariç")
    with c3: metric_card("Ciro", fmt_money(total_revenue), "Sipariş toplamı")
    with c4: metric_card("Ödeme Bekleyen", fmt_money(unpaid), "Tahsilat farkı")

    st.divider()
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("## Son Siparişler")
        if orders.empty:
            st.info("Henüz sipariş yok.")
        else:
            show_cols = ["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar"]
            last = orders.tail(10).iloc[::-1][show_cols].copy()
            last["Toplam_Tutar"] = last["Toplam_Tutar"].apply(fmt_money)
            show_df(last, height=330)
    with right:
        st.markdown("## Durum Dağılımı")
        if orders.empty:
            st.info("Grafik için veri yok.")
        else:
            status_counts = orders["Durum"].replace("", "Belirsiz").value_counts().reset_index()
            status_counts.columns = ["Durum", "Adet"]
            st.bar_chart(status_counts, x="Durum", y="Adet", use_container_width=True)

    st.markdown("## Hızlı Uyarılar")
    if orders.empty:
        success("Şu an kritik uyarı yok.")
    else:
        critical = orders[orders["Durum"].astype(str).isin(["Üretimde", "Sevkiyat Bekliyor"])]
        if critical.empty:
            success("Şu an kritik bekleyen durum görünmüyor.")
        else:
            warn(f"{len(critical)} adet üretim/sevkiyat bekleyen sipariş var.")


def firms_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Firmalar")
    st.caption("Bayi, müşteri ve şube kartlarını yönetin")
    firms = data["Firmalar"].copy()
    orders = data["Siparisler"].copy()

    with st.expander("+ Yeni firma / şube ekle", expanded=True):
        with st.form("add_firm", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Firma adı *")
                sube = st.text_input("Şube")
                contact = st.text_input("Yetkili kişi")
            with c2:
                phone = st.text_input("Telefon")
                tax_no = st.text_input("Vergi No / VKN")
                tax_office = st.text_input("Vergi Dairesi")
            with c3:
                address = st.text_area("Adres", height=92)
                note = st.text_area("Not", height=92)
            if st.form_submit_button("Firmayı kaydet", use_container_width=True):
                if not name.strip():
                    st.error("Firma adı zorunlu.")
                else:
                    new_id = make_id("F", firms["Firma_ID"] if "Firma_ID" in firms else pd.Series(dtype=str))
                    new_row = {
                        "Firma_ID": new_id, "Firma_Adi": name.strip(), "Sube": sube.strip(),
                        "Yetkili_Kisi": contact.strip(), "Telefon": phone.strip(), "Adres": address.strip(),
                        "Vergi_No": tax_no.strip(), "Vergi_Dairesi": tax_office.strip(), "Not": note.strip(),
                        "Aktif": "Aktif", "Kayit_Tarihi": today_str(),
                    }
                    firms = pd.concat([firms, pd.DataFrame([new_row])], ignore_index=True)
                    write_df("Firmalar", firms)
                    st.success("Firma kaydedildi ve Google Sheets'e yazıldı.")
                    st.rerun()

    st.markdown("## Kayıtlı Firmalar")
    show_df(firms, height=280)

    st.markdown("## Firma Düzelt / Sil")
    if firms.empty:
        st.info("Düzenlenecek firma yok.")
        return
    labels = {f"{r.Firma_ID} - {r.Firma_Adi} / {r.Sube}": i for i, r in firms.iterrows()}
    selected = st.selectbox("Firma seç", list(labels.keys()))
    idx = labels[selected]
    row = firms.loc[idx]
    with st.form("edit_firm"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_name = st.text_input("Firma adı", row["Firma_Adi"])
            e_sube = st.text_input("Şube", row["Sube"])
            e_contact = st.text_input("Yetkili kişi", row["Yetkili_Kisi"])
        with c2:
            e_phone = st.text_input("Telefon", row["Telefon"])
            e_tax_no = st.text_input("Vergi No / VKN", row["Vergi_No"])
            e_tax_office = st.text_input("Vergi Dairesi", row["Vergi_Dairesi"])
        with c3:
            e_status = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if row["Aktif"] == "Aktif" else 1)
            e_address = st.text_area("Adres", row["Adres"], height=80)
            e_note = st.text_area("Not", row["Not"], height=80)
        csave, cdelete = st.columns(2)
        save = csave.form_submit_button("Güncelle", use_container_width=True)
        delete = cdelete.form_submit_button("Sil / Pasife al", use_container_width=True)
    if save:
        firms.loc[idx, ["Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres", "Vergi_No", "Vergi_Dairesi", "Not", "Aktif"]] = [
            e_name.strip(), e_sube.strip(), e_contact.strip(), e_phone.strip(), e_address.strip(), e_tax_no.strip(), e_tax_office.strip(), e_note.strip(), e_status
        ]
        write_df("Firmalar", firms)
        st.success("Firma güncellendi.")
        st.rerun()
    if delete:
        used = False
        if not orders.empty:
            used = (orders["Firma_ID"].astype(str) == str(row["Firma_ID"])).any() or (
                (orders["Firma_Adi"].astype(str) == str(row["Firma_Adi"])) & (orders["Sube"].astype(str) == str(row["Sube"]))
            ).any()
        if used:
            firms.loc[idx, "Aktif"] = "Pasif"
            msg = "Firma geçmiş siparişlerde kullanıldığı için silinmedi, pasife alındı."
        else:
            firms = firms.drop(index=idx).reset_index(drop=True)
            msg = "Firma kalıcı olarak silindi."
        write_df("Firmalar", firms)
        st.success(msg)
        st.rerun()


def products_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Ürünler")
    st.caption("Ürün kartları, renkler, fiyatlar ve stok bilgisi")
    products = data["Urunler"].copy()
    items = data["Siparis_Kalemleri"].copy()

    with st.expander("+ Yeni ürün ekle", expanded=True):
        with st.form("add_product", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                pname = st.text_input("Ürün adı *")
                model = st.text_input("Model")
                category = st.text_input("Kategori", value="")
            with c2:
                color = st.text_input("Renk")
                price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=0.0)
            with c3:
                stock = st.number_input("Stok", min_value=0, step=1, value=0)
                note = st.text_area("Not", height=96)
            if st.form_submit_button("Ürünü kaydet", use_container_width=True):
                if not pname.strip():
                    st.error("Ürün adı zorunlu.")
                else:
                    new_id = make_id("U", products["Urun_ID"] if "Urun_ID" in products else pd.Series(dtype=str))
                    new_row = {
                        "Urun_ID": new_id, "Kategori": category.strip(), "Urun_Adi": pname.strip(),
                        "Model": model.strip(), "Renk": color.strip(), "Birim_Fiyat": str(price),
                        "Stok": str(stock), "Durum": "Aktif", "Not": note.strip(), "Kayit_Tarihi": today_str(),
                    }
                    products = pd.concat([products, pd.DataFrame([new_row])], ignore_index=True)
                    write_df("Urunler", products)
                    st.success("Ürün kaydedildi ve Google Sheets'e yazıldı.")
                    st.rerun()

    st.markdown("## Kayıtlı Ürünler")
    display = products.copy()
    if not display.empty:
        display["Birim_Fiyat"] = display["Birim_Fiyat"].apply(fmt_money)
    show_df(display, height=320)

    st.markdown("## Ürün Düzelt / Sil")
    if products.empty:
        st.info("Düzenlenecek ürün yok.")
        return
    labels = {f"{r.Urun_ID} - {r.Urun_Adi} / {r.Renk} / {r.Model}": i for i, r in products.iterrows()}
    selected = st.selectbox("Ürün seç", list(labels.keys()))
    idx = labels[selected]
    row = products.loc[idx]
    with st.form("edit_product"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_name = st.text_input("Ürün adı", row["Urun_Adi"])
            e_model = st.text_input("Model", row["Model"])
            e_category = st.text_input("Kategori", row["Kategori"])
        with c2:
            e_color = st.text_input("Renk", row["Renk"])
            e_price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=float(money_to_float(row["Birim_Fiyat"])))
        with c3:
            e_stock = st.number_input("Stok", min_value=0, step=1, value=int(money_to_float(row["Stok"])))
            e_status = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if row["Durum"] == "Aktif" else 1)
            e_note = st.text_area("Not", row["Not"], height=80)
        csave, cdelete = st.columns(2)
        save = csave.form_submit_button("Güncelle", use_container_width=True)
        delete = cdelete.form_submit_button("Sil / Pasife al", use_container_width=True)
    if save:
        products.loc[idx, ["Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Durum", "Not"]] = [
            e_category.strip(), e_name.strip(), e_model.strip(), e_color.strip(), str(e_price), str(e_stock), e_status, e_note.strip()
        ]
        write_df("Urunler", products)
        st.success("Ürün güncellendi.")
        st.rerun()
    if delete:
        used = False
        if not items.empty:
            used = (items["Urun_ID"].astype(str) == str(row["Urun_ID"])).any()
        if used:
            products.loc[idx, "Durum"] = "Pasif"
            msg = "Ürün geçmiş siparişlerde kullanıldığı için silinmedi, pasife alındı."
        else:
            products = products.drop(index=idx).reset_index(drop=True)
            msg = "Ürün kalıcı olarak silindi."
        write_df("Urunler", products)
        st.success(msg)
        st.rerun()


def new_order_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Yeni Sipariş")
    st.caption("Firma seçin, ürünleri ekleyin, siparişi Google Sheets'e kaydedin")
    firms = active_firms(data)
    products = active_products(data)
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()

    if firms.empty:
        st.warning("Önce Firmalar sekmesinden en az bir firma ekleyin.")
        return
    if products.empty:
        st.warning("Önce Ürünler sekmesinden en az bir ürün ekleyin.")
        return

    if "cart" not in st.session_state:
        st.session_state.cart = []

    st.markdown("## Sipariş Bilgileri")
    c1, c2, c3 = st.columns(3)
    firm_options = {f"{r.Firma_ID} - {r.Firma_Adi} / {r.Sube}": i for i, r in firms.iterrows()}
    with c1:
        firm_label = st.selectbox("Firma / Şube", list(firm_options.keys()))
        order_date = st.date_input("Sipariş tarihi", value=date.today())
    with c2:
        delivery_date = st.date_input("Tahmini teslim tarihi", value=date.today())
        status = st.selectbox("Sipariş durumu", ORDER_STATUS)
    with c3:
        pay_status = st.selectbox("Ödeme durumu", PAYMENT_STATUS)
        creator = st.text_input("Oluşturan", value=st.session_state.get("username", "admin"))
    ship_note = st.text_area("Sevkiyat notu", height=80)
    general_note = st.text_area("Genel not", height=80)

    st.markdown("## Ürün Kalemi Ekle")
    prod_options = {f"{r.Urun_ID} - {r.Urun_Adi} / {r.Renk} / {r.Model}": i for i, r in products.iterrows()}
    p1, p2, p3, p4 = st.columns([2.2, .7, .9, .8])
    with p1:
        product_label = st.selectbox("Ürün", list(prod_options.keys()))
    prod_row = products.loc[prod_options[product_label]]
    with p2:
        qty = st.number_input("Adet", min_value=1, step=1, value=1)
    with p3:
        unit_price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=float(money_to_float(prod_row["Birim_Fiyat"])))
    with p4:
        st.metric("Satır toplamı", fmt_money(qty * unit_price))
    item_note = st.text_input("Kalem notu")
    if st.button("+ Kalemi sepete ekle", use_container_width=True):
        st.session_state.cart.append({
            "Urun_ID": prod_row["Urun_ID"], "Urun_Adi": prod_row["Urun_Adi"], "Model": prod_row["Model"], "Renk": prod_row["Renk"],
            "Adet": int(qty), "Birim_Fiyat": float(unit_price), "Satir_Toplam": float(qty * unit_price), "Not": item_note.strip()
        })
        st.rerun()

    st.markdown("## Sepet")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        disp = cart_df.copy()
        disp["Birim_Fiyat"] = disp["Birim_Fiyat"].apply(fmt_money)
        disp["Satir_Toplam"] = disp["Satir_Toplam"].apply(fmt_money)
        show_df(disp, height=240)
        total = cart_df["Satir_Toplam"].sum()
        st.markdown(f"### Sipariş toplamı: {fmt_money(total)}")
        csave, cclear = st.columns(2)
        if cclear.button("Sepeti temizle", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
        if csave.button("Siparişi kaydet", use_container_width=True):
            firm_row = firms.loc[firm_options[firm_label]]
            order_no = make_order_no(orders["Siparis_No"] if "Siparis_No" in orders else pd.Series(dtype=str))
            order_row = {
                "Siparis_No": order_no, "Firma_ID": firm_row["Firma_ID"], "Firma_Adi": firm_row["Firma_Adi"], "Sube": firm_row["Sube"],
                "Siparis_Tarihi": str(order_date), "Teslim_Tarihi": str(delivery_date), "Durum": status,
                "Odeme_Durumu": pay_status, "Sevkiyat_Notu": ship_note.strip(), "Genel_Not": general_note.strip(),
                "Olusturan": creator.strip(), "Toplam_Tutar": str(total), "Kayit_Tarihi": now_str(),
            }
            orders = pd.concat([orders, pd.DataFrame([order_row])], ignore_index=True)
            new_items = []
            for cart_item in st.session_state.cart:
                new_items.append({
                    "Kalem_ID": make_id("K", pd.concat([items["Kalem_ID"] if "Kalem_ID" in items else pd.Series(dtype=str), pd.Series([x.get("Kalem_ID", "") for x in new_items])], ignore_index=True)),
                    "Siparis_No": order_no,
                    **cart_item,
                })
            items = pd.concat([items, pd.DataFrame(new_items)], ignore_index=True)
            write_df("Siparisler", orders)
            write_df("Siparis_Kalemleri", items)
            st.session_state.cart = []
            st.success(f"{order_no} numaralı sipariş kaydedildi.")
            st.rerun()
    else:
        st.info("Sepete henüz ürün eklenmedi.")


def orders_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Siparişler")
    st.caption("Siparişleri filtreleyin, durum ve ödeme bilgisini güncelleyin")
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    if orders.empty:
        st.info("Henüz sipariş yok.")
        return

    f1, f2, f3 = st.columns(3)
    with f1:
        q = st.text_input("Firma ara")
    with f2:
        status_filter = st.selectbox("Durum filtresi", ["Tümü"] + ORDER_STATUS)
    with f3:
        pay_filter = st.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_STATUS)
    view = orders.copy()
    if q.strip():
        view = view[view["Firma_Adi"].str.contains(q.strip(), case=False, na=False)]
    if status_filter != "Tümü":
        view = view[view["Durum"] == status_filter]
    if pay_filter != "Tümü":
        view = view[view["Odeme_Durumu"] == pay_filter]
    disp = view.copy()
    disp["Toplam_Tutar"] = disp["Toplam_Tutar"].apply(fmt_money)
    show_df(disp[["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Sevkiyat_Notu"]], height=360)

    st.markdown("## Sipariş Detayı / Güncelleme")
    labels = {f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}": i for i, r in orders.iterrows()}
    selected = st.selectbox("Sipariş seç", list(labels.keys()))
    idx = labels[selected]
    row = orders.loc[idx]
    order_items = items[items["Siparis_No"] == row["Siparis_No"]].copy()
    if not order_items.empty:
        idisp = order_items.copy()
        idisp["Birim_Fiyat"] = idisp["Birim_Fiyat"].apply(fmt_money)
        idisp["Satir_Toplam"] = idisp["Satir_Toplam"].apply(fmt_money)
        show_df(idisp, height=220)
    with st.form("update_order"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_status = st.selectbox("Durum", ORDER_STATUS, index=ORDER_STATUS.index(row["Durum"]) if row["Durum"] in ORDER_STATUS else 0)
        with c2:
            new_pay = st.selectbox("Ödeme durumu", PAYMENT_STATUS, index=PAYMENT_STATUS.index(row["Odeme_Durumu"]) if row["Odeme_Durumu"] in PAYMENT_STATUS else 0)
        with c3:
            new_delivery = st.text_input("Teslim tarihi", row["Teslim_Tarihi"])
        new_ship_note = st.text_area("Sevkiyat notu", row["Sevkiyat_Notu"], height=80)
        new_general_note = st.text_area("Genel not", row["Genel_Not"], height=80)
        csave, cdelete = st.columns(2)
        save = csave.form_submit_button("Siparişi güncelle", use_container_width=True)
        delete = cdelete.form_submit_button("Siparişi kalıcı sil", use_container_width=True)
    if save:
        orders.loc[idx, ["Durum", "Odeme_Durumu", "Teslim_Tarihi", "Sevkiyat_Notu", "Genel_Not"]] = [
            new_status, new_pay, new_delivery.strip(), new_ship_note.strip(), new_general_note.strip()
        ]
        write_df("Siparisler", orders)
        st.success("Sipariş güncellendi.")
        st.rerun()
    if delete:
        sip_no = row["Siparis_No"]
        orders = orders.drop(index=idx).reset_index(drop=True)
        items = items[items["Siparis_No"] != sip_no].reset_index(drop=True)
        payments = payments[payments["Siparis_No"] != sip_no].reset_index(drop=True)
        write_df("Siparisler", orders)
        write_df("Siparis_Kalemleri", items)
        write_df("Odemeler", payments)
        st.success("Sipariş, kalemleri ve ödemeleri kalıcı olarak silindi.")
        st.rerun()


def payments_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Ödemeler")
    st.caption("Tahsilat kaydı ekleyin ve hatalı ödemeleri silin")
    orders = data["Siparisler"].copy()
    payments = data["Odemeler"].copy()
    if orders.empty:
        st.info("Ödeme eklemek için önce sipariş oluşturun.")
        return
    st.markdown("## Yeni Ödeme")
    labels = {f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}": i for i, r in orders.iterrows()}
    with st.form("add_payment", clear_on_submit=True):
        selected = st.selectbox("Sipariş", list(labels.keys()))
        idx = labels[selected]
        row = orders.loc[idx]
        c1, c2, c3 = st.columns(3)
        with c1:
            odeme_tarihi = st.date_input("Ödeme tarihi", value=date.today())
        with c2:
            tutar = st.number_input("Tutar", min_value=0.0, step=100.0, value=0.0)
        with c3:
            tip = st.selectbox("Ödeme tipi", PAYMENT_TYPES)
        aciklama = st.text_area("Açıklama", height=80)
        if st.form_submit_button("Ödemeyi kaydet", use_container_width=True):
            if tutar <= 0:
                st.error("Tutar 0'dan büyük olmalı.")
            else:
                new_id = make_id("O", payments["Odeme_ID"] if "Odeme_ID" in payments else pd.Series(dtype=str))
                new_row = {
                    "Odeme_ID": new_id, "Siparis_No": row["Siparis_No"], "Firma_Adi": row["Firma_Adi"],
                    "Odeme_Tarihi": str(odeme_tarihi), "Tutar": str(tutar), "Odeme_Tipi": tip,
                    "Aciklama": aciklama.strip(), "Kayit_Tarihi": now_str(),
                }
                payments = pd.concat([payments, pd.DataFrame([new_row])], ignore_index=True)
                write_df("Odemeler", payments)
                st.success("Ödeme kaydedildi.")
                st.rerun()

    st.markdown("## Kayıtlı Ödemeler")
    disp = payments.copy()
    if not disp.empty:
        disp["Tutar"] = disp["Tutar"].apply(fmt_money)
    show_df(disp, height=320)

    st.markdown("## Ödeme Sil")
    if payments.empty:
        st.info("Silinecek ödeme yok.")
        return
    labels_p = {f"{r.Odeme_ID} - {r.Siparis_No} / {fmt_money(r.Tutar)}": i for i, r in payments.iterrows()}
    selected_p = st.selectbox("Ödeme seç", list(labels_p.keys()))
    if st.button("Seçili ödemeyi kalıcı sil", use_container_width=True):
        payments = payments.drop(index=labels_p[selected_p]).reset_index(drop=True)
        write_df("Odemeler", payments)
        st.success("Ödeme silindi.")
        st.rerun()


def reports_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Raporlar")
    st.caption("Firma, ürün, ödeme ve sipariş raporları")
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    if not orders.empty:
        orders["Toplam_Tutar_Num"] = orders["Toplam_Tutar"].apply(money_to_float)
    if not items.empty:
        items["Adet_Num"] = items["Adet"].apply(money_to_float)
        items["Satir_Toplam_Num"] = items["Satir_Toplam"].apply(money_to_float)
    if not payments.empty:
        payments["Tutar_Num"] = payments["Tutar"].apply(money_to_float)

    st.markdown("## Firma Bazlı Satış")
    if orders.empty:
        st.info("Rapor için sipariş yok.")
    else:
        firm_report = orders.groupby("Firma_Adi", as_index=False).agg(Siparis_Adedi=("Siparis_No", "count"), Toplam_Ciro=("Toplam_Tutar_Num", "sum"))
        firm_report["Toplam_Ciro"] = firm_report["Toplam_Ciro"].apply(fmt_money)
        show_df(firm_report, height=260)
        chart = firm_report.copy()
        chart["Toplam_Ciro_Num"] = chart["Toplam_Ciro"].apply(money_to_float)
        st.bar_chart(chart, x="Firma_Adi", y="Toplam_Ciro_Num", use_container_width=True)

    st.markdown("## Ürün Bazlı Satış")
    if items.empty:
        st.info("Rapor için sipariş kalemi yok.")
    else:
        product_report = items.groupby("Urun_Adi", as_index=False).agg(Toplam_Adet=("Adet_Num", "sum"), Toplam_Tutar=("Satir_Toplam_Num", "sum"))
        product_report["Toplam_Tutar"] = product_report["Toplam_Tutar"].apply(fmt_money)
        show_df(product_report, height=260)
        chart2 = product_report.copy()
        st.bar_chart(chart2, x="Urun_Adi", y="Toplam_Adet", use_container_width=True)

    st.markdown("## Excel Dışa Aktar")
    excel_data = export_excel(data)
    st.download_button("Tüm verileri indir (Excel)", data=excel_data, file_name=f"gundays_home_yedek_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def export_excel(data: Dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data.items():
            if name in SCHEMAS:
                normalize_df(df, name).to_excel(writer, index=False, sheet_name=name[:31])
    return output.getvalue()


def settings_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Yedek / Ayarlar")
    st.caption("Google Sheets bağlantısı, tablo onarımı, Excel yedek ve şifre değişimi")
    try:
        # Basit bağlantı kontrolü
        _ = get_spreadsheet().title
        success("Google Sheets bağlantısı aktif.")
        st.code(f"SPREADSHEET_ID = {SPREADSHEET_ID}")
    except Exception as e:
        error_box("Google Sheets bağlantısı kurulamadı.")
        st.exception(e)
        return

    st.markdown("## Tablo Bakım")
    warn("Bu butona sadece başlıklar kaydıysa veya veriler ekranda bozuk görünüyorsa bas. Normal kullanımda gerek yok.")
    c1, c2 = st.columns(2)
    if c1.button("Tabloları onar ve temizle", use_container_width=True):
        repair_all_sheets()
        st.success("Tablolar standart şemaya göre onarıldı ve temizlendi.")
        st.rerun()
    if c2.button("Verileri yenile", use_container_width=True):
        clear_data_cache()
        st.success("Önbellek temizlendi. Veriler yeniden okunacak.")
        st.rerun()

    st.markdown("## Excel Yedeği İndir")
    st.download_button("Tüm verileri indir (Excel)", data=export_excel(data), file_name=f"gundays_home_yedek_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown("## Şifre Değiştir")
    with st.form("change_pw"):
        old = st.text_input("Mevcut şifre", type="password")
        new = st.text_input("Yeni şifre", type="password")
        new2 = st.text_input("Yeni şifre tekrar", type="password")
        if st.form_submit_button("Şifreyi değiştir", use_container_width=True):
            users = data["Kullanicilar"].copy()
            username = st.session_state.get("username", "admin")
            ok, _ = authenticate(data, username, old)
            if not ok:
                st.error("Mevcut şifre hatalı.")
            elif not new or new != new2:
                st.error("Yeni şifreler eşleşmiyor.")
            else:
                if users.empty or not (users["Kullanici_Adi"] == username).any():
                    users = pd.DataFrame([{"Kullanici_Adi": username, "Sifre_Hash": hash_pw(new), "Rol": "Admin", "Aktif": "Aktif", "Kayit_Tarihi": today_str()}], columns=SCHEMAS["Kullanicilar"])
                else:
                    users.loc[users["Kullanici_Adi"] == username, "Sifre_Hash"] = hash_pw(new)
                write_df("Kullanicilar", users)
                st.success("Şifre değiştirildi.")

# -------------------------
# Ana akış
# -------------------------
def main() -> None:
    inject_css()
    try:
        data = load_all_data()
    except Exception as e:
        error_box("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
        st.exception(e)
        return

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login_page(data)
        return

    with st.sidebar:
        st.markdown("## Günday's Home")
        st.caption(f"Kullanıcı: {st.session_state.get('username', 'admin')} / {st.session_state.get('role', 'Admin')}")
        pages = {
            "Dashboard": dashboard_page,
            "Yeni Sipariş": new_order_page,
            "Siparişler": orders_page,
            "Firmalar": firms_page,
            "Ürünler": products_page,
            "Ödemeler": payments_page,
            "Raporlar": reports_page,
            "Yedek / Ayarlar": settings_page,
        }
        choice = st.radio("", list(pages.keys()), label_visibility="collapsed")
        st.divider()
        if st.button("Çıkış yap", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    pages[choice](data)

if __name__ == "__main__":
    main()
