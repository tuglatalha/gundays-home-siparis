import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from io import BytesIO
import hashlib
import re
import uuid

st.set_page_config(
    page_title="Günday's Home Sipariş Takip",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# PREMIUM THEME
# ============================================================
st.markdown(
    """
    <style>
    :root{
        --bg:#050914; --panel:#0b1220; --panel2:#111827; --gold:#d6a84f; --gold2:#f5d77d;
        --text:#f8fafc; --muted:#cbd5e1; --line:rgba(214,168,79,.32); --red:#ff4b4b;
    }
    .stApp{
        background:
          radial-gradient(circle at 8% 2%, rgba(214,168,79,.18), transparent 23%),
          radial-gradient(circle at 96% 16%, rgba(37,99,235,.16), transparent 28%),
          linear-gradient(135deg,#050914 0%,#091120 48%,#05070d 100%) !important;
        color:var(--text)!important;
    }
    .block-container{padding-top:2.5rem!important; padding-bottom:4rem!important; max-width: 1600px!important;}
    [data-testid="stSidebar"]{
        background:linear-gradient(180deg,#070d19 0%,#111827 58%,#050914 100%)!important;
        border-right:1px solid var(--line)!important;
        box-shadow:12px 0 48px rgba(0,0,0,.33)!important;
    }
    [data-testid="stSidebar"] *{color:#f8fafc!important;}
    h1,h2,h3,h4,p,label,span,div{color:inherit;}
    .main-title{font-size:34px;font-weight:950;letter-spacing:-.8px;margin-bottom:2px;color:#fff!important;}
    .sub-title{color:var(--muted)!important;font-size:14px;margin-top:0;}
    .metric-card{
        padding:22px 22px;border-radius:18px;min-height:128px;
        background:linear-gradient(145deg,rgba(214,168,79,.15),rgba(15,23,42,.98) 38%,rgba(17,24,39,.92))!important;
        border:1px solid rgba(214,168,79,.48)!important;
        box-shadow:0 18px 50px rgba(0,0,0,.36), inset 0 1px 0 rgba(255,255,255,.06)!important;
    }
    .metric-label{color:#e2e8f0!important;font-size:13px;font-weight:900;margin-bottom:10px;}
    .metric-value{color:#fff!important;font-size:31px;font-weight:950;line-height:1.05;}
    .metric-foot{color:var(--gold2)!important;font-size:12px;font-weight:800;margin-top:10px;}
    .stButton>button,.stDownloadButton>button{
        border-radius:12px!important;border:1px solid rgba(214,168,79,.55)!important;
        background:linear-gradient(135deg,rgba(214,168,79,.20),rgba(15,23,42,.90))!important;
        color:#fff!important;font-weight:850!important;
    }
    .stButton>button:hover,.stDownloadButton>button:hover{border-color:#f5d77d!important;box-shadow:0 8px 28px rgba(214,168,79,.18)!important;}
    div[data-testid="stDataFrame"]{border:1px solid rgba(255,255,255,.10);border-radius:16px;overflow:hidden;}
    .success-box{background:rgba(22,101,52,.42);border:1px solid rgba(74,222,128,.28);padding:14px 16px;border-radius:14px;color:#bbf7d0!important;font-weight:800;}
    .warn-box{background:rgba(120,53,15,.32);border:1px solid rgba(251,191,36,.32);padding:14px 16px;border-radius:14px;color:#fde68a!important;font-weight:800;}
    .danger-box{background:rgba(127,29,29,.26);border:1px solid rgba(248,113,113,.34);padding:14px 16px;border-radius:14px;color:#fecaca!important;font-weight:800;}
    .small-muted{color:#94a3b8!important;font-size:12px;}
    .gold{color:var(--gold2)!important;}
    hr{border-color:rgba(255,255,255,.10)!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONSTANTS & SCHEMA
# ============================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

SCHEMAS = {
    "Firmalar": ["Firma_ID", "Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres", "Vergi_No_VKN", "Vergi_Dairesi", "Not", "Aktif", "Kayit_Tarihi"],
    "Urunler": ["Urun_ID", "Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Durum", "Not", "Kayit_Tarihi"],
    "Siparisler": ["Siparis_ID", "Siparis_No", "Firma_ID", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar", "Sevkiyat_Notu", "Genel_Not", "Olusturan", "Kayit_Tarihi", "Guncelleme_Tarihi"],
    "Siparis_Kalemleri": ["Kalem_ID", "Siparis_ID", "Siparis_No", "Urun_ID", "Urun_Adi", "Model", "Renk", "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"],
    "Odemeler": ["Odeme_ID", "Siparis_ID", "Siparis_No", "Firma_Adi", "Odeme_Tarihi", "Tutar", "Odeme_Tipi", "Not", "Kayit_Tarihi"],
    "Kullanicilar": ["Kullanici_Adi", "Sifre", "Rol", "Aktif", "Kayit_Tarihi"],
    "Listeler": ["Tip", "Deger", "Sira"],
}

KEY_COLS = {
    "Firmalar": ["Firma_ID", "Firma_Adi"],
    "Urunler": ["Urun_ID", "Urun_Adi"],
    "Siparisler": ["Siparis_ID", "Siparis_No", "Firma_Adi"],
    "Siparis_Kalemleri": ["Kalem_ID", "Siparis_No", "Urun_Adi"],
    "Odemeler": ["Odeme_ID", "Siparis_No", "Tutar"],
    "Kullanicilar": ["Kullanici_Adi"],
    "Listeler": ["Tip", "Deger"],
}

ORDER_STATUSES = ["Sipariş Alındı", "Üretime Aktarıldı", "Üretimde", "Hazır", "Sevkiyat Bekliyor", "Gönderildi", "Teslim Edildi", "İptal Edildi"]
PAYMENT_STATUSES = ["Bekliyor", "Kısmi Ödendi", "Ödendi", "İptal / İade"]
PAYMENT_TYPES = ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet", "Diğer"]

# ============================================================
# UTILITIES
# ============================================================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return date.today().strftime("%Y-%m-%d")


def hash_password(password: str) -> str:
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def check_password(password: str, stored: str) -> bool:
    stored = str(stored or "")
    return stored == str(password) or stored == hash_password(password)


def make_uuid(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"


def normalize_text(s: str) -> str:
    s = str(s or "").strip().lower()
    tr = str.maketrans("çğıöşüİı", "cgiosuii")
    s = s.translate(tr)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def clean_cell(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def clean_money(value) -> float:
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("TL", "").replace("₺", "").replace(" ", "").strip()
    if not s:
        return 0.0
    # Turkish format: 12.850,00 -> 12850.00
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # English/float-like or plain integer
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        digits = re.sub(r"[^0-9.-]", "", s)
        try:
            return float(digits) if digits else 0.0
        except Exception:
            return 0.0


def clean_int(value) -> int:
    try:
        return int(round(clean_money(value)))
    except Exception:
        return 0


def fmt_tl(value) -> str:
    value = clean_money(value)
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def safe_df(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=cols or [])
    out = df.copy()
    if cols:
        for c in cols:
            if c not in out.columns:
                out[c] = ""
        out = out[cols]
    out.columns = [str(c) for c in out.columns]
    # guarantee unique column names for Streamlit/PyArrow
    seen = {}
    new_cols = []
    for c in out.columns:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    out.columns = new_cols
    return out.fillna("")


def numeric_cols(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].apply(clean_money)
    return out


def next_simple_id(df: pd.DataFrame, col: str, prefix: str) -> str:
    nums = []
    if df is not None and col in df.columns:
        for val in df[col].dropna().astype(str):
            m = re.search(r"(\d+)$", val)
            if m:
                nums.append(int(m.group(1)))
    return f"{prefix}-{(max(nums) + 1 if nums else 1):04d}"


def next_order_no(orders: pd.DataFrame) -> str:
    year = datetime.now().year
    nums = []
    if orders is not None and "Siparis_No" in orders.columns:
        for val in orders["Siparis_No"].dropna().astype(str):
            m = re.search(rf"GH-{year}-(\d+)$", val)
            if m:
                nums.append(int(m.group(1)))
    return f"GH-{year}-{(max(nums) + 1 if nums else 1):04d}"

# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client():
    if "SPREADSHEET_ID" not in st.secrets or "gcp_service_account" not in st.secrets:
        raise RuntimeError("Secrets eksik: SPREADSHEET_ID ve [gcp_service_account] gerekli.")
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and "\\n" in str(info["private_key"]):
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    return get_client().open_by_key(st.secrets["SPREADSHEET_ID"])


def get_or_create_ws(name: str, rows=1000, cols=30):
    ss = get_spreadsheet()
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=name, rows=rows, cols=cols)


def alias_map_for(sheet: str):
    common = {
        "kayittarihi": "Kayit_Tarihi", "kayittarih": "Kayit_Tarihi", "not": "Not", "aciklama": "Not",
        "guncellemetarihi": "Guncelleme_Tarihi", "aktif": "Aktif", "durum": "Durum",
    }
    maps = {
        "Firmalar": {
            "firmaid": "Firma_ID", "firmakodu": "Firma_ID", "id": "Firma_ID",
            "firmaadi": "Firma_Adi", "firmaad": "Firma_Adi", "firma": "Firma_Adi", "musteri": "Firma_Adi", "musteriadi": "Firma_Adi",
            "sube": "Sube", "yetkili": "Yetkili_Kisi", "yetkilikisi": "Yetkili_Kisi",
            "telefon": "Telefon", "tel": "Telefon", "adres": "Adres",
            "vergino": "Vergi_No_VKN", "vkn": "Vergi_No_VKN", "vergivkn": "Vergi_No_VKN", "verginoVKN": "Vergi_No_VKN",
            "vergidairesi": "Vergi_Dairesi",
        },
        "Urunler": {
            "urunid": "Urun_ID", "urun_id": "Urun_ID", "id": "Urun_ID",
            "kategori": "Kategori", "urunkategorisi": "Kategori",
            "urunadi": "Urun_Adi", "urunad": "Urun_Adi", "urun": "Urun_Adi",
            "model": "Model", "renk": "Renk", "birimfiyat": "Birim_Fiyat", "fiyat": "Birim_Fiyat", "satisfiyati": "Birim_Fiyat",
            "stok": "Stok", "aktif": "Durum", "durum": "Durum",
        },
        "Siparisler": {
            "siparisid": "Siparis_ID", "siparisno": "Siparis_No", "siparisnumarasi": "Siparis_No", "siparis_no": "Siparis_No",
            "firmaid": "Firma_ID", "firmaadi": "Firma_Adi", "firma": "Firma_Adi", "sube": "Sube",
            "siparistarihi": "Siparis_Tarihi", "tarih": "Siparis_Tarihi", "teslimtarihi": "Teslim_Tarihi",
            "durum": "Durum", "siparisdurumu": "Durum", "odemedurumu": "Odeme_Durumu", "odeme": "Odeme_Durumu",
            "toplam": "Toplam_Tutar", "toplamtutar": "Toplam_Tutar", "ciro": "Toplam_Tutar", "tutar": "Toplam_Tutar",
            "tahsiledilen": "Tahsil_Edilen", "odenentutar": "Tahsil_Edilen", "kalantutar": "Kalan_Tutar", "kalan": "Kalan_Tutar",
            "sevkiyatnotu": "Sevkiyat_Notu", "genelnot": "Genel_Not", "olusturan": "Olusturan",
        },
        "Siparis_Kalemleri": {
            "kalemid": "Kalem_ID", "siparisid": "Siparis_ID", "siparisno": "Siparis_No",
            "urunid": "Urun_ID", "urunadi": "Urun_Adi", "urun": "Urun_Adi", "model": "Model", "renk": "Renk",
            "adet": "Adet", "birimfiyat": "Birim_Fiyat", "satirtoplami": "Satir_Toplam", "satirtoplam": "Satir_Toplam", "toplam": "Satir_Toplam",
        },
        "Odemeler": {
            "odemeid": "Odeme_ID", "siparisid": "Siparis_ID", "siparisno": "Siparis_No", "firmaadi": "Firma_Adi", "firma": "Firma_Adi",
            "odemetarihi": "Odeme_Tarihi", "tarih": "Odeme_Tarihi", "tutar": "Tutar", "odemetipi": "Odeme_Tipi", "tip": "Odeme_Tipi",
        },
        "Kullanicilar": {"kullaniciadi": "Kullanici_Adi", "kullanici": "Kullanici_Adi", "username": "Kullanici_Adi", "sifre": "Sifre", "password": "Sifre", "rol": "Rol", "aktif": "Aktif"},
        "Listeler": {"tip": "Tip", "deger": "Deger", "sira": "Sira"},
    }
    result = common.copy()
    result.update(maps.get(sheet, {}))
    for h in SCHEMAS[sheet]:
        result[normalize_text(h)] = h
    return result


def parse_sheet_values(sheet: str, values) -> pd.DataFrame:
    headers = SCHEMAS[sheet]
    if not values:
        return pd.DataFrame(columns=headers)
    amap = alias_map_for(sheet)
    best_idx, best_score = 0, -1
    for i, row in enumerate(values[:10]):
        mapped = [amap.get(normalize_text(c), "") for c in row]
        score = len([m for m in mapped if m in headers])
        if score > best_score:
            best_idx, best_score = i, score
    # If no sensible header is found, use schema as header and try rows after first row.
    header_row = values[best_idx] if best_score > 0 else headers
    mapped_headers = []
    seen = set()
    for h in header_row:
        canon = amap.get(normalize_text(h), "")
        if canon in headers and canon not in seen:
            mapped_headers.append(canon)
            seen.add(canon)
        else:
            mapped_headers.append(None)
    start = best_idx + 1 if best_score > 0 else 1
    records = []
    for row in values[start:]:
        rec = {h: "" for h in headers}
        for j, cell in enumerate(row):
            if j < len(mapped_headers) and mapped_headers[j]:
                rec[mapped_headers[j]] = clean_cell(cell)
        # Drop repeated header rows and blank/no-key rows
        key_values = [rec.get(k, "") for k in KEY_COLS.get(sheet, [])]
        if not any(str(v).strip() for v in key_values):
            continue
        if any(normalize_text(rec.get(k, "")) == normalize_text(k) for k in KEY_COLS.get(sheet, [])):
            continue
        records.append(rec)
    df = pd.DataFrame(records, columns=headers)
    return df.fillna("")


def worksheet_needs_repair(sheet: str, values) -> bool:
    headers = SCHEMAS[sheet]
    if not values:
        return True
    first = [clean_cell(x) for x in values[0][:len(headers)]]
    return first != headers or len(values[0]) != len(set(values[0]))


def write_sheet_df(sheet: str, df: pd.DataFrame):
    ws = get_or_create_ws(sheet)
    headers = SCHEMAS[sheet]
    if df is None:
        df = pd.DataFrame(columns=headers)
    out = df.copy()
    for h in headers:
        if h not in out.columns:
            out[h] = ""
    out = out[headers].fillna("").astype(str)
    values = [headers] + out.values.tolist()
    ws.clear()
    if values:
        ws.update(values, value_input_option="USER_ENTERED")


def ensure_and_repair_schema(force=False):
    if st.session_state.get("schema_checked") and not force:
        return
    for sheet, headers in SCHEMAS.items():
        ws = get_or_create_ws(sheet, rows=1000, cols=max(30, len(headers)+5))
        values = ws.get_all_values()
        df = parse_sheet_values(sheet, values)
        # Default admin user if users sheet empty
        if sheet == "Kullanicilar" and df.empty:
            df = pd.DataFrame([{
                "Kullanici_Adi": "admin",
                "Sifre": hash_password("admin123"),
                "Rol": "Admin",
                "Aktif": "Aktif",
                "Kayit_Tarihi": now_str(),
            }], columns=headers)
        if worksheet_needs_repair(sheet, values) or force:
            write_sheet_df(sheet, df)
    st.session_state["schema_checked"] = True
    clear_data_cache()


@st.cache_data(ttl=90, show_spinner=False)
def load_data_cached(_token=0):
    data = {}
    for sheet in SCHEMAS:
        ws = get_or_create_ws(sheet)
        values = ws.get_all_values()
        data[sheet] = parse_sheet_values(sheet, values)
    return data


def clear_data_cache():
    try:
        load_data_cached.clear()
    except Exception:
        pass
    st.session_state["data_token"] = st.session_state.get("data_token", 0) + 1


def get_data():
    ensure_and_repair_schema()
    return load_data_cached(st.session_state.get("data_token", 0))


def save_sheet(sheet: str, df: pd.DataFrame):
    write_sheet_df(sheet, df)
    clear_data_cache()

# ============================================================
# BUSINESS HELPERS
# ============================================================
def active_firms(firms: pd.DataFrame) -> pd.DataFrame:
    if firms is None or firms.empty:
        return pd.DataFrame(columns=SCHEMAS["Firmalar"])
    out = firms.copy().fillna("")
    out = out[out["Firma_Adi"].astype(str).str.strip() != ""]
    if "Aktif" in out.columns:
        out = out[~out["Aktif"].astype(str).str.lower().isin(["pasif", "hayır", "hayir", "0", "false"])]
    return out


def active_products(products: pd.DataFrame) -> pd.DataFrame:
    if products is None or products.empty:
        return pd.DataFrame(columns=SCHEMAS["Urunler"])
    out = products.copy().fillna("")
    out = out[out["Urun_Adi"].astype(str).str.strip() != ""]
    if "Durum" in out.columns:
        out = out[~out["Durum"].astype(str).str.lower().isin(["pasif", "hayır", "hayir", "0", "false"])]
    return out


def recalc_orders(orders: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    if orders is None or orders.empty:
        return pd.DataFrame(columns=SCHEMAS["Siparisler"])
    out = orders.copy().fillna("")
    for col in ["Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar"]:
        out[col] = out[col].apply(clean_money) if col in out.columns else 0.0
    if payments is not None and not payments.empty:
        p = payments.copy().fillna("")
        p["Tutar"] = p["Tutar"].apply(clean_money)
        pay_by_order = p.groupby("Siparis_ID")["Tutar"].sum().to_dict() if "Siparis_ID" in p.columns else {}
    else:
        pay_by_order = {}
    for idx, row in out.iterrows():
        paid = pay_by_order.get(str(row.get("Siparis_ID", "")), clean_money(row.get("Tahsil_Edilen", 0)))
        total = clean_money(row.get("Toplam_Tutar", 0))
        out.at[idx, "Tahsil_Edilen"] = paid
        out.at[idx, "Kalan_Tutar"] = max(total - paid, 0)
        if total > 0:
            if paid <= 0 and str(row.get("Odeme_Durumu", "")).strip() in ["", "Ödendi", "Kısmi Ödendi"]:
                out.at[idx, "Odeme_Durumu"] = "Bekliyor"
            elif 0 < paid < total:
                out.at[idx, "Odeme_Durumu"] = "Kısmi Ödendi"
            elif paid >= total:
                out.at[idx, "Odeme_Durumu"] = "Ödendi"
    return out


def orders_for_display(orders: pd.DataFrame, payments: pd.DataFrame = None) -> pd.DataFrame:
    out = recalc_orders(orders, payments) if payments is not None else orders.copy()
    if out is None or out.empty:
        return pd.DataFrame(columns=["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar"])
    out = out[out["Siparis_No"].astype(str).str.strip() != ""]
    return out


def to_excel_bytes(sheets: dict) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_df(df).to_excel(writer, index=False, sheet_name=str(name)[:31])
    return output.getvalue()


def rerun_success(msg: str):
    st.success(msg)
    st.rerun()

# ============================================================
# AUTH
# ============================================================
def login_screen():
    st.markdown('<div class="main-title">Günday\'s Home Sipariş Takip</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Sipariş, firma, ürün, ödeme ve sevkiyat durumlarını tek panelden yönetin.</p>', unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.35, 1])
    with center:
        st.markdown("## Yönetim Paneli Girişi")
        with st.form("login_form"):
            u = st.text_input("Kullanıcı adı")
            p = st.text_input("Şifre", type="password")
            ok = st.form_submit_button("Giriş yap", use_container_width=True)
        st.info("İlk kurulum bilgisi: admin / admin123. Yayına almadan önce şifreyi değiştirin.")
        if ok:
            try:
                ensure_and_repair_schema()
                users = get_data()["Kullanicilar"].copy().fillna("")
                users = users[users["Aktif"].astype(str).str.lower().isin(["aktif", "true", "1", "evet", "yes"])]
                matched = users[users["Kullanici_Adi"].astype(str).str.strip() == str(u).strip()]
                if not matched.empty and check_password(p, matched.iloc[0].get("Sifre", "")):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = str(u).strip()
                    st.session_state["role"] = matched.iloc[0].get("Rol", "Admin") or "Admin"
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
            except Exception as e:
                st.error("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
                st.exception(e)

# ============================================================
# LAYOUT HELPERS
# ============================================================
def metric_card(label, value, foot=""):
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_menu():
    with st.sidebar:
        st.markdown("### Günday's Home")
        st.caption(f"Kullanıcı: {st.session_state.get('username','admin')} / {st.session_state.get('role','Admin')}")
        pages = ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Ödemeler", "Raporlar", "Yedek / Ayarlar"]
        page = st.radio("", pages, label_visibility="collapsed")
        st.markdown("---")
        if st.button("Çıkış yap", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    return page

# ============================================================
# PAGES
# ============================================================
def dashboard_page(data):
    st.markdown('<div class="main-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Günday\'s Home genel sipariş özeti</p>', unsafe_allow_html=True)
    orders = orders_for_display(data["Siparisler"], data["Odemeler"])
    orders_num = numeric_cols(orders, ["Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar"])
    valid_orders = orders_num[~orders_num["Durum"].astype(str).isin(["İptal Edildi"])] if not orders_num.empty else orders_num
    total_orders = len(orders_num)
    active_orders = len(valid_orders[~valid_orders["Durum"].astype(str).isin(["Teslim Edildi", "İptal Edildi"])]) if not valid_orders.empty else 0
    ciro = valid_orders["Toplam_Tutar"].sum() if "Toplam_Tutar" in valid_orders.columns else 0
    pending = valid_orders["Kalan_Tutar"].sum() if "Kalan_Tutar" in valid_orders.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Toplam Sipariş", total_orders, "Tüm kayıtlar")
    with c2: metric_card("Aktif Sipariş", active_orders, "Teslim/iptal hariç")
    with c3: metric_card("Ciro", fmt_tl(ciro), "Sipariş toplamı")
    with c4: metric_card("Ödeme Bekleyen", fmt_tl(pending), "Kalan tahsilat")
    st.markdown("---")

    left, right = st.columns([1.05, .95])
    with left:
        st.markdown("## Son Siparişler")
        if orders.empty:
            st.info("Henüz sipariş bulunmuyor.")
        else:
            show = orders.sort_values("Kayit_Tarihi", ascending=False).head(10)
            show = show[["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar"]].copy()
            show["Toplam_Tutar"] = show["Toplam_Tutar"].apply(fmt_tl)
            st.dataframe(safe_df(show), use_container_width=True, hide_index=True)
    with right:
        st.markdown("## Durum Dağılımı")
        if orders.empty:
            st.info("Grafik için veri yok.")
        else:
            status_df = orders.groupby("Durum").size().reset_index(name="Adet")
            status_df = status_df[status_df["Durum"].astype(str).str.strip() != ""]
            if status_df.empty:
                st.info("Grafik için veri yok.")
            else:
                st.bar_chart(status_df.set_index("Durum"))
    st.markdown("## Hızlı Uyarılar")
    if pending > 0:
        st.markdown(f'<div class="warn-box">Bekleyen tahsilat: {fmt_tl(pending)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-box">Şu an kritik uyarı yok.</div>', unsafe_allow_html=True)


def new_order_page(data):
    st.markdown('<div class="main-title">Yeni Sipariş</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Firma seçin, ürünleri sepete ekleyin, siparişi Google Sheets\'e kaydedin</p>', unsafe_allow_html=True)
    firms = active_firms(data["Firmalar"])
    products = active_products(data["Urunler"])

    if "cart" not in st.session_state:
        st.session_state["cart"] = []

    if firms.empty:
        st.warning("Önce Firmalar sekmesinden en az bir firma eklemelisin.")
        return
    if products.empty:
        st.warning("Önce Ürünler sekmesinden en az bir ürün eklemelisin.")
        return

    firm_options = []
    firm_map = {}
    for _, r in firms.iterrows():
        label = f"{r['Firma_ID']} | {r['Firma_Adi']}" + (f" - {r['Sube']}" if str(r.get('Sube','')).strip() else "")
        firm_options.append(label)
        firm_map[label] = r.to_dict()

    st.markdown("## Sipariş Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        firm_label = st.selectbox("Firma / Şube", firm_options)
        selected_firm = firm_map[firm_label]
    with c2:
        teslim = st.date_input("Tahmini teslim tarihi", value=date.today())
        status = st.selectbox("Sipariş durumu", ORDER_STATUSES, index=0)
    with c3:
        payment_status = st.selectbox("Ödeme durumu", PAYMENT_STATUSES, index=0)
        creator = st.text_input("Oluşturan", value=st.session_state.get("username", "admin"))
    sevkiyat_notu = st.text_area("Sevkiyat notu", height=80)
    genel_not = st.text_area("Genel not", height=80)

    st.markdown("## Ürün Kalemi Ekle")
    product_options = []
    product_map = {}
    for _, r in products.iterrows():
        label = f"{r['Urun_ID']} | {r['Urun_Adi']} - {r['Renk']} / {r['Model']}"
        product_options.append(label)
        product_map[label] = r.to_dict()
    pc1, pc2, pc3, pc4 = st.columns([2.8, 1, 1.1, 1.2])
    with pc1:
        product_label = st.selectbox("Ürün", product_options)
        selected_product = product_map[product_label]
    with pc2:
        qty = st.number_input("Adet", min_value=1, step=1, value=1)
    with pc3:
        unit_price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=clean_money(selected_product.get("Birim_Fiyat", 0)))
    with pc4:
        st.metric("Satır toplamı", fmt_tl(qty * unit_price))
    item_note = st.text_input("Kalem notu")
    if st.button("+ Kalemi sepete ekle", use_container_width=True):
        st.session_state["cart"].append({
            "Urun_ID": selected_product.get("Urun_ID", ""), "Urun_Adi": selected_product.get("Urun_Adi", ""),
            "Model": selected_product.get("Model", ""), "Renk": selected_product.get("Renk", ""),
            "Adet": int(qty), "Birim_Fiyat": float(unit_price), "Satir_Toplam": float(qty * unit_price), "Not": item_note,
        })
        st.rerun()

    st.markdown("## Sipariş Sepeti")
    cart = st.session_state.get("cart", [])
    if cart:
        cart_df = pd.DataFrame(cart)
        show = cart_df.copy()
        show["Birim_Fiyat"] = show["Birim_Fiyat"].apply(fmt_tl)
        show["Satir_Toplam"] = show["Satir_Toplam"].apply(fmt_tl)
        st.dataframe(safe_df(show), use_container_width=True, hide_index=True)
        total = sum(clean_money(x.get("Satir_Toplam", 0)) for x in cart)
        st.markdown(f"### Toplam: <span class='gold'>{fmt_tl(total)}</span>", unsafe_allow_html=True)
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Sepeti temizle", use_container_width=True):
                st.session_state["cart"] = []
                st.rerun()
        with b2:
            if st.button("Siparişi kaydet", use_container_width=True):
                orders = data["Siparisler"].copy()
                items = data["Siparis_Kalemleri"].copy()
                sid = make_uuid("SIP")
                sno = next_order_no(orders)
                order_row = {
                    "Siparis_ID": sid, "Siparis_No": sno, "Firma_ID": selected_firm.get("Firma_ID", ""),
                    "Firma_Adi": selected_firm.get("Firma_Adi", ""), "Sube": selected_firm.get("Sube", ""),
                    "Siparis_Tarihi": today_str(), "Teslim_Tarihi": str(teslim), "Durum": status,
                    "Odeme_Durumu": payment_status, "Toplam_Tutar": total, "Tahsil_Edilen": 0,
                    "Kalan_Tutar": total, "Sevkiyat_Notu": sevkiyat_notu, "Genel_Not": genel_not,
                    "Olusturan": creator, "Kayit_Tarihi": now_str(), "Guncelleme_Tarihi": now_str(),
                }
                orders = pd.concat([orders, pd.DataFrame([order_row])], ignore_index=True)
                new_items = []
                for x in cart:
                    new_items.append({
                        "Kalem_ID": make_uuid("KLM"), "Siparis_ID": sid, "Siparis_No": sno,
                        "Urun_ID": x.get("Urun_ID", ""), "Urun_Adi": x.get("Urun_Adi", ""),
                        "Model": x.get("Model", ""), "Renk": x.get("Renk", ""), "Adet": x.get("Adet", 0),
                        "Birim_Fiyat": x.get("Birim_Fiyat", 0), "Satir_Toplam": x.get("Satir_Toplam", 0), "Not": x.get("Not", ""),
                    })
                items = pd.concat([items, pd.DataFrame(new_items)], ignore_index=True)
                save_sheet("Siparisler", orders)
                save_sheet("Siparis_Kalemleri", items)
                st.session_state["cart"] = []
                st.success(f"Sipariş kaydedildi: {sno}")
                st.rerun()
    else:
        st.info("Sepette ürün yok.")


def orders_page(data):
    st.markdown('<div class="main-title">Siparişler</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Siparişleri filtreleyin, güncelleyin veya hatalı kaydı silin</p>', unsafe_allow_html=True)
    orders = orders_for_display(data["Siparisler"], data["Odemeler"])
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    if orders.empty:
        st.info("Henüz sipariş yok.")
        return

    f1, f2, f3 = st.columns(3)
    with f1:
        search = st.text_input("Firma ara")
    with f2:
        status_filter = st.selectbox("Durum filtresi", ["Tümü"] + ORDER_STATUSES)
    with f3:
        pay_filter = st.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_STATUSES)
    filtered = orders.copy()
    if search:
        filtered = filtered[filtered["Firma_Adi"].astype(str).str.contains(search, case=False, na=False)]
    if status_filter != "Tümü":
        filtered = filtered[filtered["Durum"] == status_filter]
    if pay_filter != "Tümü":
        filtered = filtered[filtered["Odeme_Durumu"] == pay_filter]
    show = filtered[["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar"]].copy()
    for c in ["Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar"]:
        show[c] = show[c].apply(fmt_tl)
    st.dataframe(safe_df(show), use_container_width=True, hide_index=True)

    st.markdown("## Sipariş Detayı / Güncelleme")
    options = [f"{r['Siparis_No']} | {r['Firma_Adi']}" for _, r in orders.iterrows()]
    opt_map = {f"{r['Siparis_No']} | {r['Firma_Adi']}": r.to_dict() for _, r in orders.iterrows()}
    selected = st.selectbox("Sipariş seç", options)
    row = opt_map[selected]
    sid = row.get("Siparis_ID", "")
    st.write(f"**Seçili sipariş:** {row.get('Siparis_No')} - {row.get('Firma_Adi')} / {fmt_tl(row.get('Toplam_Tutar',0))}")
    det_items = items[items["Siparis_ID"].astype(str) == str(sid)] if not items.empty else pd.DataFrame(columns=SCHEMAS["Siparis_Kalemleri"])
    det_show = det_items[["Urun_Adi", "Model", "Renk", "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"]].copy() if not det_items.empty else det_items
    if not det_show.empty:
        det_show["Birim_Fiyat"] = det_show["Birim_Fiyat"].apply(fmt_tl)
        det_show["Satir_Toplam"] = det_show["Satir_Toplam"].apply(fmt_tl)
    st.dataframe(safe_df(det_show), use_container_width=True, hide_index=True)

    with st.form("update_order_form"):
        u1, u2, u3 = st.columns(3)
        with u1:
            new_status = st.selectbox("Durum", ORDER_STATUSES, index=ORDER_STATUSES.index(row.get("Durum")) if row.get("Durum") in ORDER_STATUSES else 0)
        with u2:
            new_pay = st.selectbox("Ödeme durumu", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(row.get("Odeme_Durumu")) if row.get("Odeme_Durumu") in PAYMENT_STATUSES else 0)
        with u3:
            new_delivery = st.text_input("Teslim tarihi", value=str(row.get("Teslim_Tarihi", "")))
        new_ship_note = st.text_area("Sevkiyat notu", value=str(row.get("Sevkiyat_Notu", "")), height=80)
        new_general_note = st.text_area("Genel not", value=str(row.get("Genel_Not", "")), height=80)
        submitted = st.form_submit_button("Siparişi güncelle", use_container_width=True)
    if submitted:
        idx = data["Siparisler"].index[data["Siparisler"]["Siparis_ID"].astype(str) == str(sid)].tolist()
        orders_raw = data["Siparisler"].copy()
        if idx:
            i = idx[0]
            orders_raw.at[i, "Durum"] = new_status
            orders_raw.at[i, "Odeme_Durumu"] = new_pay
            orders_raw.at[i, "Teslim_Tarihi"] = new_delivery
            orders_raw.at[i, "Sevkiyat_Notu"] = new_ship_note
            orders_raw.at[i, "Genel_Not"] = new_general_note
            orders_raw.at[i, "Guncelleme_Tarihi"] = now_str()
            save_sheet("Siparisler", orders_raw)
            st.success("Sipariş güncellendi.")
            st.rerun()

    st.markdown("### Hatalı siparişi sil")
    confirm = st.checkbox("Bu siparişi ve bağlı kalem/ödeme kayıtlarını silmek istediğimi onaylıyorum")
    if st.button("Seçili siparişi kalıcı sil", type="primary", disabled=not confirm):
        orders_new = data["Siparisler"][data["Siparisler"]["Siparis_ID"].astype(str) != str(sid)].copy()
        items_new = items[items["Siparis_ID"].astype(str) != str(sid)].copy() if not items.empty else items
        payments_new = payments[payments["Siparis_ID"].astype(str) != str(sid)].copy() if not payments.empty else payments
        save_sheet("Siparisler", orders_new)
        save_sheet("Siparis_Kalemleri", items_new)
        save_sheet("Odemeler", payments_new)
        st.success("Sipariş silindi.")
        st.rerun()


def firms_page(data):
    st.markdown('<div class="main-title">Firmalar</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Bayi, müşteri ve şube kartlarını yönetin</p>', unsafe_allow_html=True)
    firms = data["Firmalar"].copy()
    orders = data["Siparisler"].copy()
    with st.expander("+ Yeni firma / şube ekle", expanded=True):
        with st.form("add_firm_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Firma adı *")
                branch = st.text_input("Şube")
                contact = st.text_input("Yetkili kişi")
            with c2:
                phone = st.text_input("Telefon")
                tax_no = st.text_input("Vergi No / VKN")
                tax_office = st.text_input("Vergi Dairesi")
            with c3:
                address = st.text_area("Adres", height=80)
                note = st.text_area("Not", height=80)
            if st.form_submit_button("Firmayı kaydet", use_container_width=True):
                if not name.strip():
                    st.error("Firma adı zorunlu.")
                else:
                    row = {"Firma_ID": next_simple_id(firms, "Firma_ID", "F"), "Firma_Adi": name.strip(), "Sube": branch.strip(), "Yetkili_Kisi": contact.strip(), "Telefon": phone.strip(), "Adres": address.strip(), "Vergi_No_VKN": tax_no.strip(), "Vergi_Dairesi": tax_office.strip(), "Not": note.strip(), "Aktif": "Aktif", "Kayit_Tarihi": now_str()}
                    firms2 = pd.concat([firms, pd.DataFrame([row])], ignore_index=True)
                    save_sheet("Firmalar", firms2)
                    st.success("Firma kaydedildi.")
                    st.rerun()
    st.markdown("## Kayıtlı Firmalar")
    disp_cols = ["Firma_ID", "Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Vergi_No_VKN", "Aktif", "Kayit_Tarihi"]
    st.dataframe(safe_df(firms, disp_cols), use_container_width=True, hide_index=True)

    st.markdown("## Firma Düzelt / Sil")
    firms_nonblank = firms[firms["Firma_Adi"].astype(str).str.strip() != ""]
    if firms_nonblank.empty:
        st.info("Düzenlenecek firma yok.")
        return
    options = [f"{r['Firma_ID']} | {r['Firma_Adi']}" + (f" - {r['Sube']}" if str(r.get('Sube','')).strip() else "") for _, r in firms_nonblank.iterrows()]
    opt_map = {f"{r['Firma_ID']} | {r['Firma_Adi']}" + (f" - {r['Sube']}" if str(r.get('Sube','')).strip() else ""): r.to_dict() for _, r in firms_nonblank.iterrows()}
    selected = st.selectbox("Firma seç", options)
    row = opt_map[selected]
    fid = row.get("Firma_ID", "")
    with st.form("edit_firm_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_name = st.text_input("Firma adı", value=row.get("Firma_Adi", ""))
            e_branch = st.text_input("Şube", value=row.get("Sube", ""))
            e_contact = st.text_input("Yetkili kişi", value=row.get("Yetkili_Kisi", ""))
        with c2:
            e_phone = st.text_input("Telefon", value=row.get("Telefon", ""))
            e_tax = st.text_input("Vergi No / VKN", value=row.get("Vergi_No_VKN", ""))
            e_office = st.text_input("Vergi Dairesi", value=row.get("Vergi_Dairesi", ""))
        with c3:
            e_active = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if row.get("Aktif", "Aktif") != "Pasif" else 1)
            e_address = st.text_area("Adres", value=row.get("Adres", ""), height=80)
            e_note = st.text_area("Not", value=row.get("Not", ""), height=80)
        if st.form_submit_button("Firmayı güncelle", use_container_width=True):
            idx = firms.index[firms["Firma_ID"].astype(str) == str(fid)].tolist()
            if idx:
                i = idx[0]
                updates = {"Firma_Adi": e_name, "Sube": e_branch, "Yetkili_Kisi": e_contact, "Telefon": e_phone, "Adres": e_address, "Vergi_No_VKN": e_tax, "Vergi_Dairesi": e_office, "Not": e_note, "Aktif": e_active}
                for k, v in updates.items():
                    firms.at[i, k] = v
                save_sheet("Firmalar", firms)
                st.success("Firma güncellendi.")
                st.rerun()
    used = not orders[orders["Firma_ID"].astype(str) == str(fid)].empty if not orders.empty else False
    if used:
        st.warning("Bu firma siparişlerde kullanılmış. Geçmiş rapor bozulmasın diye kalıcı silme yerine pasife alabilirsin.")
        if st.button("Firmayı pasife al"):
            firms.loc[firms["Firma_ID"].astype(str) == str(fid), "Aktif"] = "Pasif"
            save_sheet("Firmalar", firms)
            st.rerun()
    else:
        if st.button("Firmayı kalıcı sil"):
            firms = firms[firms["Firma_ID"].astype(str) != str(fid)]
            save_sheet("Firmalar", firms)
            st.success("Firma silindi.")
            st.rerun()


def products_page(data):
    st.markdown('<div class="main-title">Ürünler</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Ürün kartları, renkler, fiyatlar ve stok bilgisi</p>', unsafe_allow_html=True)
    products = data["Urunler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    with st.expander("+ Yeni ürün ekle", expanded=True):
        with st.form("add_product_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                pname = st.text_input("Ürün adı *")
                model = st.text_input("Model")
                category = st.text_input("Kategori")
            with c2:
                color = st.text_input("Renk")
                price = st.number_input("Birim fiyat", min_value=0.0, step=50.0)
            with c3:
                stock = st.number_input("Stok", min_value=0, step=1, value=0)
                note = st.text_area("Not", height=80)
            if st.form_submit_button("Ürünü kaydet", use_container_width=True):
                if not pname.strip():
                    st.error("Ürün adı zorunlu.")
                else:
                    row = {"Urun_ID": next_simple_id(products, "Urun_ID", "U"), "Kategori": category.strip(), "Urun_Adi": pname.strip(), "Model": model.strip(), "Renk": color.strip(), "Birim_Fiyat": price, "Stok": stock, "Durum": "Aktif", "Not": note.strip(), "Kayit_Tarihi": now_str()}
                    products2 = pd.concat([products, pd.DataFrame([row])], ignore_index=True)
                    save_sheet("Urunler", products2)
                    st.success("Ürün kaydedildi.")
                    st.rerun()
    st.markdown("## Kayıtlı Ürünler")
    show = products.copy()
    if not show.empty:
        show["Birim_Fiyat"] = show["Birim_Fiyat"].apply(fmt_tl)
    st.dataframe(safe_df(show, ["Urun_ID", "Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Durum", "Not"]), use_container_width=True, hide_index=True)

    st.markdown("## Ürün Düzelt / Sil")
    products_nonblank = products[products["Urun_Adi"].astype(str).str.strip() != ""]
    if products_nonblank.empty:
        st.info("Düzenlenecek ürün yok.")
        return
    options = [f"{r['Urun_ID']} | {r['Urun_Adi']} - {r.get('Renk','')}" for _, r in products_nonblank.iterrows()]
    opt_map = {f"{r['Urun_ID']} | {r['Urun_Adi']} - {r.get('Renk','')}": r.to_dict() for _, r in products_nonblank.iterrows()}
    selected = st.selectbox("Ürün seç", options)
    row = opt_map[selected]
    uid = row.get("Urun_ID", "")
    with st.form("edit_product_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_name = st.text_input("Ürün adı", value=row.get("Urun_Adi", ""))
            e_model = st.text_input("Model", value=row.get("Model", ""))
            e_category = st.text_input("Kategori", value=row.get("Kategori", ""))
        with c2:
            e_color = st.text_input("Renk", value=row.get("Renk", ""))
            e_price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=clean_money(row.get("Birim_Fiyat", 0)))
        with c3:
            e_stock = st.number_input("Stok", min_value=0, step=1, value=clean_int(row.get("Stok", 0)))
            e_status = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if row.get("Durum", "Aktif") != "Pasif" else 1)
            e_note = st.text_area("Not", value=row.get("Not", ""), height=80)
        if st.form_submit_button("Ürünü güncelle", use_container_width=True):
            idx = products.index[products["Urun_ID"].astype(str) == str(uid)].tolist()
            if idx:
                i = idx[0]
                updates = {"Urun_Adi": e_name, "Model": e_model, "Kategori": e_category, "Renk": e_color, "Birim_Fiyat": e_price, "Stok": e_stock, "Durum": e_status, "Not": e_note}
                for k, v in updates.items():
                    products.at[i, k] = v
                save_sheet("Urunler", products)
                st.success("Ürün güncellendi.")
                st.rerun()
    used = not items[items["Urun_ID"].astype(str) == str(uid)].empty if not items.empty else False
    if used:
        st.warning("Bu ürün siparişlerde kullanılmış. Geçmiş rapor bozulmasın diye kalıcı silme yerine pasife alabilirsin.")
        if st.button("Ürünü pasife al"):
            products.loc[products["Urun_ID"].astype(str) == str(uid), "Durum"] = "Pasif"
            save_sheet("Urunler", products)
            st.rerun()
    else:
        if st.button("Ürünü kalıcı sil"):
            products = products[products["Urun_ID"].astype(str) != str(uid)]
            save_sheet("Urunler", products)
            st.success("Ürün silindi.")
            st.rerun()


def payments_page(data):
    st.markdown('<div class="main-title">Ödemeler</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Tahsilat kayıtları ve sipariş bakiye takibi</p>', unsafe_allow_html=True)
    orders = orders_for_display(data["Siparisler"], data["Odemeler"])
    payments = data["Odemeler"].copy()
    if orders.empty:
        st.info("Ödeme eklemek için önce sipariş oluşturmalısın.")
        return
    st.markdown("## Yeni Ödeme Ekle")
    options = [f"{r['Siparis_No']} | {r['Firma_Adi']} | Kalan: {fmt_tl(r.get('Kalan_Tutar',0))}" for _, r in orders.iterrows()]
    opt_map = {f"{r['Siparis_No']} | {r['Firma_Adi']} | Kalan: {fmt_tl(r.get('Kalan_Tutar',0))}": r.to_dict() for _, r in orders.iterrows()}
    with st.form("add_payment_form"):
        selected = st.selectbox("Sipariş", options)
        row = opt_map[selected]
        c1, c2, c3 = st.columns(3)
        with c1:
            pdate = st.date_input("Ödeme tarihi", value=date.today())
        with c2:
            amount = st.number_input("Tutar", min_value=0.0, step=100.0, value=clean_money(row.get("Kalan_Tutar", 0)))
        with c3:
            ptype = st.selectbox("Ödeme tipi", PAYMENT_TYPES)
        note = st.text_area("Not", height=80)
        if st.form_submit_button("Ödemeyi kaydet", use_container_width=True):
            if amount <= 0:
                st.error("Tutar 0'dan büyük olmalı.")
            else:
                new_pay = {"Odeme_ID": make_uuid("ODM"), "Siparis_ID": row.get("Siparis_ID", ""), "Siparis_No": row.get("Siparis_No", ""), "Firma_Adi": row.get("Firma_Adi", ""), "Odeme_Tarihi": str(pdate), "Tutar": amount, "Odeme_Tipi": ptype, "Not": note, "Kayit_Tarihi": now_str()}
                payments2 = pd.concat([payments, pd.DataFrame([new_pay])], ignore_index=True)
                orders2 = recalc_orders(data["Siparisler"], payments2)
                save_sheet("Odemeler", payments2)
                save_sheet("Siparisler", orders2)
                st.success("Ödeme kaydedildi.")
                st.rerun()
    st.markdown("## Kayıtlı Ödemeler")
    show = payments.copy()
    if not show.empty:
        show["Tutar"] = show["Tutar"].apply(fmt_tl)
    st.dataframe(safe_df(show, ["Odeme_ID", "Siparis_No", "Firma_Adi", "Odeme_Tarihi", "Tutar", "Odeme_Tipi", "Not"]), use_container_width=True, hide_index=True)

    st.markdown("## Hatalı Ödeme Sil")
    pays = payments[payments["Odeme_ID"].astype(str).str.strip() != ""]
    if not pays.empty:
        opts = [f"{r['Odeme_ID']} | {r['Siparis_No']} | {fmt_tl(r['Tutar'])}" for _, r in pays.iterrows()]
        omap = {f"{r['Odeme_ID']} | {r['Siparis_No']} | {fmt_tl(r['Tutar'])}": r.to_dict() for _, r in pays.iterrows()}
        sel = st.selectbox("Ödeme seç", opts)
        oid = omap[sel].get("Odeme_ID", "")
        if st.button("Seçili ödemeyi sil"):
            payments2 = payments[payments["Odeme_ID"].astype(str) != str(oid)]
            orders2 = recalc_orders(data["Siparisler"], payments2)
            save_sheet("Odemeler", payments2)
            save_sheet("Siparisler", orders2)
            st.success("Ödeme silindi.")
            st.rerun()
    else:
        st.info("Silinecek ödeme yok.")


def reports_page(data):
    st.markdown('<div class="main-title">Raporlar</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Firma, ürün, ciro ve tahsilat raporları</p>', unsafe_allow_html=True)
    orders = orders_for_display(data["Siparisler"], data["Odemeler"])
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    if orders.empty:
        st.info("Rapor için sipariş verisi yok.")
    orders_num = numeric_cols(orders, ["Toplam_Tutar", "Tahsil_Edilen", "Kalan_Tutar"])
    items_num = numeric_cols(items, ["Adet", "Birim_Fiyat", "Satir_Toplam"])

    st.markdown("## Firma Bazlı Satış")
    if not orders_num.empty:
        firm_report = orders_num.groupby("Firma_Adi", dropna=False).agg(Siparis_Adedi=("Siparis_No", "count"), Toplam_Ciro=("Toplam_Tutar", "sum"), Tahsil_Edilen=("Tahsil_Edilen", "sum"), Kalan_Tutar=("Kalan_Tutar", "sum")).reset_index()
        st.dataframe(safe_df(firm_report), use_container_width=True, hide_index=True)
        if not firm_report.empty:
            st.bar_chart(firm_report.set_index("Firma_Adi")[["Toplam_Ciro"]])
    else:
        firm_report = pd.DataFrame(columns=["Firma_Adi", "Siparis_Adedi", "Toplam_Ciro", "Tahsil_Edilen", "Kalan_Tutar"])
        st.info("Firma raporu için veri yok.")

    st.markdown("## Ürün Bazlı Satış")
    if not items_num.empty:
        product_report = items_num.groupby("Urun_Adi", dropna=False).agg(Toplam_Adet=("Adet", "sum"), Toplam_Tutar=("Satir_Toplam", "sum")).reset_index()
        st.dataframe(safe_df(product_report), use_container_width=True, hide_index=True)
        if not product_report.empty:
            st.bar_chart(product_report.set_index("Urun_Adi")[["Toplam_Adet"]])
    else:
        product_report = pd.DataFrame(columns=["Urun_Adi", "Toplam_Adet", "Toplam_Tutar"])
        st.info("Ürün raporu için veri yok.")

    st.markdown("## Excel Dışa Aktar")
    try:
        excel = to_excel_bytes({
            "Siparisler": orders,
            "Kalemler": items,
            "Odemeler": payments,
            "Firma_Raporu": firm_report,
            "Urun_Raporu": product_report,
        })
        st.download_button("Raporu indir (Excel)", excel, file_name=f"gundays_rapor_{today_str()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception as e:
        st.error("Excel oluşturulurken hata oluştu.")
        st.exception(e)


def settings_page(data):
    st.markdown('<div class="main-title">Yedek / Ayarlar</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Bağlantı kontrolü, tablo onarımı, Excel yedeği ve şifre değişimi</p>', unsafe_allow_html=True)
    st.markdown("## Google Sheets Bağlantısı")
    st.markdown('<div class="success-box">Google Sheets bağlantısı aktif.</div>', unsafe_allow_html=True)
    st.code(f"SPREADSHEET_ID = {st.secrets.get('SPREADSHEET_ID', '')}")

    st.markdown("## Google Sheet Tablo Onarımı")
    st.caption("Firmalar/Ürünler/Siparişler gibi sayfalarda başlık kayması, boş satır, duplicate kolon veya eski şablon hatası varsa burası düzeltir.")
    if st.button("Tabloları onar ve boş satırları temizle", use_container_width=True):
        ensure_and_repair_schema(force=True)
        st.success("Google Sheet tabloları onarıldı. Sayfa yenileniyor.")
        st.rerun()

    st.markdown("## Excel Yedeği İndir")
    try:
        excel = to_excel_bytes({name: df for name, df in data.items()})
        st.download_button("Tüm verileri indir (Excel)", excel, file_name=f"gundays_yedek_{today_str()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception as e:
        st.error("Yedek oluşturulamadı.")
        st.exception(e)

    st.markdown("## Şifre Değiştir")
    with st.form("password_change"):
        old = st.text_input("Mevcut şifre", type="password")
        new = st.text_input("Yeni şifre", type="password")
        new2 = st.text_input("Yeni şifre tekrar", type="password")
        if st.form_submit_button("Şifreyi değiştir", use_container_width=True):
            users = data["Kullanicilar"].copy()
            username = st.session_state.get("username", "admin")
            idx = users.index[users["Kullanici_Adi"].astype(str) == str(username)].tolist()
            if not idx:
                st.error("Kullanıcı kaydı bulunamadı.")
            elif not check_password(old, users.at[idx[0], "Sifre"]):
                st.error("Mevcut şifre hatalı.")
            elif not new or new != new2:
                st.error("Yeni şifreler aynı değil.")
            else:
                users.at[idx[0], "Sifre"] = hash_password(new)
                save_sheet("Kullanicilar", users)
                st.success("Şifre değiştirildi.")

# ============================================================
# MAIN
# ============================================================
def main():
    if not st.session_state.get("logged_in"):
        login_screen()
        return

    page = sidebar_menu()
    try:
        data = get_data()
    except Exception as e:
        st.error("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
        st.exception(e)
        return

    if page == "Dashboard":
        dashboard_page(data)
    elif page == "Yeni Sipariş":
        new_order_page(data)
    elif page == "Siparişler":
        orders_page(data)
    elif page == "Firmalar":
        firms_page(data)
    elif page == "Ürünler":
        products_page(data)
    elif page == "Ödemeler":
        payments_page(data)
    elif page == "Raporlar":
        reports_page(data)
    elif page == "Yedek / Ayarlar":
        settings_page(data)

if __name__ == "__main__":
    main()
