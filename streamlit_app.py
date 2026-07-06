# Günday's Home Sipariş Takip - Google Sheets V6 Final
# Ana veri kaynağı: Google Sheets

from __future__ import annotations

import io
import math
import re
import time
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

APP_TITLE = "Günday's Home Sipariş Takip"
DEFAULT_SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CACHE_TTL_SECONDS = 300

SHEETS: Dict[str, Dict[str, Any]] = {
    "Firmalar": {
        "primary": "Firma_ID",
        "headers": [
            "Firma_ID", "Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres",
            "Vergi_No", "Vergi_Dairesi", "Not", "Aktif", "Kayit_Tarihi"
        ],
        "aliases": {
            "Firma_ID": ["firma_id", "firma id", "id", "bayi_id", "musteri_id"],
            "Firma_Adi": ["firma_adi", "firma adi", "firma adı", "firma", "firma_adı", "bayi", "musteri", "müşteri", "cari"],
            "Sube": ["sube", "şube", "magaza", "mağaza"],
            "Yetkili_Kisi": ["yetkili_kisi", "yetkili kişi", "yetkili", "ilgili"],
            "Telefon": ["telefon", "tel", "gsm"],
            "Adres": ["adres"],
            "Vergi_No": ["vergi_no", "vergi no", "vkn", "tckn", "vergi numarasi", "vergi numarası"],
            "Vergi_Dairesi": ["vergi_dairesi", "vergi dairesi"],
            "Not": ["not", "aciklama", "açıklama"],
            "Aktif": ["aktif", "durum", "status"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi", "tarih"],
        },
    },
    "Urunler": {
        "primary": "Urun_ID",
        "headers": [
            "Urun_ID", "Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat",
            "Stok", "Not", "Aktif", "Kayit_Tarihi"
        ],
        "aliases": {
            "Urun_ID": ["urun_id", "ürün id", "urun id", "id"],
            "Kategori": ["kategori", "urun_grubu", "ürün grubu", "grup"],
            "Urun_Adi": ["urun_adi", "ürün adı", "urun adi", "ürün", "urun", "ad", "adi", "adı"],
            "Model": ["model"],
            "Renk": ["renk", "color"],
            "Birim_Fiyat": ["birim_fiyat", "birim fiyat", "fiyat", "satis_fiyati", "satış fiyatı", "liste fiyatı"],
            "Stok": ["stok", "stock"],
            "Not": ["not", "aciklama", "açıklama"],
            "Aktif": ["aktif", "durum", "status"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi", "tarih"],
        },
    },
    "Siparisler": {
        "primary": "Siparis_No",
        "headers": [
            "Siparis_No", "Firma_ID", "Firma_Adi", "Sube", "Siparis_Tarihi",
            "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Odenen_Tutar",
            "Sevkiyat_Notu", "Genel_Not", "Olusturan"
        ],
        "aliases": {
            "Siparis_No": ["siparis_no", "sipariş no", "siparis no", "sipariş_no", "order_no", "no"],
            "Firma_ID": ["firma_id", "firma id"],
            "Firma_Adi": ["firma_adi", "firma adı", "firma adi", "firma", "musteri", "müşteri"],
            "Sube": ["sube", "şube"],
            "Siparis_Tarihi": ["siparis_tarihi", "sipariş tarihi", "siparis tarihi", "tarih"],
            "Teslim_Tarihi": ["teslim_tarihi", "teslim tarihi", "termin", "tahmini teslim tarihi"],
            "Durum": ["durum", "siparis durumu", "sipariş durumu"],
            "Odeme_Durumu": ["odeme_durumu", "ödeme durumu", "odeme durumu", "ödeme"],
            "Toplam_Tutar": ["toplam_tutar", "toplam tutar", "toplam", "ciro", "sipariş toplamı"],
            "Odenen_Tutar": ["odenen_tutar", "ödenen tutar", "tahsilat", "tahsil edilen"],
            "Sevkiyat_Notu": ["sevkiyat_notu", "sevkiyat notu", "teslimat notu"],
            "Genel_Not": ["genel_not", "genel not", "not", "aciklama", "açıklama"],
            "Olusturan": ["olusturan", "oluşturan", "kullanici", "kullanıcı"],
        },
    },
    "Siparis_Kalemleri": {
        "primary": "Kalem_ID",
        "headers": [
            "Kalem_ID", "Siparis_No", "Urun_ID", "Urun_Adi", "Model", "Renk",
            "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"
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
            "Not": ["not", "aciklama", "açıklama"],
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
            "Not": ["not", "aciklama", "açıklama"],
            "Kayit_Tarihi": ["kayit_tarihi", "kayıt tarihi"],
        },
    },
}

ORDER_STATUSES = ["Sipariş Alındı", "Üretimde", "Hazır", "Sevkiyat Bekliyor", "Gönderildi", "Teslim Edildi", "İptal"]
PAYMENT_STATUSES = ["Bekliyor", "Vadeli", "Kısmi Ödendi", "Ödendi", "İade", "İptal"]
PAYMENT_TYPES = ["Nakit", "Havale/EFT", "Kredi Kartı", "Çek/Senet", "Diğer"]

# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------

def normalize_key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def money_to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace("TL", "").replace("₺", "").strip()
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in {"-", ",", "."}:
        return 0.0
    # Turkish money: 12.850,50 -> 12850.50. Also handle 12850.50.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        # If multiple dots, they are thousands separators.
        if text.count(".") > 1:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def int_to_float(value: Any) -> float:
    return money_to_float(value)


def fmt_money(value: Any) -> str:
    val = money_to_float(value)
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def make_alias_map(sheet_name: str) -> Dict[str, str]:
    config = SHEETS[sheet_name]
    mapping: Dict[str, str] = {}
    for canonical in config["headers"]:
        mapping[normalize_key(canonical)] = canonical
    for canonical, aliases in config.get("aliases", {}).items():
        for alias in aliases:
            mapping[normalize_key(alias)] = canonical
    return mapping


def canonicalize_status(value: Any, default: str = "Aktif") -> str:
    text = safe_str(value)
    if not text:
        return default
    norm = normalize_key(text)
    if norm in {"pasif", "kapali", "kapali_kayit", "silindi", "0", "false", "hayir", "hayır"}:
        return "Pasif"
    if norm in {"aktif", "acik", "açık", "1", "true", "evet"}:
        return "Aktif"
    return text


def is_header_like(value: Any, headers: List[str]) -> bool:
    n = normalize_key(value)
    return n in {normalize_key(h) for h in headers} or n in {"id", "kategori", "model", "renk", "stok", "durum", "not"}

# -----------------------------------------------------------------------------
# Google Sheets service
# -----------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_sheets_service():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Streamlit Secrets içinde [gcp_service_account] bulunamadı.")
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def get_spreadsheet_id() -> str:
    return st.secrets.get("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)


def api_error_message(err: Exception) -> str:
    if isinstance(err, HttpError):
        text = str(err)
        if "Quota exceeded" in text or "quota" in text.lower() or "429" in text:
            return (
                "Google Sheets okuma kotası geçici olarak doldu. 1-2 dakika bekleyip sayfayı yenileyin. "
                "Bu sürüm kotayı azaltır; tekrar tekrar reboot/yenileme yapmayın."
            )
        if "403" in text:
            return "Google Sheet yetki hatası. Service account mailinin Sheet dosyasında Düzenleyici olduğundan emin olun."
        if "404" in text:
            return "Google Sheet bulunamadı. SPREADSHEET_ID yanlış olabilir."
        return text[:900]
    return str(err)


def _empty_df(sheet_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SHEETS[sheet_name]["headers"])


def parse_sheet_values(sheet_name: str, values: List[List[Any]]) -> pd.DataFrame:
    config = SHEETS[sheet_name]
    headers = config["headers"]
    primary = config["primary"]
    alias_map = make_alias_map(sheet_name)

    if not values:
        return _empty_df(sheet_name)

    # Find the best header row. Prefer rows where the primary key appears early.
    candidates: List[Tuple[int, int, int]] = []
    primary_norm = normalize_key(primary)
    for i, row in enumerate(values[:12]):
        normalized = [normalize_key(c) for c in row]
        canonical_hits = [alias_map.get(c) for c in normalized if c in alias_map]
        score = len(set(canonical_hits))
        primary_bonus = 0
        for pos, cell in enumerate(normalized[:4]):
            if alias_map.get(cell) == primary or cell == primary_norm:
                primary_bonus = 100 - pos
                break
        # Avoid pure title rows like "Ürün Kartları" even if later cells match shifted headers.
        first_cell_quality = 10 if normalized and alias_map.get(normalized[0]) == primary else 0
        candidates.append((score + primary_bonus + first_cell_quality, score, i))

    best = max(candidates, key=lambda x: (x[0], x[1], -x[2])) if candidates else (0, 0, 0)
    header_idx = best[2]
    raw_headers = values[header_idx] if header_idx < len(values) else []

    # If the selected row still does not contain the primary key, create canonical mapping by position.
    selected_norm = [normalize_key(c) for c in raw_headers]
    if all(alias_map.get(c) != primary for c in selected_norm):
        raw_headers = headers

    # Build column mapping. Duplicate names get ignored after first occurrence.
    column_to_canonical: Dict[int, str] = {}
    used: set[str] = set()
    for idx, cell in enumerate(raw_headers):
        can = alias_map.get(normalize_key(cell))
        if can and can not in used:
            column_to_canonical[idx] = can
            used.add(can)

    # Fallback: if we have too few mappings, assume canonical order.
    if len(column_to_canonical) < 2:
        column_to_canonical = {i: h for i, h in enumerate(headers)}

    records: List[Dict[str, Any]] = []
    data_rows = values[header_idx + 1:]
    for row in data_rows:
        rec = {h: "" for h in headers}
        for idx, can in column_to_canonical.items():
            if idx < len(row):
                rec[can] = safe_str(row[idx])
        # Drop repeated header rows and empty rows.
        primary_value = safe_str(rec.get(primary))
        if not primary_value:
            continue
        if is_header_like(primary_value, headers):
            continue
        if primary == "Siparis_No" and not primary_value.upper().startswith("GH-"):
            continue
        if primary == "Urun_ID" and not primary_value.upper().startswith("U-"):
            continue
        if primary == "Firma_ID" and not primary_value.upper().startswith("F-"):
            continue
        if primary == "Kalem_ID" and not primary_value.upper().startswith("K-"):
            continue
        if primary == "Odeme_ID" and not primary_value.upper().startswith("O-"):
            continue
        records.append(rec)

    df = pd.DataFrame(records, columns=headers)
    return normalize_df(sheet_name, df)


def normalize_df(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
    headers = SHEETS[sheet_name]["headers"]
    primary = SHEETS[sheet_name]["primary"]
    if df is None or df.empty:
        return pd.DataFrame(columns=headers)
    for h in headers:
        if h not in df.columns:
            df[h] = ""
    df = df[headers].copy()
    df = df.fillna("").astype(str)
    # Remove hidden/polluted header rows.
    df = df[df[primary].astype(str).str.strip() != ""]
    df = df[~df[primary].apply(lambda x: is_header_like(x, headers))]

    if sheet_name in {"Firmalar", "Urunler"}:
        if "Aktif" in df.columns:
            df["Aktif"] = df["Aktif"].apply(lambda x: canonicalize_status(x, "Aktif"))
        else:
            df["Aktif"] = "Aktif"
    if sheet_name == "Siparisler":
        for col in ["Toplam_Tutar", "Odenen_Tutar"]:
            df[col] = df[col].apply(money_to_float)
    if sheet_name == "Siparis_Kalemleri":
        for col in ["Adet", "Birim_Fiyat", "Satir_Toplam"]:
            df[col] = df[col].apply(money_to_float)
    if sheet_name == "Odemeler":
        df["Tutar"] = df["Tutar"].apply(money_to_float)
    if sheet_name == "Urunler":
        df["Birim_Fiyat"] = df["Birim_Fiyat"].apply(money_to_float)
        df["Stok"] = df["Stok"].apply(money_to_float)
    return df.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def read_all_data_cached(spreadsheet_id: str) -> Dict[str, pd.DataFrame]:
    service = get_sheets_service()
    ranges = [f"'{name}'!A1:Z2000" for name in SHEETS.keys()]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()
    value_ranges = result.get("valueRanges", [])
    data: Dict[str, pd.DataFrame] = {}
    for sheet_name, value_range in zip(SHEETS.keys(), value_ranges):
        data[sheet_name] = parse_sheet_values(sheet_name, value_range.get("values", []))
    # In case API returned fewer ranges due missing tabs.
    for sheet_name in SHEETS.keys():
        data.setdefault(sheet_name, _empty_df(sheet_name))
    return data


def load_data() -> Dict[str, pd.DataFrame]:
    return read_all_data_cached(get_spreadsheet_id())


def clear_data_cache() -> None:
    read_all_data_cached.clear()


def values_for_df(sheet_name: str, df: pd.DataFrame) -> List[List[Any]]:
    headers = SHEETS[sheet_name]["headers"]
    if df is None:
        df = pd.DataFrame(columns=headers)
    df = normalize_df(sheet_name, df)
    rows: List[List[Any]] = [headers]
    for _, row in df.iterrows():
        rows.append([safe_str(row.get(h, "")) for h in headers])
    return rows


def rewrite_sheet(sheet_name: str, df: pd.DataFrame) -> None:
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id()
    values = values_for_df(sheet_name, df)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:Z5000",
        body={},
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()
    clear_data_cache()


def append_row(sheet_name: str, row: Dict[str, Any]) -> None:
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id()
    headers = SHEETS[sheet_name]["headers"]
    values = [[safe_str(row.get(h, "")) for h in headers]]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    clear_data_cache()


def append_rows(sheet_name: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id()
    headers = SHEETS[sheet_name]["headers"]
    values = [[safe_str(row.get(h, "")) for h in headers] for row in rows]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    clear_data_cache()


def repair_all_sheets(data: Dict[str, pd.DataFrame]) -> None:
    # Rewrites every main tab in canonical header order and removes polluted/blank rows.
    for sheet_name in SHEETS.keys():
        rewrite_sheet(sheet_name, data.get(sheet_name, _empty_df(sheet_name)))
    clear_data_cache()


def next_id(df: pd.DataFrame, prefix: str, col: str, digits: int = 4) -> str:
    max_num = 0
    if df is not None and not df.empty and col in df.columns:
        for val in df[col].astype(str):
            m = re.search(rf"{re.escape(prefix)}-?(\d+)$", val.strip(), re.IGNORECASE)
            if m:
                max_num = max(max_num, int(m.group(1)))
    return f"{prefix}-{max_num + 1:0{digits}d}"


def next_order_no(orders: pd.DataFrame) -> str:
    year = datetime.now().year
    pattern = re.compile(rf"GH-{year}-(\d+)$", re.IGNORECASE)
    max_num = 0
    if orders is not None and not orders.empty and "Siparis_No" in orders.columns:
        for val in orders["Siparis_No"].astype(str):
            m = pattern.search(val.strip())
            if m:
                max_num = max(max_num, int(m.group(1)))
    return f"GH-{year}-{max_num + 1:04d}"


def active_firms(firms: pd.DataFrame) -> pd.DataFrame:
    if firms is None or firms.empty:
        return pd.DataFrame(columns=SHEETS["Firmalar"]["headers"])
    out = firms.copy()
    if "Aktif" in out.columns:
        out = out[out["Aktif"].astype(str).str.lower() != "pasif"]
    return out.reset_index(drop=True)


def active_products(products: pd.DataFrame) -> pd.DataFrame:
    if products is None or products.empty:
        return pd.DataFrame(columns=SHEETS["Urunler"]["headers"])
    out = products.copy()
    if "Aktif" in out.columns:
        out = out[out["Aktif"].astype(str).str.lower() != "pasif"]
    return out.reset_index(drop=True)

# -----------------------------------------------------------------------------
# Theme / UI helpers
# -----------------------------------------------------------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #050b14;
            --panel: #0a1324;
            --panel2: #111827;
            --gold: #d6a84f;
            --gold2: #f4d47b;
            --text: #f8fafc;
            --muted: #b8c0cc;
            --line: rgba(214,168,79,.35);
        }
        .stApp {
            background:
                radial-gradient(circle at 0% 0%, rgba(214,168,79,.16), transparent 24%),
                linear-gradient(120deg, #05070b 0%, #071327 62%, #0d1b34 100%);
            color: var(--text);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #081121 0%, #0d1728 100%);
            border-right: 1px solid rgba(214,168,79,.25);
        }
        [data-testid="stSidebar"] * { color: #f8fafc !important; }
        h1, h2, h3 { color: #ffffff !important; letter-spacing: -.03em; }
        .small-muted { color: var(--muted); font-size: .92rem; }
        .premium-card {
            border: 1px solid rgba(214,168,79,.55);
            background: linear-gradient(145deg, rgba(13,24,44,.98), rgba(8,13,24,.98));
            border-radius: 18px;
            padding: 24px 22px;
            box-shadow: 0 12px 34px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.04);
            min-height: 130px;
        }
        .premium-card .label { color: #ffffff; font-weight: 800; font-size: .95rem; }
        .premium-card .value { color: #ffffff; font-weight: 900; font-size: 2.05rem; margin-top: 12px; }
        .premium-card .hint { color: var(--gold2); font-weight: 700; font-size: .82rem; margin-top: 10px; }
        .status-pill {
            display: inline-block; padding: 4px 10px; border-radius: 999px; font-weight: 800; font-size: .78rem;
            border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.08);
        }
        .stButton > button, .stDownloadButton > button, button[kind="secondary"] {
            background: linear-gradient(90deg, rgba(214,168,79,.24), rgba(214,168,79,.08)) !important;
            border: 1px solid rgba(214,168,79,.75) !important;
            color: #ffffff !important; border-radius: 12px !important; font-weight: 800 !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: rgba(244,212,123,.95) !important; box-shadow: 0 0 0 2px rgba(214,168,79,.18);
        }
        [data-testid="stDataFrame"], .stDataFrame { border-radius: 14px !important; overflow: hidden !important; }
        div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {
            background: rgba(255,255,255,.09) !important;
            color: white !important;
            border-color: rgba(255,255,255,.18) !important;
        }
        label, .stMarkdown p, .stCaption, .stText { color: #f8fafc !important; }
        .stAlert { border-radius: 14px; }
        hr { border-color: rgba(214,168,79,.18); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, hint: str = "") -> str:
    return f"""
    <div class=\"premium-card\">
        <div class=\"label\">{label}</div>
        <div class=\"value\">{value}</div>
        <div class=\"hint\">{hint}</div>
    </div>
    """


def show_df(df: pd.DataFrame, use_container_width: bool = True, height: int | None = None) -> None:
    if df is None or df.empty:
        st.info("Gösterilecek kayıt yok.")
        return
    st.dataframe(df, use_container_width=use_container_width, hide_index=True, height=height)


def display_orders_table(orders: pd.DataFrame, max_rows: int | None = None) -> None:
    if orders is None or orders.empty:
        st.info("Henüz sipariş yok.")
        return
    cols = ["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Odenen_Tutar"]
    view = orders.copy()
    for c in ["Toplam_Tutar", "Odenen_Tutar"]:
        if c in view.columns:
            view[c] = view[c].apply(fmt_money)
    view = view[[c for c in cols if c in view.columns]]
    if max_rows:
        view = view.tail(max_rows).iloc[::-1]
    show_df(view, height=280 if len(view) > 5 else None)

# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------

def login_page() -> None:
    st.markdown(f"# {APP_TITLE}")
    st.caption("Sipariş, firma, ürün, sevkiyat ve ödeme durumlarını tek panelden yönetin.")
    col1, col2, col3 = st.columns([1, 1.25, 1])
    with col2:
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
        st.info("İlk kurulum bilgisi: admin / admin123. Canlı kullanımda Streamlit Secrets üzerinden APP_PASSWORD değiştirin.")

# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------

def dashboard_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Dashboard")
    st.caption("Günday's Home genel sipariş özeti")

    total_orders = len(orders)
    active_orders = len(orders[~orders["Durum"].astype(str).str.lower().eq("iptal")]) if not orders.empty else 0
    total_revenue = orders[~orders["Durum"].astype(str).str.lower().eq("iptal")]["Toplam_Tutar"].sum() if not orders.empty else 0
    total_paid = payments["Tutar"].sum() if not payments.empty else 0
    pending = max(float(total_revenue) - float(total_paid), 0.0)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Toplam Sipariş", str(total_orders), "Tüm kayıtlar"), unsafe_allow_html=True)
    c2.markdown(metric_card("Aktif Sipariş", str(active_orders), "İptal hariç"), unsafe_allow_html=True)
    c3.markdown(metric_card("Ciro", fmt_money(total_revenue), "Sipariş toplamı"), unsafe_allow_html=True)
    c4.markdown(metric_card("Ödeme Bekleyen", fmt_money(pending), "Tahsilat farkı"), unsafe_allow_html=True)

    st.divider()
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("## Son Siparişler")
        display_orders_table(orders, max_rows=8)
    with right:
        st.markdown("## Durum Dağılımı")
        if not orders.empty:
            chart = orders.groupby("Durum", dropna=False).size().reset_index(name="Adet")
            st.bar_chart(chart.set_index("Durum"), use_container_width=True)
        else:
            st.info("Grafik için veri yok.")

    st.markdown("## Hızlı Uyarılar")
    critical = []
    if not orders.empty:
        waiting = orders[orders["Durum"].isin(["Sipariş Alındı", "Üretimde", "Hazır", "Sevkiyat Bekliyor"])]
        if len(waiting) > 0:
            critical.append(f"Aktif süreçte {len(waiting)} sipariş var.")
        unpaid = pending
        if unpaid > 0:
            critical.append(f"Bekleyen tahsilat: {fmt_money(unpaid)}")
    if critical:
        for item in critical:
            st.warning(item)
    else:
        st.success("Şu an kritik uyarı yok.")


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
                    "Firma_ID": next_id(firms, "F", "Firma_ID"),
                    "Firma_Adi": name.strip(), "Sube": branch.strip(), "Yetkili_Kisi": contact.strip(),
                    "Telefon": phone.strip(), "Adres": address.strip(), "Vergi_No": tax_no.strip(),
                    "Vergi_Dairesi": tax_office.strip(), "Not": note.strip(), "Aktif": "Aktif", "Kayit_Tarihi": now_str(),
                }
                try:
                    append_row("Firmalar", row)
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
    options = [f"{r.Firma_ID} - {r.Firma_Adi} / {r.Sube}" for r in firms.itertuples()]
    selected = st.selectbox("Firma seç", options)
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
        firms.loc[firms["Firma_ID"] == firm_id, ["Firma_Adi", "Sube", "Yetkili_Kisi", "Telefon", "Adres", "Vergi_No", "Vergi_Dairesi", "Not", "Aktif"]] = [
            name, branch, contact, phone, address, tax_no, tax_office, note, active
        ]
        try:
            rewrite_sheet("Firmalar", firms)
            st.success("Firma güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    used = (not orders.empty) and firm_id in set(orders["Firma_ID"].astype(str))
    cdel1, cdel2 = st.columns([1, 3])
    with cdel1:
        if used:
            if st.button("Pasife al", use_container_width=True):
                firms.loc[firms["Firma_ID"] == firm_id, "Aktif"] = "Pasif"
                try:
                    rewrite_sheet("Firmalar", firms)
                    st.success("Firma pasife alındı. Geçmiş siparişler korunur.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))
        else:
            if st.button("Kalıcı sil", use_container_width=True):
                firms = firms[firms["Firma_ID"] != firm_id]
                try:
                    rewrite_sheet("Firmalar", firms)
                    st.success("Firma silindi.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))
    with cdel2:
        st.caption("Firma geçmiş siparişte kullanılmışsa silmek yerine pasife alınır.")


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
                    append_row("Urunler", row)
                    st.success("Ürün kaydedildi.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))

    st.markdown("## Kayıtlı Ürünler")
    view = products.copy()
    if not view.empty:
        view["Birim_Fiyat"] = view["Birim_Fiyat"].apply(fmt_money)
    show_df(view)

    st.markdown("## Ürün Düzelt / Sil")
    if products.empty:
        st.info("Düzenlenecek ürün yok.")
        return
    options = [f"{r.Urun_ID} - {r.Urun_Adi} / {r.Renk} / {r.Model}" for r in products.itertuples()]
    selected = st.selectbox("Ürün seç", options)
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
        products.loc[products["Urun_ID"] == product_id, ["Kategori", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Not", "Aktif"]] = [
            category, name, model, color, price, stock, note, active
        ]
        try:
            rewrite_sheet("Urunler", products)
            st.success("Ürün güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    used = (not items.empty) and product_id in set(items["Urun_ID"].astype(str))
    cdel1, cdel2 = st.columns([1, 3])
    with cdel1:
        if used:
            if st.button("Pasife al", use_container_width=True):
                products.loc[products["Urun_ID"] == product_id, "Aktif"] = "Pasif"
                try:
                    rewrite_sheet("Urunler", products)
                    st.success("Ürün pasife alındı. Geçmiş siparişler korunur.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))
        else:
            if st.button("Kalıcı sil", use_container_width=True):
                products = products[products["Urun_ID"] != product_id]
                try:
                    rewrite_sheet("Urunler", products)
                    st.success("Ürün silindi.")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))
    with cdel2:
        st.caption("Ürün geçmiş siparişte kullanılmışsa silmek yerine pasife alınır.")


def new_order_page(data: Dict[str, pd.DataFrame]) -> None:
    firms = active_firms(data["Firmalar"])
    products = active_products(data["Urunler"])
    orders = data["Siparisler"]
    items = data["Siparis_Kalemleri"]
    st.markdown("# Yeni Sipariş")
    st.caption("Firma seçin, ürünleri ekleyin, siparişi Google Sheets'e kaydedin")

    if firms.empty:
        st.warning("Önce Firmalar ekranından en az bir firma ekleyin. Eğer Sheet'te firma olduğu halde burada görünmüyorsa Yedek / Ayarlar > Tabloları onar ve temizle butonuna basın.")
        return
    if products.empty:
        st.warning("Önce Ürünler ekranından en az bir ürün ekleyin. Eğer Sheet'te ürün olduğu halde burada görünmüyorsa Yedek / Ayarlar > Tabloları onar ve temizle butonuna basın.")
        return

    if "cart" not in st.session_state:
        st.session_state["cart"] = []

    st.markdown("## Sipariş Bilgileri")
    c1, c2, c3 = st.columns(3)
    firm_labels = [f"{r.Firma_ID} | {r.Firma_Adi} | {r.Sube}" for r in firms.itertuples()]
    with c1:
        firm_label = st.selectbox("Firma / Şube", firm_labels)
        delivery = st.date_input("Tahmini teslim tarihi", value=date.today())
    with c2:
        order_status = st.selectbox("Sipariş durumu", ORDER_STATUSES, index=0)
        creator = st.text_input("Oluşturan", st.session_state.get("username", "admin"))
    with c3:
        payment_status = st.selectbox("Ödeme durumu", PAYMENT_STATUSES, index=0)
        shipment_note = st.text_area("Sevkiyat notu")
    general_note = st.text_area("Genel not")

    st.markdown("## Ürün Kalemi Ekle")
    product_labels = [f"{r.Urun_ID} | {r.Urun_Adi} | {r.Renk} | {r.Model} | {fmt_money(r.Birim_Fiyat)}" for r in products.itertuples()]
    pc1, pc2, pc3, pc4 = st.columns([2, .7, .9, .9])
    with pc1:
        product_label = st.selectbox("Ürün", product_labels)
    selected_product_id = product_label.split(" | ", 1)[0]
    product_row = products[products["Urun_ID"] == selected_product_id].iloc[0]
    with pc2:
        qty = st.number_input("Adet", min_value=1, value=1, step=1)
    with pc3:
        unit_price = st.number_input("Birim fiyat", min_value=0.0, value=float(money_to_float(product_row["Birim_Fiyat"])), step=10.0, format="%.2f")
    line_total = qty * unit_price
    with pc4:
        st.metric("Satır toplamı", fmt_money(line_total))
    item_note = st.text_input("Kalem notu")
    if st.button("+ Kalemi sepete ekle", use_container_width=True):
        st.session_state["cart"].append({
            "Urun_ID": product_row["Urun_ID"],
            "Urun_Adi": product_row["Urun_Adi"],
            "Model": product_row["Model"],
            "Renk": product_row["Renk"],
            "Adet": qty,
            "Birim_Fiyat": unit_price,
            "Satir_Toplam": line_total,
            "Not": item_note,
        })
        st.rerun()

    st.markdown("## Sepet")
    cart = st.session_state["cart"]
    if cart:
        cart_df = pd.DataFrame(cart)
        show_cart = cart_df.copy()
        show_cart["Birim_Fiyat"] = show_cart["Birim_Fiyat"].apply(fmt_money)
        show_cart["Satir_Toplam"] = show_cart["Satir_Toplam"].apply(fmt_money)
        show_df(show_cart)
        total = sum(float(x["Satir_Toplam"]) for x in cart)
        st.markdown(metric_card("Sipariş Toplamı", fmt_money(total), "Sepetteki kalem toplamı"), unsafe_allow_html=True)
        csave, cclear = st.columns([3, 1])
        with csave:
            if st.button("Siparişi kaydet", use_container_width=True):
                firm_id = firm_label.split(" | ", 1)[0]
                firm = firms[firms["Firma_ID"] == firm_id].iloc[0]
                order_no = next_order_no(orders)
                order_row = {
                    "Siparis_No": order_no,
                    "Firma_ID": firm["Firma_ID"],
                    "Firma_Adi": firm["Firma_Adi"],
                    "Sube": firm["Sube"],
                    "Siparis_Tarihi": today_str(),
                    "Teslim_Tarihi": delivery.strftime("%Y-%m-%d"),
                    "Durum": order_status,
                    "Odeme_Durumu": payment_status,
                    "Toplam_Tutar": total,
                    "Odenen_Tutar": 0,
                    "Sevkiyat_Notu": shipment_note,
                    "Genel_Not": general_note,
                    "Olusturan": creator,
                }
                start_no = len(items) + 1
                item_rows = []
                for idx, it in enumerate(cart, start=start_no):
                    row = dict(it)
                    row["Kalem_ID"] = f"K-{idx:04d}"
                    row["Siparis_No"] = order_no
                    item_rows.append(row)
                try:
                    append_row("Siparisler", order_row)
                    append_rows("Siparis_Kalemleri", item_rows)
                    st.session_state["cart"] = []
                    st.success(f"Sipariş kaydedildi: {order_no}")
                    st.rerun()
                except Exception as e:
                    st.error(api_error_message(e))
        with cclear:
            if st.button("Sepeti temizle", use_container_width=True):
                st.session_state["cart"] = []
                st.rerun()
    else:
        st.info("Sepette ürün yok.")


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
        search = st.text_input("Firma ara")
    with c2:
        status_filter = st.selectbox("Durum filtresi", ["Tümü"] + ORDER_STATUSES)
    with c3:
        payment_filter = st.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_STATUSES)

    filtered = orders.copy()
    if search.strip():
        s = search.strip().lower()
        filtered = filtered[filtered["Firma_Adi"].astype(str).str.lower().str.contains(s, na=False)]
    if status_filter != "Tümü":
        filtered = filtered[filtered["Durum"] == status_filter]
    if payment_filter != "Tümü":
        filtered = filtered[filtered["Odeme_Durumu"] == payment_filter]
    display_orders_table(filtered)

    st.markdown("## Sipariş Detayı / Güncelleme")
    options = [f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}" for r in orders.itertuples()]
    selected = st.selectbox("Sipariş seç", options)
    order_no = selected.split(" - ", 1)[0]
    current = orders[orders["Siparis_No"] == order_no].iloc[0]
    order_items = items[items["Siparis_No"] == order_no] if not items.empty else pd.DataFrame(columns=SHEETS["Siparis_Kalemleri"]["headers"])
    order_payments = payments[payments["Siparis_No"] == order_no] if not payments.empty else pd.DataFrame(columns=SHEETS["Odemeler"]["headers"])
    show_items = order_items.copy()
    if not show_items.empty:
        show_items["Birim_Fiyat"] = show_items["Birim_Fiyat"].apply(fmt_money)
        show_items["Satir_Toplam"] = show_items["Satir_Toplam"].apply(fmt_money)
    st.markdown("### Ürün Kalemleri")
    show_df(show_items)
    if not order_payments.empty:
        st.markdown("### Ödemeler")
        pay_view = order_payments.copy()
        pay_view["Tutar"] = pay_view["Tutar"].apply(fmt_money)
        show_df(pay_view)

    with st.form("update_order"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_status = st.selectbox("Sipariş durumu", ORDER_STATUSES, index=ORDER_STATUSES.index(current["Durum"]) if current["Durum"] in ORDER_STATUSES else 0)
        with c2:
            new_payment = st.selectbox("Ödeme durumu", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(current["Odeme_Durumu"]) if current["Odeme_Durumu"] in PAYMENT_STATUSES else 0)
        with c3:
            delivery_val = safe_str(current["Teslim_Tarihi"]) or today_str()
            try:
                delivery_date = datetime.strptime(delivery_val[:10], "%Y-%m-%d").date()
            except Exception:
                delivery_date = date.today()
            new_delivery = st.date_input("Teslim tarihi", delivery_date)
        ship_note = st.text_area("Sevkiyat notu", current["Sevkiyat_Notu"])
        general_note = st.text_area("Genel not", current["Genel_Not"])
        save = st.form_submit_button("Siparişi güncelle", use_container_width=True)
    if save:
        idx = orders[orders["Siparis_No"] == order_no].index
        orders.loc[idx, ["Durum", "Odeme_Durumu", "Teslim_Tarihi", "Sevkiyat_Notu", "Genel_Not"]] = [new_status, new_payment, new_delivery.strftime("%Y-%m-%d"), ship_note, general_note]
        try:
            rewrite_sheet("Siparisler", orders)
            st.success("Sipariş güncellendi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))

    st.markdown("### Sipariş Silme")
    st.warning("Kalıcı silme, sipariş kaydını, sipariş kalemlerini ve ödeme kayıtlarını Google Sheet'ten kaldırır.")
    confirm = st.checkbox(f"{order_no} siparişini kalıcı silmek istiyorum")
    if confirm and st.button("Siparişi kalıcı sil", use_container_width=True):
        try:
            rewrite_sheet("Siparisler", orders[orders["Siparis_No"] != order_no])
            rewrite_sheet("Siparis_Kalemleri", items[items["Siparis_No"] != order_no])
            rewrite_sheet("Odemeler", payments[payments["Siparis_No"] != order_no])
            st.success("Sipariş ve bağlantılı kayıtları silindi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))


def payments_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Ödemeler")
    st.caption("Tahsilat kayıtlarını girin ve hatalı ödemeleri silin")

    if orders.empty:
        st.info("Ödeme eklemek için önce sipariş oluşturun.")
        return

    st.markdown("## Yeni Ödeme Ekle")
    with st.form("add_payment"):
        order_options = [f"{r.Siparis_No} - {r.Firma_Adi} / {fmt_money(r.Toplam_Tutar)}" for r in orders.itertuples()]
        selected = st.selectbox("Sipariş", order_options)
        order_no = selected.split(" - ", 1)[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            pay_date = st.date_input("Tarih", value=date.today())
        with c2:
            amount = st.number_input("Tutar", min_value=0.0, step=100.0, format="%.2f")
        with c3:
            pay_type = st.selectbox("Ödeme türü", PAYMENT_TYPES)
        note = st.text_area("Not")
        submitted = st.form_submit_button("Ödemeyi kaydet", use_container_width=True)
    if submitted:
        if amount <= 0:
            st.error("Tutar 0'dan büyük olmalı.")
        else:
            row = {
                "Odeme_ID": next_id(payments, "O", "Odeme_ID"),
                "Siparis_No": order_no,
                "Tarih": pay_date.strftime("%Y-%m-%d"),
                "Tutar": amount,
                "Odeme_Turu": pay_type,
                "Not": note,
                "Kayit_Tarihi": now_str(),
            }
            try:
                append_row("Odemeler", row)
                # Update paid amount and payment status on order.
                all_payments = pd.concat([payments, pd.DataFrame([row])], ignore_index=True)
                total_paid = all_payments[all_payments["Siparis_No"] == order_no]["Tutar"].apply(money_to_float).sum()
                idx = orders[orders["Siparis_No"] == order_no].index
                order_total = money_to_float(orders.loc[idx[0], "Toplam_Tutar"])
                new_status = "Ödendi" if total_paid >= order_total and order_total > 0 else "Kısmi Ödendi"
                orders.loc[idx, ["Odenen_Tutar", "Odeme_Durumu"]] = [total_paid, new_status]
                rewrite_sheet("Siparisler", orders)
                st.success("Ödeme kaydedildi.")
                st.rerun()
            except Exception as e:
                st.error(api_error_message(e))

    st.markdown("## Kayıtlı Ödemeler")
    view = payments.copy()
    if not view.empty:
        view["Tutar"] = view["Tutar"].apply(fmt_money)
    show_df(view)

    st.markdown("## Hatalı Ödeme Sil")
    if payments.empty:
        st.info("Silinecek ödeme yok.")
        return
    options = [f"{r.Odeme_ID} - {r.Siparis_No} / {fmt_money(r.Tutar)} / {r.Tarih}" for r in payments.itertuples()]
    selected = st.selectbox("Ödeme seç", options)
    payment_id = selected.split(" - ", 1)[0]
    if st.checkbox("Bu ödeme kaydını silmek istiyorum") and st.button("Ödemeyi sil", use_container_width=True):
        try:
            order_no = payments[payments["Odeme_ID"] == payment_id].iloc[0]["Siparis_No"]
            payments = payments[payments["Odeme_ID"] != payment_id]
            rewrite_sheet("Odemeler", payments)
            # Recalculate order paid amount.
            total_paid = payments[payments["Siparis_No"] == order_no]["Tutar"].apply(money_to_float).sum() if not payments.empty else 0
            idx = orders[orders["Siparis_No"] == order_no].index
            if len(idx) > 0:
                order_total = money_to_float(orders.loc[idx[0], "Toplam_Tutar"])
                if total_paid <= 0:
                    new_status = "Bekliyor"
                elif total_paid >= order_total:
                    new_status = "Ödendi"
                else:
                    new_status = "Kısmi Ödendi"
                orders.loc[idx, ["Odenen_Tutar", "Odeme_Durumu"]] = [total_paid, new_status]
                rewrite_sheet("Siparisler", orders)
            st.success("Ödeme silindi.")
            st.rerun()
        except Exception as e:
            st.error(api_error_message(e))


def reports_page(data: Dict[str, pd.DataFrame]) -> None:
    orders = data["Siparisler"].copy()
    items = data["Siparis_Kalemleri"].copy()
    payments = data["Odemeler"].copy()
    st.markdown("# Raporlar")
    st.caption("Firma, ürün, ciro ve tahsilat raporları")

    if orders.empty:
        st.info("Rapor için henüz sipariş yok.")
    else:
        active = orders[~orders["Durum"].astype(str).str.lower().eq("iptal")].copy()
        c1, c2, c3 = st.columns(3)
        c1.markdown(metric_card("Toplam Ciro", fmt_money(active["Toplam_Tutar"].sum()), "İptal hariç"), unsafe_allow_html=True)
        c2.markdown(metric_card("Tahsilat", fmt_money(payments["Tutar"].sum() if not payments.empty else 0), "Ödeme kayıtları"), unsafe_allow_html=True)
        c3.markdown(metric_card("Açık Tutar", fmt_money(max(active["Toplam_Tutar"].sum() - (payments["Tutar"].sum() if not payments.empty else 0), 0)), "Bekleyen"), unsafe_allow_html=True)

        st.markdown("## Firma Bazlı Satış")
        firm_report = active.groupby("Firma_Adi", dropna=False).agg(Siparis_Adedi=("Siparis_No", "count"), Toplam_Ciro=("Toplam_Tutar", "sum")).reset_index()
        show_df(firm_report.assign(Toplam_Ciro=firm_report["Toplam_Ciro"].apply(fmt_money)))
        if not firm_report.empty:
            st.bar_chart(firm_report.set_index("Firma_Adi")[["Toplam_Ciro"]], use_container_width=True)

        st.markdown("## Ürün Bazlı Satış")
        if not items.empty:
            product_report = items.groupby("Urun_Adi", dropna=False).agg(Toplam_Adet=("Adet", "sum"), Toplam_Tutar=("Satir_Toplam", "sum")).reset_index()
            show_df(product_report.assign(Toplam_Tutar=product_report["Toplam_Tutar"].apply(fmt_money)))
            if not product_report.empty:
                st.bar_chart(product_report.set_index("Urun_Adi")[["Toplam_Adet"]], use_container_width=True)
        else:
            st.info("Ürün kalemi yok.")

    st.markdown("## Excel Dışa Aktar")
    excel_bytes = to_excel_bytes({
        "Siparisler": data["Siparisler"],
        "Siparis_Kalemleri": data["Siparis_Kalemleri"],
        "Firmalar": data["Firmalar"],
        "Urunler": data["Urunler"],
        "Odemeler": data["Odemeler"],
    })
    st.download_button("Tüm raporu indir (Excel)", data=excel_bytes, file_name=f"gundays_home_rapor_{today_str()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()


def settings_page(data: Dict[str, pd.DataFrame]) -> None:
    st.markdown("# Yedek / Ayarlar")
    st.caption("Bağlantı kontrolü, tablo onarımı, Excel yedeği ve şifre bilgisi")
    st.markdown("## Google Sheets Bağlantısı")
    st.success("Google Sheets bağlantısı aktif.")
    st.code(f"SPREADSHEET_ID = {get_spreadsheet_id()}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Verileri yenile", use_container_width=True):
            clear_data_cache()
            st.success("Önbellek temizlendi. Sayfa yenileniyor.")
            st.rerun()
    with c2:
        if st.button("Tabloları onar ve temizle", use_container_width=True):
            try:
                repair_all_sheets(data)
                st.success("Tablolar canonical başlıklarla onarıldı, boş/header satırları temizlendi.")
                st.rerun()
            except Exception as e:
                st.error(api_error_message(e))

    st.warning("Onarım butonunu sürekli basmayın. Google Sheets kotası dolarsa 1-2 dakika bekleyin.")

    st.markdown("## Excel Yedeği İndir")
    excel_bytes = to_excel_bytes(data)
    st.download_button("Tüm verileri indir (Excel)", data=excel_bytes, file_name=f"gundays_home_yedek_{today_str()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown("## Şifre")
    st.info("Kalıcı şifre değişimi için Streamlit > Manage app > Settings > Secrets alanına APP_USER ve APP_PASSWORD ekleyin/değiştirin.")
    st.code('APP_USER = "admin"\nAPP_PASSWORD = "YeniGucluSifre"')

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📦", layout="wide")
    inject_css()

    if not st.session_state.get("logged_in"):
        login_page()
        return

    with st.sidebar:
        st.markdown("## Günday's Home")
        st.caption(f"Kullanıcı: {st.session_state.get('username', 'admin')} / Admin")
        page = st.radio(
            "Menü",
            ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Ödemeler", "Raporlar", "Yedek / Ayarlar"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Çıkış yap", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    try:
        data = load_data()
    except Exception as e:
        st.error("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
        st.error(api_error_message(e))
        st.info("Özellikle 429 kota hatası varsa 1-2 dakika bekleyin. Bağlantı aktifse sürekli reboot yapmayın; kota tekrar dolar.")
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
