# Günday's Home Sipariş Takip - V7 Stable
# Google Sheets tabanlı, başlık kaymalarına dayanıklı sürüm.

from __future__ import annotations

import io
import json
import math
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

APP_TITLE = "Günday's Home Sipariş Takip"
DEFAULT_SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CACHE_TTL_SECONDS = 120

SHEETS: Dict[str, Dict[str, Any]] = {
    "Firmalar": {
        "primary": "Firma_ID",
        "headers": [
            "Firma_ID", "Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres",
            "Vergi_No", "Vergi_Dairesi", "Not", "Aktif", "Kayit_Tarihi",
        ],
        "aliases": {
            "Firma_ID": ["firma_id", "firma id", "id", "bayi_id", "musteri_id", "müşteri id"],
            "Firma_Adi": ["firma_adi", "firma adı", "firma adi", "firma", "firma_adı", "bayi", "musteri", "müşteri", "cari", "firma adı *"],
            "Sube": ["sube", "şube", "magaza", "mağaza"],
            "Yetkili_Kisi": ["yetkili_kisi", "yetkili kişi", "yetkili", "ilgili"],
            "Telefon": ["telefon", "tel", "gsm", "numara"],
            "Adres": ["adres"],
            "Vergi_No": ["vergi_no", "vergi no", "vkn", "tckn", "vergi numarası", "vergi numarasi"],
            "Vergi_Dairesi": ["vergi_dairesi", "vergi dairesi"],
            "Not": ["not", "açıklama", "aciklama", "genel not"],
            "Aktif": ["aktif", "durum", "status"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi", "kayıt", "tarih"],
        },
    },
    "Urunler": {
        "primary": "Urun_ID",
        "headers": [
            "Urun_ID", "Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat",
            "Stok", "Not", "Aktif", "Kayit_Tarihi",
        ],
        "aliases": {
            "Urun_ID": ["urun_id", "ürün id", "urun id", "id"],
            "Kategori": ["kategori", "urun_grubu", "ürün grubu", "grup", "ürün kartları", "urun kartlari"],
            "Urun_Adi": ["urun_adi", "ürün adı", "urun adi", "ürün", "urun", "ad", "adı", "adi", "ürün adı *"],
            "Model": ["model"],
            "Renk": ["renk", "color"],
            "Birim_Fiyat": ["birim_fiyat", "birim fiyat", "fiyat", "satış fiyatı", "satis fiyati", "liste fiyatı"],
            "Stok": ["stok", "stock"],
            "Not": ["not", "açıklama", "aciklama", "genel not"],
            "Aktif": ["aktif", "durum", "status"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi", "kayıt", "tarih"],
        },
    },
    "Siparisler": {
        "primary": "Siparis_No",
        "headers": [
            "Siparis_No", "Firma_ID", "Firma_Adi", "Sube", "Siparis_Tarihi",
            "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Odenen_Tutar",
            "Sevkiyat_Notu", "Genel_Not", "Olusturan",
        ],
        "aliases": {
            "Siparis_No": ["siparis_no", "sipariş no", "siparis no", "sipariş_no", "order no", "order_no", "no"],
            "Firma_ID": ["firma_id", "firma id", "bayi_id"],
            "Firma_Adi": ["firma_adi", "firma adı", "firma adi", "firma", "musteri", "müşteri", "cari"],
            "Sube": ["sube", "şube", "magaza", "mağaza"],
            "Siparis_Tarihi": ["siparis_tarihi", "sipariş tarihi", "siparis tarihi", "tarih"],
            "Teslim_Tarihi": ["teslim_tarihi", "teslim tarihi", "termin", "tahmini teslim tarihi"],
            "Durum": ["durum", "siparis durumu", "sipariş durumu"],
            "Odeme_Durumu": ["odeme_durumu", "ödeme durumu", "odeme durumu", "ödeme", "odeme"],
            "Toplam_Tutar": ["toplam_tutar", "toplam tutar", "toplam", "ciro", "tutar", "sipariş toplamı"],
            "Odenen_Tutar": ["odenen_tutar", "ödenen tutar", "ödenen", "tahsilat", "tahsil edilen"],
            "Sevkiyat_Notu": ["sevkiyat_notu", "sevkiyat notu", "teslimat notu"],
            "Genel_Not": ["genel_not", "genel not", "not", "açıklama", "aciklama"],
            "Olusturan": ["olusturan", "oluşturan", "kullanıcı", "kullanici"],
        },
    },
    "Siparis_Kalemleri": {
        "primary": "Kalem_ID",
        "headers": [
            "Kalem_ID", "Siparis_No", "Urun_ID", "Urun_Adi", "Model", "Renk",
            "Adet", "Birim_Fiyat", "Satir_Toplam", "Not",
        ],
        "aliases": {
            "Kalem_ID": ["kalem_id", "kalem id", "id"],
            "Siparis_No": ["siparis_no", "sipariş no", "siparis no"],
            "Urun_ID": ["urun_id", "ürün id", "urun id"],
            "Urun_Adi": ["urun_adi", "ürün adı", "urun adi", "urun", "ürün"],
            "Model": ["model"],
            "Renk": ["renk"],
            "Adet": ["adet", "miktar", "qty"],
            "Birim_Fiyat": ["birim_fiyat", "birim fiyat", "fiyat"],
            "Satir_Toplam": ["satir_toplam", "satır toplam", "satir toplam", "toplam", "tutar"],
            "Not": ["not", "açıklama", "aciklama"],
        },
    },
    "Odemeler": {
        "primary": "Odeme_ID",
        "headers": ["Odeme_ID", "Siparis_No", "Tarih", "Tutar", "Odeme_Turu", "Not", "Kayit_Tarihi"],
        "aliases": {
            "Odeme_ID": ["odeme_id", "ödeme id", "id"],
            "Siparis_No": ["siparis_no", "sipariş no", "siparis no"],
            "Tarih": ["tarih", "odeme tarihi", "ödeme tarihi"],
            "Tutar": ["tutar", "ödeme", "odeme", "tahsilat"],
            "Odeme_Turu": ["odeme_turu", "ödeme türü", "ödeme tipi", "odeme tipi", "tip"],
            "Not": ["not", "açıklama", "aciklama"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi"],
        },
    },
}

ORDER_STATUSES = ["Sipariş Alındı", "Üretimde", "Hazır", "Sevkiyat Bekliyor", "Gönderildi", "Teslim Edildi", "İptal"]
PAYMENT_STATUSES = ["Bekliyor", "Vadeli", "Kısmi Ödendi", "Ödendi", "İade", "İptal"]
PAYMENT_TYPES = ["Nakit", "Havale/EFT", "Kredi Kartı", "Çek/Senet", "Diğer"]
NUMERIC_COLUMNS = {
    "Birim_Fiyat", "Stok", "Toplam_Tutar", "Odenen_Tutar", "Adet", "Satir_Toplam", "Tutar"
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = text.replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money_to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        try:
            x = float(value)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0
    text = safe_str(value)
    if not text:
        return 0.0
    text = text.replace("TL", "").replace("₺", "").strip()
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if text in {"", "-", ",", "."}:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return float(text)
    except Exception:
        return 0.0


def fmt_money(value: Any) -> str:
    val = money_to_float(value)
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def normalize_status(value: Any, default: str = "Aktif") -> str:
    text = safe_str(value)
    if not text:
        return default
    key = normalize_key(text)
    if key in {"pasif", "kapali", "silindi", "false", "hayir", "0"}:
        return "Pasif"
    if key in {"aktif", "acik", "true", "evet", "1"}:
        return "Aktif"
    return text


def alias_map_for(sheet_name: str) -> Dict[str, str]:
    cfg = SHEETS[sheet_name]
    mapping: Dict[str, str] = {}
    for h in cfg["headers"]:
        mapping[normalize_key(h)] = h
    for canon, aliases in cfg.get("aliases", {}).items():
        for a in aliases:
            mapping[normalize_key(a)] = canon
    return mapping


def empty_df(sheet_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SHEETS[sheet_name]["headers"])


def row_score_for_header(sheet_name: str, row: List[Any]) -> int:
    mapping = alias_map_for(sheet_name)
    cfg = SHEETS[sheet_name]
    seen = []
    for cell in row:
        canon = mapping.get(normalize_key(cell))
        if canon and canon not in seen:
            seen.append(canon)
    score = len(seen) * 10
    first = mapping.get(normalize_key(row[0] if row else ""))
    if first == cfg["primary"]:
        score += 25
    # Prefer rows that contain many exact canonical-like labels in the first columns.
    ordered = cfg["headers"]
    for idx, cell in enumerate(row[: len(ordered)]):
        if mapping.get(normalize_key(cell)) == ordered[idx]:
            score += 2
    return score


def find_header_row(sheet_name: str, values: List[List[Any]]) -> Optional[int]:
    if not values:
        return None
    best_i = None
    best_score = -1
    for i, row in enumerate(values[:25]):
        score = row_score_for_header(sheet_name, row)
        if score > best_score:
            best_i = i
            best_score = score
    # At least 2 matched columns required.
    if best_score < 20:
        return None
    return best_i


def row_is_header_noise(sheet_name: str, rec: Dict[str, Any]) -> bool:
    headers = SHEETS[sheet_name]["headers"]
    vals = [normalize_key(rec.get(h, "")) for h in headers]
    mapped = set(alias_map_for(sheet_name).keys())
    hits = sum(1 for v in vals if v in mapped)
    primary = normalize_key(rec.get(SHEETS[sheet_name]["primary"], ""))
    return hits >= 3 or primary == normalize_key(SHEETS[sheet_name]["primary"])


def parse_sheet_values(sheet_name: str, values: List[List[Any]]) -> pd.DataFrame:
    cfg = SHEETS[sheet_name]
    headers = cfg["headers"]
    mapping = alias_map_for(sheet_name)
    header_i = find_header_row(sheet_name, values)
    if header_i is None:
        return empty_df(sheet_name)

    raw_header = values[header_i]
    col_to_canon: Dict[int, str] = {}
    already: set[str] = set()
    for idx, cell in enumerate(raw_header):
        canon = mapping.get(normalize_key(cell))
        if canon and canon not in already:
            col_to_canon[idx] = canon
            already.add(canon)

    rows: List[Dict[str, Any]] = []
    for raw in values[header_i + 1 :]:
        rec = {h: "" for h in headers}
        for idx, canon in col_to_canon.items():
            if idx < len(raw):
                rec[canon] = safe_str(raw[idx])
        if not any(safe_str(v) for v in rec.values()):
            continue
        if row_is_header_noise(sheet_name, rec):
            continue
        # If there are shifted legacy rows that start with primary but mapping was shifted,
        # try to recover them by positional canonical order.
        if not safe_str(rec.get(cfg["primary"])) and raw:
            first_norm = normalize_key(raw[0])
            if first_norm.startswith(normalize_key(cfg["primary"]).split("_")[0]):
                continue
        rows.append(rec)

    df = pd.DataFrame(rows, columns=headers)
    return clean_df(sheet_name, df)


def clean_df(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
    headers = SHEETS[sheet_name]["headers"]
    primary = SHEETS[sheet_name]["primary"]
    df = df.copy() if df is not None else empty_df(sheet_name)
    # Drop duplicate columns if any slipped through.
    df = df.loc[:, ~pd.Index(df.columns).duplicated(keep="first")]
    for h in headers:
        if h not in df.columns:
            df[h] = ""
    df = df[headers].copy()
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].map(safe_str)
    for col in NUMERIC_COLUMNS.intersection(df.columns):
        df[col] = df[col].map(money_to_float)
    if "Aktif" in df.columns:
        df["Aktif"] = df["Aktif"].map(lambda x: normalize_status(x, "Aktif"))
    if "Durum" in df.columns and sheet_name == "Siparisler":
        df["Durum"] = df["Durum"].map(lambda x: safe_str(x) or "Sipariş Alındı")
    if "Odeme_Durumu" in df.columns:
        df["Odeme_Durumu"] = df["Odeme_Durumu"].map(lambda x: safe_str(x) or "Bekliyor")
    # Remove blank primary rows and header-looking rows.
    if primary in df.columns:
        df = df[df[primary].map(lambda x: bool(safe_str(x)) and normalize_key(x) != normalize_key(primary))]
    noise_mask = df.apply(lambda r: row_is_header_noise(sheet_name, r.to_dict()), axis=1) if not df.empty else []
    if len(noise_mask):
        df = df[~noise_mask]
    return df.reset_index(drop=True)


def df_to_values(sheet_name: str, df: pd.DataFrame) -> List[List[Any]]:
    headers = SHEETS[sheet_name]["headers"]
    df = clean_df(sheet_name, df)
    out = [headers]
    for _, row in df.iterrows():
        vals = []
        for h in headers:
            v = row.get(h, "")
            if h in NUMERIC_COLUMNS:
                v = money_to_float(v)
            vals.append(v)
        out.append(vals)
    return out


def next_id(df: pd.DataFrame, prefix: str, col: str) -> str:
    max_no = 0
    if df is not None and not df.empty and col in df.columns:
        for value in df[col].astype(str):
            m = re.search(r"(\d+)$", value)
            if m:
                max_no = max(max_no, int(m.group(1)))
    return f"{prefix}-{max_no + 1:04d}"


def next_order_no(orders: pd.DataFrame) -> str:
    year = datetime.now().year
    max_no = 0
    if orders is not None and not orders.empty and "Siparis_No" in orders.columns:
        for value in orders["Siparis_No"].astype(str):
            m = re.search(r"GH-(?:\d{4})-(\d+)$", value)
            if m:
                max_no = max(max_no, int(m.group(1)))
    return f"GH-{year}-{max_no + 1:04d}"


def api_error_message(e: Exception) -> str:
    text = str(e)
    if "Quota exceeded" in text or "429" in text:
        return "Google Sheets okuma/yazma kotası geçici olarak doldu. 1-2 dakika bekleyip tekrar deneyin."
    if "The caller does not have permission" in text or "403" in text:
        return "Google Sheet yetkisi eksik. Service account maili Sheet'e Düzenleyici olarak eklenmeli."
    if "Unable to parse range" in text:
        return "Google Sheet sekme adı/range okunamadı. Ayarlar > Tabloları onar işlemini deneyin."
    return text

# -----------------------------------------------------------------------------
# Google Sheets API
# -----------------------------------------------------------------------------

def spreadsheet_id() -> str:
    return st.secrets.get("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)


def service_info_json() -> str:
    try:
        info = dict(st.secrets["gcp_service_account"])
    except Exception:
        return ""
    return json.dumps(info, sort_keys=True)


def get_service():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Streamlit Secrets içinde gcp_service_account yok.")
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_all_data_cached(spreadsheet_id_value: str, service_info: str) -> Dict[str, pd.DataFrame]:
    if not service_info:
        raise RuntimeError("Google Service Account secrets bulunamadı.")
    service = get_service()
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id_value, fields="sheets.properties.title").execute()
    existing_titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    ranges = [f"'{name}'!A1:Z5000" for name in SHEETS if name in existing_titles]
    values_by_name = {name: [] for name in SHEETS}
    if ranges:
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id_value,
            ranges=ranges,
            majorDimension="ROWS",
        ).execute()
        for vr in result.get("valueRanges", []):
            rng = vr.get("range", "")
            # Range format: 'Firmalar'!A1:Z5000 or Firmalar!A1:Z5000
            title = rng.split("!")[0].strip("'")
            if title in values_by_name:
                values_by_name[title] = vr.get("values", [])
    return {name: parse_sheet_values(name, values_by_name.get(name, [])) for name in SHEETS}


def load_all_data() -> Dict[str, pd.DataFrame]:
    return load_all_data_cached(spreadsheet_id(), service_info_json())


def clear_data_cache() -> None:
    try:
        load_all_data_cached.clear()
    except Exception:
        pass


def ensure_tabs_exist() -> None:
    service = get_service()
    sid = spreadsheet_id()
    meta = service.spreadsheets().get(spreadsheetId=sid, fields="sheets.properties.title").execute()
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
    requests = []
    for name in SHEETS:
        if name not in existing:
            requests.append({"addSheet": {"properties": {"title": name}}})
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()


def rewrite_sheet(sheet_name: str, df: pd.DataFrame) -> None:
    service = get_service()
    sid = spreadsheet_id()
    ensure_tabs_exist()
    values = df_to_values(sheet_name, df)
    service.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{sheet_name}'!A1:Z5000").execute()
    service.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"'{sheet_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()
    clear_data_cache()


def append_row(sheet_name: str, row: Dict[str, Any], data: Optional[Dict[str, pd.DataFrame]] = None) -> None:
    data = data or load_all_data()
    df = data[sheet_name].copy()
    headers = SHEETS[sheet_name]["headers"]
    new_row = {h: row.get(h, "") for h in headers}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    rewrite_sheet(sheet_name, df)


def repair_all_tables() -> Dict[str, int]:
    ensure_tabs_exist()
    data = load_all_data()
    counts = {}
    for name, df in data.items():
        clean = clean_df(name, df)
        rewrite_sheet(name, clean)
        counts[name] = len(clean)
    clear_data_cache()
    return counts

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

def set_page() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        :root { --gold:#d6a84f; --gold2:#f4d47b; --bg:#05070b; --panel:#0b1425; --text:#f8fafc; --muted:#aeb7c7; }
        .stApp {
            background: radial-gradient(circle at 0% 0%, rgba(214,168,79,.13), transparent 24%),
                        linear-gradient(120deg, #05070b 0%, #071327 62%, #0d1b34 100%);
            color: var(--text);
        }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #081121 0%, #0d1728 100%); border-right: 1px solid rgba(214,168,79,.25); }
        [data-testid="stSidebar"] * { color: #f8fafc !important; }
        h1, h2, h3 { color: #fff !important; letter-spacing: -.03em; }
        .small-muted { color: var(--muted); font-size: .92rem; }
        .premium-card { border: 1px solid rgba(214,168,79,.55); background: linear-gradient(145deg, rgba(13,24,44,.98), rgba(8,13,24,.98)); border-radius: 18px; padding: 24px 22px; box-shadow: 0 12px 34px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.04); min-height: 130px; }
        .premium-card .label { color:#fff; font-weight:800; font-size:.95rem; }
        .premium-card .value { color:#fff; font-weight:900; font-size:2.05rem; margin-top:12px; }
        .premium-card .hint { color:var(--gold2); font-weight:700; font-size:.82rem; margin-top:10px; }
        .stButton > button, .stDownloadButton > button, button[kind="secondary"] { background: linear-gradient(90deg, rgba(214,168,79,.24), rgba(214,168,79,.08)) !important; border:1px solid rgba(214,168,79,.75) !important; color:#fff !important; border-radius:12px !important; font-weight:800 !important; }
        .stButton > button:hover, .stDownloadButton > button:hover { border-color: rgba(244,212,123,.95) !important; box-shadow:0 0 0 2px rgba(214,168,79,.18); }
        div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input { background: rgba(255,255,255,.09) !important; color:white !important; border-color:rgba(255,255,255,.18) !important; }
        label, .stMarkdown p, .stCaption, .stText { color:#f8fafc !important; }
        .stAlert { border-radius:14px; }
        hr { border-color: rgba(214,168,79,.18); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, hint: str = "") -> str:
    return f"""
    <div class="premium-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="hint">{hint}</div>
    </div>
    """


def show_df(df: pd.DataFrame, height: Optional[int] = None) -> None:
    if df is None or df.empty:
        st.info("Gösterilecek kayıt yok.")
        return
    view = df.copy()
    # st.dataframe no longer accepts height=None in newer Streamlit.
    if isinstance(height, int) and height > 0:
        st.dataframe(view, use_container_width=True, hide_index=True, height=height)
    else:
        st.dataframe(view, use_container_width=True, hide_index=True)


def download_excel_button(data: Dict[str, pd.DataFrame], label: str = "Tüm verileri indir (Excel)") -> None:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data.items():
            df.to_excel(writer, index=False, sheet_name=name[:31])
    st.download_button(label, data=output.getvalue(), file_name=f"gundays_yedek_{today_str()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def login_page() -> None:
    st.markdown(f"# {APP_TITLE}")
    st.caption("Sipariş, firma, ürün, sevkiyat ve ödeme durumlarını tek panelden yönetin.")
    c1, c2, c3 = st.columns([1, 1.25, 1])
    with c2:
        st.markdown("## Yönetim Paneli Girişi")
        with st.form("login_form"):
            username = st.text_input("Kullanıcı adı")
            password = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş yap", use_container_width=True)
        expected_user = st.secrets.get("APP_USER", "admin")
        expected_pass = st.secrets.get("APP_PASSWORD", "admin123")
        if submitted:
            if username == expected_user and password == expected_pass:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")
        st.info("İlk kurulum bilgisi: admin / admin123. Yayına almadan önce Streamlit Secrets içinden APP_PASSWORD ekleyerek değiştir.")


def sidebar() -> str:
    st.sidebar.markdown("## Günday's Home")
    st.sidebar.caption(f"Kullanıcı: {st.session_state.get('username', 'admin')} / Admin")
    pages = ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Ödemeler", "Raporlar", "Yedek / Ayarlar"]
    page = st.sidebar.radio("", pages, label_visibility="collapsed")
    st.sidebar.markdown("---")
    if st.sidebar.button("Çıkış yap", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    return page

# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------

def dashboard_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Dashboard")
    st.caption("Günday's Home genel sipariş özeti")

    if not orders.empty:
        active_mask = ~orders["Durum"].astype(str).map(normalize_key).isin({"iptal", "iptal_edildi"})
        active_orders = int(active_mask.sum())
        total_revenue = float(orders.loc[active_mask, "Toplam_Tutar"].map(money_to_float).sum())
    else:
        active_orders = 0
        total_revenue = 0.0
    total_orders = len(orders)
    total_paid = float(payments["Tutar"].map(money_to_float).sum()) if not payments.empty else 0.0
    pending = max(total_revenue - total_paid, 0.0)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Toplam Sipariş", str(total_orders), "Tüm kayıtlar"), unsafe_allow_html=True)
    c2.markdown(metric_card("Aktif Sipariş", str(active_orders), "İptal hariç"), unsafe_allow_html=True)
    c3.markdown(metric_card("Ciro", fmt_money(total_revenue), "Sipariş toplamı"), unsafe_allow_html=True)
    c4.markdown(metric_card("Ödeme Bekleyen", fmt_money(pending), "Tahsilat farkı"), unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns([1.15, 1])
    with col1:
        st.markdown("## Son Siparişler")
        if orders.empty:
            st.info("Henüz sipariş yok.")
        else:
            view = orders[[c for c in ["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar"] if c in orders.columns]].tail(8).iloc[::-1].copy()
            if "Toplam_Tutar" in view.columns:
                view["Toplam_Tutar"] = view["Toplam_Tutar"].map(fmt_money)
            show_df(view, height=280)
    with col2:
        st.markdown("## Durum Dağılımı")
        if orders.empty:
            st.info("Grafik için veri yok.")
        else:
            chart = orders.groupby("Durum", dropna=False).size().reset_index(name="Adet")
            st.bar_chart(chart.set_index("Durum"))

    st.markdown("## Hızlı Uyarılar")
    warnings = []
    if not orders.empty:
        waiting = orders[orders["Durum"].isin(["Sipariş Alındı", "Üretimde", "Hazır", "Sevkiyat Bekliyor"])]
        if len(waiting) > 0:
            warnings.append(f"Açık durumda {len(waiting)} sipariş var.")
        unpaid = orders[orders["Odeme_Durumu"].isin(["Bekliyor", "Vadeli", "Kısmi Ödendi"])]
        if len(unpaid) > 0:
            warnings.append(f"Ödemesi kapanmamış {len(unpaid)} sipariş var.")
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success("Şu an kritik uyarı yok.")


def firm_options(firms: pd.DataFrame) -> List[str]:
    if firms.empty:
        return []
    view = firms[firms["Aktif"].astype(str) != "Pasif"].copy()
    opts = []
    for r in view.itertuples(index=False):
        label = f"{r.Firma_ID} | {r.Firma_Adi}"
        if safe_str(r.Sube):
            label += f" / {r.Sube}"
        opts.append(label)
    return opts


def product_options(products: pd.DataFrame) -> List[str]:
    if products.empty:
        return []
    view = products[products["Aktif"].astype(str) != "Pasif"].copy()
    opts = []
    for r in view.itertuples(index=False):
        label = f"{r.Urun_ID} | {r.Urun_Adi}"
        details = " / ".join([x for x in [safe_str(r.Renk), safe_str(r.Model)] if x])
        if details:
            label += f" - {details}"
        opts.append(label)
    return opts


def new_order_page(data: Dict[str, pd.DataFrame]) -> None:
    firms = data["Firmalar"].copy()
    products = data["Urunler"].copy()
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    st.markdown("# Yeni Sipariş")
    st.caption("Firma seçin, ürünleri ekleyin, siparişi Google Sheets'e kaydedin")

    fopts = firm_options(firms)
    popts = product_options(products)
    if not fopts:
        st.error("Önce Firmalar sekmesinden en az bir aktif firma eklemen gerekiyor.")
        return
    if not popts:
        st.error("Önce Ürünler sekmesinden en az bir aktif ürün eklemen gerekiyor.")
        return

    with st.form("new_order_form"):
        st.markdown("## Sipariş Bilgileri")
        c1, c2, c3 = st.columns(3)
        with c1:
            firm_sel = st.selectbox("Firma / Şube", fopts)
            order_date = st.date_input("Sipariş tarihi", value=date.today())
        with c2:
            delivery_date = st.date_input("Tahmini teslim tarihi", value=date.today())
            status = st.selectbox("Sipariş durumu", ORDER_STATUSES)
        with c3:
            payment_status = st.selectbox("Ödeme durumu", PAYMENT_STATUSES)
            creator = st.text_input("Oluşturan", st.session_state.get("username", "admin"))
        shipping_note = st.text_area("Sevkiyat notu")
        general_note = st.text_area("Genel not")

        st.markdown("## Ürün Kalemleri")
        product_sel = st.selectbox("Ürün", popts)
        pc1, pc2, pc3 = st.columns([2, 1, 1])
        with pc1:
            item_note = st.text_input("Kalem notu")
        with pc2:
            qty = st.number_input("Adet", min_value=1, step=1, value=1)
        selected_pid = product_sel.split(" | ", 1)[0]
        selected_product = products[products["Urun_ID"] == selected_pid].iloc[0]
        default_price = float(money_to_float(selected_product.get("Birim_Fiyat", 0)))
        with pc3:
            unit_price = st.number_input("Birim fiyat", min_value=0.0, step=10.0, value=default_price, format="%.2f")
        submitted = st.form_submit_button(f"Siparişi kaydet — Toplam: {fmt_money(qty * unit_price)}", use_container_width=True)

    if submitted:
        firm_id = firm_sel.split(" | ", 1)[0]
        firm = firms[firms["Firma_ID"] == firm_id].iloc[0]
        order_no = next_order_no(orders)
        order_row = {
            "Siparis_No": order_no,
            "Firma_ID": firm_id,
            "Firma_Adi": firm["Firma_Adi"],
            "Sube": firm["Sube"],
            "Siparis_Tarihi": str(order_date),
            "Teslim_Tarihi": str(delivery_date),
            "Durum": status,
            "Odeme_Durumu": payment_status,
            "Toplam_Tutar": qty * unit_price,
            "Odenen_Tutar": 0,
            "Sevkiyat_Notu": shipping_note,
            "Genel_Not": general_note,
            "Olusturan": creator,
        }
        item_row = {
            "Kalem_ID": next_id(items, "K", "Kalem_ID"),
            "Siparis_No": order_no,
            "Urun_ID": selected_product["Urun_ID"],
            "Urun_Adi": selected_product["Urun_Adi"],
            "Model": selected_product["Model"],
            "Renk": selected_product["Renk"],
            "Adet": qty,
            "Birim_Fiyat": unit_price,
            "Satir_Toplam": qty * unit_price,
            "Not": item_note,
        }
        try:
            append_row("Siparisler", order_row, data)
            clear_data_cache()
            fresh = load_all_data()
            append_row("Siparis_Kalemleri", item_row, fresh)
            st.success(f"Sipariş kaydedildi: {order_no}")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))


def orders_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Siparişler")
    st.caption("Siparişleri filtreleyin, durum ve ödeme bilgisini güncelleyin")

    if orders.empty:
        st.info("Henüz sipariş yok.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        firm_search = st.text_input("Firma ara")
    with c2:
        status_filter = st.selectbox("Durum filtresi", ["Tümü"] + ORDER_STATUSES)
    with c3:
        pay_filter = st.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_STATUSES)

    view = orders.copy()
    if firm_search.strip():
        q = normalize_key(firm_search)
        view = view[view["Firma_Adi"].map(normalize_key).str.contains(q, na=False)]
    if status_filter != "Tümü":
        view = view[view["Durum"] == status_filter]
    if pay_filter != "Tümü":
        view = view[view["Odeme_Durumu"] == pay_filter]
    display = view.copy()
    display["Toplam_Tutar"] = display["Toplam_Tutar"].map(fmt_money)
    if "Odenen_Tutar" in display.columns:
        display["Odenen_Tutar"] = display["Odenen_Tutar"].map(fmt_money)
    show_df(display, height=350)

    st.markdown("## Sipariş Detayı / Güncelleme")
    order_opts = [f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}" for r in orders.itertuples()]
    selected = st.selectbox("Sipariş seç", order_opts)
    order_no = selected.split(" - ", 1)[0]
    current = orders[orders["Siparis_No"] == order_no].iloc[0]
    st.markdown(f"### {order_no}")
    order_items = items[items["Siparis_No"] == order_no].copy()
    if not order_items.empty:
        oi = order_items.copy()
        for c in ["Birim_Fiyat", "Satir_Toplam"]:
            oi[c] = oi[c].map(fmt_money)
        show_df(oi)
    else:
        st.info("Bu siparişe bağlı kalem yok.")

    with st.form("update_order"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_status = st.selectbox("Durum", ORDER_STATUSES, index=ORDER_STATUSES.index(current["Durum"]) if current["Durum"] in ORDER_STATUSES else 0)
        with c2:
            new_pay = st.selectbox("Ödeme durumu", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(current["Odeme_Durumu"]) if current["Odeme_Durumu"] in PAYMENT_STATUSES else 0)
        with c3:
            paid = st.number_input("Ödenen tutar", min_value=0.0, value=float(money_to_float(current.get("Odenen_Tutar", 0))), step=100.0, format="%.2f")
        shipping_note = st.text_area("Sevkiyat notu", current.get("Sevkiyat_Notu", ""))
        general_note = st.text_area("Genel not", current.get("Genel_Not", ""))
        save = st.form_submit_button("Siparişi güncelle", use_container_width=True)
    if save:
        idx = orders[orders["Siparis_No"] == order_no].index[0]
        orders.loc[idx, ["Durum", "Odeme_Durumu", "Odenen_Tutar", "Sevkiyat_Notu", "Genel_Not"]] = [new_status, new_pay, paid, shipping_note, general_note]
        try:
            rewrite_sheet("Siparisler", orders)
            st.success("Sipariş güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    with st.expander("Tehlikeli işlem: Siparişi sil"):
        st.warning("Silinen sipariş, kalemleri ve ödeme kayıtlarıyla birlikte kaldırılır.")
        confirm = st.checkbox(f"{order_no} siparişini silmek istiyorum")
        if st.button("Siparişi kalıcı sil", disabled=not confirm, use_container_width=True):
            try:
                rewrite_sheet("Siparisler", orders[orders["Siparis_No"] != order_no])
                rewrite_sheet("Siparis_Kalemleri", items[items["Siparis_No"] != order_no])
                rewrite_sheet("Odemeler", payments[payments["Siparis_No"] != order_no])
                st.success("Sipariş silindi.")
                st.rerun()
            except Exception as e:
                st.error(api_error_message(e))


def firms_page(data: Dict[str, pd.DataFrame]) -> None:
    firms = data["Firmalar"].copy()
    orders = data["Siparisler"].copy()
    st.markdown("# Firmalar")
    st.caption("Bayi, müşteri ve şube kartlarını yönetin")

    with st.expander("+ Yeni firma / şube ekle", expanded=True):
        with st.form("add_firm"):
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
                address = st.text_area("Adres")
                note = st.text_area("Not")
            submitted = st.form_submit_button("Firmayı kaydet", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Firma adı zorunlu.")
            else:
                row = {
                    "Firma_ID": next_id(firms, "F", "Firma_ID"), "Firma_Adi": name.strip(), "Sube": branch.strip(),
                    "Yetkili_Kisi": contact.strip(), "Telefon": phone.strip(), "Adres": address.strip(),
                    "Vergi_No": tax_no.strip(), "Vergi_Dairesi": tax_office.strip(), "Not": note.strip(),
                    "Aktif": "Aktif", "Kayit_Tarihi": now_str(),
                }
                try:
                    append_row("Firmalar", row, data)
                    st.success("Firma kaydedildi.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))

    st.markdown("## Kayıtlı Firmalar")
    show_df(firms)

    st.markdown("## Firma Düzelt / Sil")
    if firms.empty:
        st.info("Düzenlenecek firma yok.")
        return
    opts = [f"{r.Firma_ID} - {r.Firma_Adi} / {r.Sube}" for r in firms.itertuples()]
    selected = st.selectbox("Firma seç", opts)
    firm_id = selected.split(" - ", 1)[0]
    current = firms[firms["Firma_ID"] == firm_id].iloc[0]
    with st.form("edit_firm"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Firma adı", current["Firma_Adi"])
            branch = st.text_input("Şube", current["Sube"])
            contact = st.text_input("Yetkili kişi", current["Yetkili_Kisi"])
        with c2:
            phone = st.text_input("Telefon", current["Telefon"])
            tax_no = st.text_input("Vergi No / VKN", current["Vergi_No"])
            tax_office = st.text_input("Vergi Dairesi", current["Vergi_Dairesi"])
        with c3:
            active = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if current["Aktif"] != "Pasif" else 1)
            address = st.text_area("Adres", current["Adres"])
            note = st.text_area("Not", current["Not"])
        save = st.form_submit_button("Firma bilgilerini güncelle", use_container_width=True)
    if save:
        idx = firms[firms["Firma_ID"] == firm_id].index[0]
        firms.loc[idx, ["Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres", "Vergi_No", "Vergi_Dairesi", "Not", "Aktif"]] = [name, branch, contact, phone, address, tax_no, tax_office, note, active]
        try:
            rewrite_sheet("Firmalar", firms)
            st.success("Firma güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    used = firm_id in set(orders["Firma_ID"].astype(str)) if not orders.empty else False
    with st.expander("Sil / Pasife al"):
        if used:
            st.info("Bu firma geçmiş siparişlerde kullanılmış. Raporlar bozulmasın diye kalıcı silmek yerine pasife alınır.")
            if st.button("Firmayı pasife al", use_container_width=True):
                firms.loc[firms["Firma_ID"] == firm_id, "Aktif"] = "Pasif"
                rewrite_sheet("Firmalar", firms)
                st.rerun()
        else:
            confirm = st.checkbox("Bu firmayı kalıcı sil")
            if st.button("Firmayı sil", disabled=not confirm, use_container_width=True):
                rewrite_sheet("Firmalar", firms[firms["Firma_ID"] != firm_id])
                st.rerun()


def products_page(data: Dict[str, pd.DataFrame]) -> None:
    products = data["Urunler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    st.markdown("# Ürünler")
    st.caption("Ürün kartları, renkler, fiyatlar ve stok bilgisi")

    with st.expander("+ Yeni ürün ekle", expanded=True):
        with st.form("add_product"):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Ürün adı *")
                model = st.text_input("Model")
                category = st.text_input("Kategori")
            with c2:
                color = st.text_input("Renk")
                price = st.number_input("Birim fiyat", min_value=0.0, step=10.0, format="%.2f")
            with c3:
                stock = st.number_input("Stok", min_value=0, step=1)
                note = st.text_area("Not")
            submitted = st.form_submit_button("Ürünü kaydet", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Ürün adı zorunlu.")
            else:
                row = {
                    "Urun_ID": next_id(products, "U", "Urun_ID"), "Kategori": category.strip(),
                    "Urun_Adi": name.strip(), "Model": model.strip(), "Renk": color.strip(),
                    "Birim_Fiyat": price, "Stok": stock, "Not": note.strip(), "Aktif": "Aktif", "Kayit_Tarihi": now_str(),
                }
                try:
                    append_row("Urunler", row, data)
                    st.success("Ürün kaydedildi.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))

    st.markdown("## Kayıtlı Ürünler")
    view = products.copy()
    if not view.empty:
        view["Birim_Fiyat"] = view["Birim_Fiyat"].map(fmt_money)
    show_df(view)

    st.markdown("## Ürün Düzelt / Sil")
    if products.empty:
        st.info("Düzenlenecek ürün yok.")
        return
    opts = [f"{r.Urun_ID} - {r.Urun_Adi} / {r.Renk} / {r.Model}" for r in products.itertuples()]
    selected = st.selectbox("Ürün seç", opts)
    product_id = selected.split(" - ", 1)[0]
    current = products[products["Urun_ID"] == product_id].iloc[0]
    with st.form("edit_product"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Ürün adı", current["Urun_Adi"])
            model = st.text_input("Model", current["Model"])
            category = st.text_input("Kategori", current["Kategori"])
        with c2:
            color = st.text_input("Renk", current["Renk"])
            price = st.number_input("Birim fiyat", min_value=0.0, value=float(money_to_float(current["Birim_Fiyat"])), step=10.0, format="%.2f")
        with c3:
            stock = st.number_input("Stok", min_value=0, value=int(money_to_float(current["Stok"])), step=1)
            active = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if current["Aktif"] != "Pasif" else 1)
            note = st.text_area("Not", current["Not"])
        save = st.form_submit_button("Ürün bilgilerini güncelle", use_container_width=True)
    if save:
        idx = products[products["Urun_ID"] == product_id].index[0]
        products.loc[idx, ["Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Not", "Aktif"]] = [category, name, model, color, price, stock, note, active]
        try:
            rewrite_sheet("Urunler", products)
            st.success("Ürün güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    used = product_id in set(items["Urun_ID"].astype(str)) if not items.empty else False
    with st.expander("Sil / Pasife al"):
        if used:
            st.info("Bu ürün geçmiş siparişlerde kullanılmış. Raporlar bozulmasın diye kalıcı silmek yerine pasife alınır.")
            if st.button("Ürünü pasife al", use_container_width=True):
                products.loc[products["Urun_ID"] == product_id, "Aktif"] = "Pasif"
                rewrite_sheet("Urunler", products)
                st.rerun()
        else:
            confirm = st.checkbox("Bu ürünü kalıcı sil")
            if st.button("Ürünü sil", disabled=not confirm, use_container_width=True):
                rewrite_sheet("Urunler", products[products["Urun_ID"] != product_id])
                st.rerun()


def payments_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Ödemeler")
    st.caption("Tahsilatları kaydedin ve hatalı ödeme kayıtlarını silin")
    if orders.empty:
        st.info("Ödeme eklemek için önce sipariş oluşturmalısın.")
        return

    order_opts = [f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}" for r in orders.itertuples()]
    with st.form("add_payment"):
        selected = st.selectbox("Sipariş", order_opts)
        c1, c2, c3 = st.columns(3)
        with c1:
            pay_date = st.date_input("Ödeme tarihi", value=date.today())
        with c2:
            amount = st.number_input("Tutar", min_value=0.0, step=100.0, format="%.2f")
        with c3:
            pay_type = st.selectbox("Ödeme türü", PAYMENT_TYPES)
        note = st.text_input("Not")
        submitted = st.form_submit_button("Ödemeyi kaydet", use_container_width=True)
    if submitted:
        order_no = selected.split(" - ", 1)[0]
        row = {"Odeme_ID": next_id(payments, "P", "Odeme_ID"), "Siparis_No": order_no, "Tarih": str(pay_date), "Tutar": amount, "Odeme_Turu": pay_type, "Not": note, "Kayit_Tarihi": now_str()}
        try:
            append_row("Odemeler", row, data)
            # Update order paid total.
            fresh = load_all_data()
            payments2 = fresh["Odemeler"]
            orders2 = fresh["Siparisler"]
            paid_total = payments2[payments2["Siparis_No"] == order_no]["Tutar"].map(money_to_float).sum()
            orders2.loc[orders2["Siparis_No"] == order_no, "Odenen_Tutar"] = paid_total
            total = money_to_float(orders2.loc[orders2["Siparis_No"] == order_no, "Toplam_Tutar"].iloc[0])
            if paid_total >= total and total > 0:
                orders2.loc[orders2["Siparis_No"] == order_no, "Odeme_Durumu"] = "Ödendi"
            elif paid_total > 0:
                orders2.loc[orders2["Siparis_No"] == order_no, "Odeme_Durumu"] = "Kısmi Ödendi"
            rewrite_sheet("Siparisler", orders2)
            st.success("Ödeme kaydedildi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    st.markdown("## Ödeme Kayıtları")
    view = payments.copy()
    if not view.empty:
        view["Tutar"] = view["Tutar"].map(fmt_money)
    show_df(view)
    if not payments.empty:
        st.markdown("## Ödeme Sil")
        opts = [f"{r.Odeme_ID} - {r.Siparis_No} / {fmt_money(r.Tutar)}" for r in payments.itertuples()]
        selected = st.selectbox("Ödeme seç", opts)
        pay_id = selected.split(" - ", 1)[0]
        confirm = st.checkbox("Bu ödeme kaydını sil")
        if st.button("Ödemeyi sil", disabled=not confirm, use_container_width=True):
            try:
                rewrite_sheet("Odemeler", payments[payments["Odeme_ID"] != pay_id])
                st.success("Ödeme silindi.")
                st.rerun()
            except Exception as e:
                st.error(api_error_message(e))


def reports_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    st.markdown("# Raporlar")
    st.caption("Firma, ürün ve durum bazlı özetler")

    if orders.empty:
        st.info("Rapor için sipariş verisi yok.")
        download_excel_button(data)
        return

    active_orders = orders[~orders["Durum"].map(normalize_key).isin({"iptal", "iptal_edildi"})].copy()
    firm_report = active_orders.groupby("Firma_Adi", dropna=False).agg(Siparis_Adedi=("Siparis_No", "count"), Toplam_Ciro=("Toplam_Tutar", "sum")).reset_index()
    st.markdown("## Firma Bazlı Satış")
    show_df(firm_report)
    if not firm_report.empty:
        st.bar_chart(firm_report.set_index("Firma_Adi")[["Toplam_Ciro"]])

    st.markdown("## Ürün Bazlı Satış")
    if items.empty:
        st.info("Ürün kalemi yok.")
    else:
        product_report = items.groupby("Urun_Adi", dropna=False).agg(Toplam_Adet=("Adet", "sum"), Toplam_Tutar=("Satir_Toplam", "sum")).reset_index()
        show_df(product_report)
        if not product_report.empty:
            st.bar_chart(product_report.set_index("Urun_Adi")[["Toplam_Adet"]])

    st.markdown("## Excel Dışa Aktar")
    download_excel_button(data, "Rapor ve tüm verileri indir")


def settings_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Yedek / Ayarlar")
    st.caption("Google Sheets bağlantı kontrolü, tablo onarımı ve Excel yedeği")
    st.markdown("## Google Sheets Bağlantısı")
    st.success("Google Sheets bağlantısı aktif.")
    st.code(f"SPREADSHEET_ID = {spreadsheet_id()}")

    st.markdown("## Tablo Onarımı")
    st.warning("Sheet başlıkları kaydıysa veya eski demo satırlar görünüyorsa bu butona bir kez bas. Üst üste basma; Google kotası dolabilir.")
    if st.button("Tabloları onar ve temizle", use_container_width=True):
        try:
            with st.spinner("Tablolar temizleniyor..."):
                counts = repair_all_tables()
            st.success("Tablolar temizlendi: " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    if st.button("Verileri yenile", use_container_width=True):
        clear_data_cache()
        st.rerun()

    st.markdown("## Excel Yedeği İndir")
    download_excel_button(data)

    st.markdown("## Şifre")
    st.info("Kalıcı şifre değişimi için Streamlit > Manage app > Settings > Secrets alanına APP_PASSWORD = \"yeni_sifren\" ekle.")

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    set_page()
    if not st.session_state.get("logged_in"):
        login_page()
        return
    page = sidebar()
    try:
        with st.spinner("Google Sheets verileri okunuyor..."):
            data = load_all_data()
    except Exception as e:
        st.error("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
        st.error(api_error_message(e))
        st.info("1-2 dakika bekleyip sayfayı yenileyin. Devam ederse service account mailinin Sheet'e Düzenleyici olarak eklendiğini ve Secrets değerlerini kontrol edin.")
        return

    try:
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
    except Exception as e:
        st.error("Bu sayfada beklenmeyen bir hata oluştu.")
        st.error(api_error_message(e))
        st.exception(e)


if __name__ == "__main__":
    main()
