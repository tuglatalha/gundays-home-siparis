from __future__ import annotations

# TEK DOSYA SÜRÜMÜ
# Bu dosya Streamlit Cloud'da "Main file path = streamlit_app.py" olarak çalışır.
# src/ klasörü olmasa bile uygulama açılır.

import datetime as dt
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

DEFAULT_SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAMES = {
    "dashboard": "Dashboard",
    "firmalar": "Firmalar",
    "urunler": "Urunler",
    "siparisler": "Siparisler",
    "kalemler": "Siparis_Kalemleri",
    "odemeler": "Odemeler",
    "listeler": "Listeler",
    "kullanim": "Kullanim",
    "kullanicilar": "Kullanicilar",
}

SCHEMAS: Dict[str, List[str]] = {
    "Firmalar": [
        "firma_id", "firma_adi", "sube", "yetkili_kisi", "telefon", "adres",
        "vergi_dairesi", "vkn_tckn", "not", "durum", "eklenme_tarihi",
    ],
    "Urunler": [
        "urun_id", "kategori", "urun_adi", "model", "renk", "birim",
        "varsayilan_fiyat", "stok", "durum", "not",
    ],
    "Siparisler": [
        "siparis_id", "siparis_tarihi", "teslim_tarihi", "firma_id", "firma_adi", "sube",
        "siparis_durumu", "odeme_durumu", "sevkiyat_tipi", "kargo_firma", "takip_no",
        "toplam_tutar", "not",
    ],
    "Siparis_Kalemleri": [
        "kalem_id", "siparis_id", "urun_id", "urun_adi", "renk", "adet",
        "birim_fiyat", "iskonto_orani", "satir_toplami", "not",
    ],
    "Odemeler": [
        "odeme_id", "siparis_id", "firma_id", "odeme_tarihi", "odeme_tipi",
        "tutar", "aciklama", "kayit_tarihi",
    ],
    "Kullanicilar": ["kullanici", "ad_soyad", "rol", "durum"],
}

# Every value below is normalized before matching. This lets the app work with
# firma_id, Firma_ID, Firma ID, Firma Adı, Firma_Adı, etc.
ALIASES: Dict[str, List[str]] = {
    "firma_id": ["firma_id", "firma id", "firma kodu", "firma_no", "cari_id"],
    "firma_adi": ["firma_adi", "firma adı", "firma adi", "cari", "cari_adi", "müşteri", "musteri", "bayi", "firma"],
    "sube": ["sube", "şube", "magaza", "mağaza", "depo"],
    "yetkili_kisi": ["yetkili_kisi", "yetkili kişi", "yetkili", "ilgili"],
    "telefon": ["telefon", "tel", "gsm", "cep"],
    "adres": ["adres"],
    "vergi_dairesi": ["vergi_dairesi", "vergi dairesi", "vd"],
    "vkn_tckn": ["vkn_tckn", "vkn", "tckn", "vergi no", "vergi_no"],
    "not": ["not", "notlar", "açıklama", "aciklama"],
    "durum": ["durum", "aktif", "statu", "statü"],
    "eklenme_tarihi": ["eklenme_tarihi", "eklenme tarihi", "kayıt tarihi", "kayit_tarihi", "kayit zamani"],

    "urun_id": ["urun_id", "ürün_id", "urun id", "ürün id", "stok kodu", "sku"],
    "kategori": ["kategori", "ürün grubu", "urun grubu"],
    "urun_adi": ["urun_adi", "ürün_adı", "urun adi", "ürün adı", "ürün", "urun", "cinsi"],
    "model": ["model"],
    "renk": ["renk", "rengi"],
    "birim": ["birim"],
    "varsayilan_fiyat": ["varsayilan_fiyat", "varsayılan fiyat", "varsayilan fiyat", "birim fiyat", "birim_fiyat", "fiyat"],
    "stok": ["stok", "stok_adedi", "stok adedi"],

    "siparis_id": ["siparis_id", "sipariş_id", "siparis id", "sipariş id", "order id", "sipariş no", "siparis no"],
    "siparis_tarihi": ["siparis_tarihi", "sipariş_tarihi", "siparis tarihi", "sipariş tarihi", "tarih"],
    "teslim_tarihi": ["teslim_tarihi", "teslim tarihi", "termin", "vade"],
    "siparis_durumu": ["siparis_durumu", "sipariş_durumu", "sipariş durumu", "siparis durumu", "durum"],
    "odeme_durumu": ["odeme_durumu", "ödeme_durumu", "ödeme durumu", "odeme durumu"],
    "sevkiyat_tipi": ["sevkiyat_tipi", "sevkiyat tipi", "teslimat tipi"],
    "kargo_firma": ["kargo_firma", "kargo firma", "kargo", "nakliye"],
    "takip_no": ["takip_no", "takip no", "kargo takip", "takip numarası"],
    "toplam_tutar": ["toplam_tutar", "toplam tutar", "ciro", "tutar", "genel toplam"],

    "kalem_id": ["kalem_id", "kalem id", "satir_id", "satır_id"],
    "adet": ["adet", "miktar"],
    "birim_fiyat": ["birim_fiyat", "birim fiyat", "fiyat"],
    "iskonto_orani": ["iskonto_orani", "iskonto oranı", "iskonto", "indirim"],
    "satir_toplami": ["satir_toplami", "satır_toplamı", "satır toplamı", "satir toplami", "tutar"],

    "odeme_id": ["odeme_id", "ödeme_id", "odeme id", "ödeme id"],
    "odeme_tarihi": ["odeme_tarihi", "ödeme_tarihi", "ödeme tarihi", "odeme tarihi", "tarih"],
    "odeme_tipi": ["odeme_tipi", "ödeme_tipi", "ödeme tipi", "odeme tipi", "ödeme türü", "odeme turu"],
    "tutar": ["tutar", "ödeme tutarı", "odeme tutari", "tahsilat", "tahsilat_tutari"],
    "aciklama": ["aciklama", "açıklama", "not"],
    "kayit_tarihi": ["kayit_tarihi", "kayıt_tarihi", "kayıt tarihi", "kayit tarihi", "kayıt zamanı"],

    "kullanici": ["kullanici", "kullanıcı", "user", "username"],
    "ad_soyad": ["ad_soyad", "ad soyad", "isim"],
    "rol": ["rol", "yetki"],
}

NUMERIC_COLS = {
    "adet", "birim_fiyat", "iskonto_orani", "satir_toplami", "varsayilan_fiyat", "stok",
    "toplam_tutar", "tutar",
}
DATE_COLS = {"siparis_tarihi", "teslim_tarihi", "odeme_tarihi", "kayit_tarihi", "eklenme_tarihi"}

DEFAULT_LISTS = {
    "siparis_durumlari": ["Sipariş Alındı", "Üretimde", "Hazır", "Sevk Edildi", "Teslim Edildi", "İptal"],
    "odeme_durumlari": ["Bekliyor", "Kısmi Ödendi", "Ödendi", "İptal"],
    "sevkiyat_tipleri": ["Sevkiyat Yok", "Araçla Teslim", "Kargo", "Müşteri Teslim Alacak"],
    "odeme_tipleri": ["Nakit", "Havale/EFT", "Kart", "Çek/Senet", "Pazaryeri", "Diğer"],
    "durumlar": ["Aktif", "Pasif"],
    "renkler": ["Naturel", "Ceviz", "Siyah", "Lake Beyaz", "Diğer"],
}

@dataclass
class SheetMeta:
    sheet_name: str
    header_row_index: int  # 1-based Google Sheets row index
    headers: List[str]
    canonical_to_header: Dict[str, str]
    header_to_canonical: Dict[str, str]


def normalize_key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def alias_set(canonical: str) -> set[str]:
    aliases = ALIASES.get(canonical, [canonical])
    return {normalize_key(x) for x in aliases + [canonical]}


def canonical_from_header(header: str, expected: Iterable[str]) -> Optional[str]:
    n = normalize_key(header)
    if not n:
        return None
    for canonical in expected:
        if n in alias_set(canonical):
            return canonical
    # Last-resort exact canonical normalized match.
    for canonical in expected:
        if n == normalize_key(canonical):
            return canonical
    return None


def safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace("₺", "").replace("TL", "").replace("tl", "").strip()
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    return text


def date_to_iso(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return ""
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    raw = str(value).strip()
    # Google/Excel serial date. Google Sheets exports dates as serials via API sometimes.
    if re.fullmatch(r"\d+(\.0)?", raw):
        number = int(float(raw))
        if 25000 <= number <= 70000:
            return (dt.date(1899, 12, 30) + dt.timedelta(days=number)).isoformat()
    parsed = pd.to_datetime(raw, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return raw
    return parsed.date().isoformat()


def money(value: Any) -> str:
    return f"{safe_float(value):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def get_spreadsheet_id() -> str:
    try:
        return st.secrets.get("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)
    except Exception:
        return os.getenv("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    try:
        if "gcp_service_account" in st.secrets:
            service_account_info = dict(st.secrets["gcp_service_account"])
        elif "GOOGLE_SERVICE_ACCOUNT_JSON" in os.environ:
            import json
            service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        else:
            raise RuntimeError(
                "Google servis hesabı bulunamadı. Streamlit secrets içine gcp_service_account ekle."
            )
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_key(get_spreadsheet_id())
    except Exception as exc:
        raise RuntimeError(f"Google Sheet bağlantısı kurulamadı: {exc}") from exc


def worksheet(sheet_name: str):
    sh = get_spreadsheet()
    return sh.worksheet(sheet_name)


def raw_values(sheet_name: str) -> List[List[str]]:
    return worksheet(sheet_name).get_all_values()


def _score_header(row: List[str], expected: List[str]) -> int:
    score = 0
    seen: set[str] = set()
    for cell in row:
        canonical = canonical_from_header(cell, expected)
        if canonical and canonical not in seen:
            score += 1
            seen.add(canonical)
    return score


def get_sheet_meta(sheet_name: str) -> SheetMeta:
    values = raw_values(sheet_name)
    expected = SCHEMAS.get(sheet_name, [])
    if not values:
        raise ValueError(f"{sheet_name} sayfası boş görünüyor.")

    best_idx = 0
    best_score = -1
    scan_limit = min(10, len(values))
    for idx in range(scan_limit):
        score = _score_header(values[idx], expected)
        if score > best_score:
            best_idx = idx
            best_score = score

    # If no expected schema exists, assume first non-empty row is the header.
    if best_score <= 0:
        for idx, row in enumerate(values[:scan_limit]):
            if any(clean_text(x) for x in row):
                best_idx = idx
                break

    raw_headers = [clean_text(h) for h in values[best_idx]]
    headers: List[str] = []
    used: Dict[str, int] = {}
    for i, h in enumerate(raw_headers):
        name = h or f"column_{i+1}"
        if name in used:
            used[name] += 1
            name = f"{name}_{used[name]}"
        else:
            used[name] = 1
        headers.append(name)

    canonical_to_header: Dict[str, str] = {}
    header_to_canonical: Dict[str, str] = {}
    for header in headers:
        canonical = canonical_from_header(header, expected)
        if canonical and canonical not in canonical_to_header:
            canonical_to_header[canonical] = header
            header_to_canonical[header] = canonical

    return SheetMeta(
        sheet_name=sheet_name,
        header_row_index=best_idx + 1,
        headers=headers,
        canonical_to_header=canonical_to_header,
        header_to_canonical=header_to_canonical,
    )


@st.cache_data(ttl=20, show_spinner=False)
def read_df(sheet_name: str) -> pd.DataFrame:
    values = raw_values(sheet_name)
    if not values:
        return pd.DataFrame()
    meta = get_sheet_meta(sheet_name)
    start = meta.header_row_index
    rows = values[start:]
    width = len(meta.headers)
    normalized_rows = []
    for row in rows:
        r = row[:width] + [""] * max(0, width - len(row))
        if any(clean_text(x) for x in r):
            normalized_rows.append(r)
    df = pd.DataFrame(normalized_rows, columns=meta.headers)

    rename_map = {
        header: canonical for header, canonical in meta.header_to_canonical.items()
    }
    df = df.rename(columns=rename_map)

    for col in DATE_COLS.intersection(df.columns):
        df[col] = df[col].map(date_to_iso)
    for col in NUMERIC_COLS.intersection(df.columns):
        df[col] = df[col].map(safe_float)

    return drop_template_rows(sheet_name, df)


def read_df_no_filter(sheet_name: str) -> pd.DataFrame:
    values = raw_values(sheet_name)
    if not values:
        return pd.DataFrame()
    meta = get_sheet_meta(sheet_name)
    start = meta.header_row_index
    rows = values[start:]
    width = len(meta.headers)
    normalized_rows = []
    for row in rows:
        r = row[:width] + [""] * max(0, width - len(row))
        if any(clean_text(x) for x in r):
            normalized_rows.append(r)
    df = pd.DataFrame(normalized_rows, columns=meta.headers)
    return df.rename(columns={h: c for h, c in meta.header_to_canonical.items()})


def drop_template_rows(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()

    def has_text(row: pd.Series, cols: List[str]) -> bool:
        return any(clean_text(row.get(c, "")) for c in cols)

    if sheet_name == "Firmalar":
        mask = work.apply(lambda r: has_text(r, ["firma_adi", "sube", "telefon", "adres"]), axis=1)
        return work[mask].reset_index(drop=True)
    if sheet_name == "Urunler":
        mask = work.apply(lambda r: has_text(r, ["urun_adi", "kategori", "model", "renk"]), axis=1)
        return work[mask].reset_index(drop=True)
    if sheet_name == "Siparisler":
        mask = work.apply(lambda r: has_text(r, ["firma_adi", "firma_id", "siparis_tarihi", "teslim_tarihi"]), axis=1)
        return work[mask].reset_index(drop=True)
    if sheet_name == "Siparis_Kalemleri":
        mask = work.apply(lambda r: has_text(r, ["siparis_id", "urun_adi", "urun_id", "renk"]) and safe_float(r.get("adet", 0)) > 0, axis=1)
        return work[mask].reset_index(drop=True)
    if sheet_name == "Odemeler":
        mask = work.apply(lambda r: has_text(r, ["siparis_id", "firma_id", "odeme_tarihi"]) and safe_float(r.get("tutar", 0)) > 0, axis=1)
        return work[mask].reset_index(drop=True)
    return work.reset_index(drop=True)


def clear_cache() -> None:
    st.cache_data.clear()


def next_id(sheet_name: str, id_col: str, prefix: str, width: int = 4, year: bool = False) -> str:
    df = read_df_no_filter(sheet_name)
    existing = []
    if id_col in df.columns:
        existing = [clean_text(x) for x in df[id_col].tolist()]
    current_year = dt.date.today().year
    max_no = 0
    if year:
        regex = re.compile(rf"^{re.escape(prefix)}-{current_year}-(\d+)$", re.IGNORECASE)
    else:
        regex = re.compile(rf"^{re.escape(prefix)}-(\d+)$", re.IGNORECASE)
    for value in existing:
        match = regex.match(value)
        if match:
            max_no = max(max_no, int(match.group(1)))
    if year:
        return f"{prefix}-{current_year}-{max_no + 1:0{width}d}"
    return f"{prefix}-{max_no + 1:0{width}d}"


def row_for_append(sheet_name: str, record: Dict[str, Any]) -> List[Any]:
    meta = get_sheet_meta(sheet_name)
    row = []
    expected = SCHEMAS.get(sheet_name, [])
    for header in meta.headers:
        canonical = meta.header_to_canonical.get(header) or canonical_from_header(header, expected)
        value = record.get(canonical or header, "")
        if isinstance(value, (dt.date, dt.datetime)):
            value = date_to_iso(value)
        row.append(value)
    return row


def append_record(sheet_name: str, record: Dict[str, Any]) -> None:
    ws = worksheet(sheet_name)
    row = row_for_append(sheet_name, record)
    ws.append_row(row, value_input_option="USER_ENTERED")
    clear_cache()


def append_records(sheet_name: str, records: List[Dict[str, Any]]) -> None:
    if not records:
        return
    ws = worksheet(sheet_name)
    rows = [row_for_append(sheet_name, r) for r in records]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    clear_cache()


def find_google_row(sheet_name: str, key_col: str, key_value: str) -> Optional[int]:
    values = raw_values(sheet_name)
    meta = get_sheet_meta(sheet_name)
    header = meta.canonical_to_header.get(key_col)
    if not header:
        return None
    try:
        col_idx = meta.headers.index(header)
    except ValueError:
        return None
    for zero_idx, row in enumerate(values[meta.header_row_index:], start=meta.header_row_index + 1):
        current = clean_text(row[col_idx] if col_idx < len(row) else "")
        if current == key_value:
            return zero_idx
    return None


def update_record(sheet_name: str, key_col: str, key_value: str, updates: Dict[str, Any]) -> bool:
    ws = worksheet(sheet_name)
    meta = get_sheet_meta(sheet_name)
    row_no = find_google_row(sheet_name, key_col, key_value)
    if row_no is None:
        return False
    batch = []
    for canonical, value in updates.items():
        header = meta.canonical_to_header.get(canonical)
        if not header:
            continue
        col_no = meta.headers.index(header) + 1
        a1 = gspread.utils.rowcol_to_a1(row_no, col_no)
        if isinstance(value, (dt.date, dt.datetime)):
            value = date_to_iso(value)
        batch.append({"range": a1, "values": [[value]]})
    if batch:
        ws.batch_update(batch, value_input_option="USER_ENTERED")
        clear_cache()
        return True
    return False


def option_label(row: pd.Series, fields: List[str], fallback: str = "") -> str:
    pieces = [clean_text(row.get(f, "")) for f in fields]
    pieces = [p for p in pieces if p]
    return " | ".join(pieces) or fallback


def active_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "durum" not in df.columns:
        return df
    status = df["durum"].astype(str).map(normalize_key)
    return df[(status == "aktif") | (status == "")].reset_index(drop=True)


def build_order_totals(orders: pd.DataFrame, items: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    orders = orders.copy()
    if orders.empty:
        return orders
    if "siparis_id" not in orders.columns:
        return orders

    if not items.empty and "siparis_id" in items.columns:
        items = items.copy()
        if "satir_toplami" not in items.columns:
            items["satir_toplami"] = 0.0
        item_totals = items.groupby("siparis_id", dropna=False)["satir_toplami"].sum().rename("kalem_toplami")
        item_counts = items.groupby("siparis_id", dropna=False)["kalem_id"].count().rename("kalem_sayisi") if "kalem_id" in items.columns else None
        orders = orders.merge(item_totals, on="siparis_id", how="left")
        if item_counts is not None:
            orders = orders.merge(item_counts, on="siparis_id", how="left")
    else:
        orders["kalem_toplami"] = 0.0
        orders["kalem_sayisi"] = 0

    if not payments.empty and "siparis_id" in payments.columns:
        paid = payments.groupby("siparis_id", dropna=False)["tutar"].sum().rename("odenen_tutar")
        orders = orders.merge(paid, on="siparis_id", how="left")
    else:
        orders["odenen_tutar"] = 0.0

    orders["toplam_tutar"] = orders.get("toplam_tutar", 0).map(safe_float)
    orders["kalem_toplami"] = orders["kalem_toplami"].fillna(0).map(safe_float)
    orders["odenen_tutar"] = orders["odenen_tutar"].fillna(0).map(safe_float)
    orders["hesaplanan_tutar"] = orders.apply(
        lambda r: r["kalem_toplami"] if r["kalem_toplami"] > 0 else r["toplam_tutar"], axis=1
    )
    orders["kalan_tutar"] = orders["hesaplanan_tutar"] - orders["odenen_tutar"]
    return orders


def recompute_order_payment_status(order_id: str) -> None:
    orders = read_df("Siparisler")
    payments = read_df("Odemeler")
    items = read_df("Siparis_Kalemleri")
    full = build_order_totals(orders, items, payments)
    if full.empty or "siparis_id" not in full.columns:
        return
    row = full[full["siparis_id"] == order_id]
    if row.empty:
        return
    total = safe_float(row.iloc[0].get("hesaplanan_tutar", 0))
    paid = safe_float(row.iloc[0].get("odenen_tutar", 0))
    if total <= 0:
        status = "Bekliyor"
    elif paid >= total:
        status = "Ödendi"
    elif paid > 0:
        status = "Kısmi Ödendi"
    else:
        status = "Bekliyor"
    update_record("Siparisler", "siparis_id", order_id, {"odeme_durumu": status})


def audit_schema() -> pd.DataFrame:
    rows = []
    try:
        sh = get_spreadsheet()
        existing_titles = [w.title for w in sh.worksheets()]
    except Exception as exc:
        return pd.DataFrame([{"Sayfa": "Bağlantı", "Durum": "Hata", "Detay": str(exc)}])

    for sheet_name, expected in SCHEMAS.items():
        if sheet_name not in existing_titles:
            rows.append({"Sayfa": sheet_name, "Durum": "Eksik", "Detay": "Sayfa bulunamadı"})
            continue
        try:
            meta = get_sheet_meta(sheet_name)
            missing = [c for c in expected if c not in meta.canonical_to_header]
            rows.append({
                "Sayfa": sheet_name,
                "Durum": "Tamam" if not missing else "Kontrol",
                "Başlık Satırı": meta.header_row_index,
                "Eşleşen Kolon": len(meta.canonical_to_header),
                "Eksik/Kontrol Edilecek": ", ".join(missing),
            })
        except Exception as exc:
            rows.append({"Sayfa": sheet_name, "Durum": "Hata", "Detay": str(exc)})
    return pd.DataFrame(rows)


# =========================
# STREAMLIT ARAYÜZÜ
# =========================

st.set_page_config(
    page_title="Gündays Home Sipariş Takip",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.3rem; padding-bottom: 2.2rem;}
    div[data-testid="stMetricValue"] {font-size: 1.55rem;}
    .status-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 16px;
        padding: 14px 16px;
        background: rgba(128,128,128,.06);
    }
    .small-muted {color: #8a8a8a; font-size: .88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_all():
    firmalar = read_df("Firmalar")
    urunler = read_df("Urunler")
    siparisler = read_df("Siparisler")
    kalemler = read_df("Siparis_Kalemleri")
    odemeler = read_df("Odemeler")
    siparisler_full = build_order_totals(siparisler, kalemler, odemeler)
    return firmalar, urunler, siparisler_full, kalemler, odemeler


def show_connection_error(exc: Exception):
    st.error("Google Sheets bağlantısı kurulamadı.")
    st.code(str(exc))
    st.info(
        "Streamlit Cloud > App > Settings > Secrets bölümüne servis hesabı bilgilerini ekle ve "
        "servis hesabı e-postasını Google Sheet üzerinde Düzenleyici yap."
    )


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in ["toplam_tutar", "kalem_toplami", "hesaplanan_tutar", "odenen_tutar", "kalan_tutar", "satir_toplami", "birim_fiyat", "tutar", "varsayilan_fiyat"]:
        if col in out.columns:
            out[col] = out[col].map(money)
    return out


def status_badge(status: str) -> str:
    return clean_text(status) or "-"


def dashboard_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("📦 Gündays Home Sipariş Takip")
    st.caption("Veriler Google Sheets üzerinden okunur ve yeni kayıtlar doğrudan aynı dosyaya yazılır.")

    total_sales = safe_float(siparisler["hesaplanan_tutar"].sum()) if "hesaplanan_tutar" in siparisler.columns else 0
    total_paid = safe_float(siparisler["odenen_tutar"].sum()) if "odenen_tutar" in siparisler.columns else 0
    open_balance = total_sales - total_paid
    order_count = len(siparisler)
    active_company_count = len(active_only(firmalar))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Ciro", money(total_sales))
    c2.metric("Tahsilat", money(total_paid))
    c3.metric("Açık Bakiye", money(open_balance))
    c4.metric("Sipariş", f"{order_count}")
    c5.metric("Aktif Firma", f"{active_company_count}")

    st.divider()

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Sipariş Durumu")
        if not siparisler.empty and "siparis_durumu" in siparisler.columns:
            status_df = siparisler.groupby("siparis_durumu", dropna=False).size().reset_index(name="Adet")
            status_df["siparis_durumu"] = status_df["siparis_durumu"].replace("", "Belirsiz")
            chart_df = status_df.set_index("siparis_durumu")[["Adet"]]
            st.bar_chart(chart_df, use_container_width=True, height=340)
        else:
            st.info("Henüz sipariş bulunmuyor.")

    with right:
        st.subheader("Ödeme Durumu")
        if not siparisler.empty and "odeme_durumu" in siparisler.columns:
            pay_df = siparisler.groupby("odeme_durumu", dropna=False).size().reset_index(name="Adet")
            pay_df["odeme_durumu"] = pay_df["odeme_durumu"].replace("", "Belirsiz")
            chart_df = pay_df.set_index("odeme_durumu")[["Adet"]]
            st.bar_chart(chart_df, use_container_width=True, height=340)
        else:
            st.info("Henüz ödeme verisi bulunmuyor.")

    st.subheader("Son Siparişler")
    if siparisler.empty:
        st.warning("Siparişler sayfasında gösterilecek dolu kayıt yok.")
    else:
        cols = [c for c in [
            "siparis_id", "siparis_tarihi", "firma_adi", "sube", "siparis_durumu",
            "odeme_durumu", "hesaplanan_tutar", "odenen_tutar", "kalan_tutar", "not"
        ] if c in siparisler.columns]
        st.dataframe(format_table(siparisler[cols].tail(30).sort_index(ascending=False)), use_container_width=True, hide_index=True)


def new_order_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("➕ Yeni Sipariş")
    active_firms = active_only(firmalar)
    active_products = active_only(urunler)

    if active_firms.empty:
        st.error("Aktif firma bulunamadı. Önce Firmalar sayfasından firma ekle.")
        return
    if active_products.empty:
        st.error("Aktif ürün bulunamadı. Önce Ürünler sayfasından ürün ekle.")
        return

    firm_options: Dict[str, pd.Series] = {}
    for _, row in active_firms.iterrows():
        label = option_label(row, ["firma_adi", "sube", "firma_id"], "Firma")
        firm_options[label] = row

    product_options: Dict[str, pd.Series] = {}
    for _, row in active_products.iterrows():
        fiyat = money(row.get("varsayilan_fiyat", 0))
        label = f"{option_label(row, ['urun_adi', 'renk', 'urun_id'], 'Ürün')} — {fiyat}"
        product_options[label] = row

    with st.form("new_order_form", clear_on_submit=False):
        st.subheader("Sipariş Bilgileri")
        c1, c2, c3 = st.columns(3)
        firma_label = c1.selectbox("Firma / Şube", list(firm_options.keys()))
        siparis_tarihi = c2.date_input("Sipariş Tarihi", value=dt.date.today())
        teslim_tarihi = c3.date_input("Teslim Tarihi", value=dt.date.today() + dt.timedelta(days=7))

        c4, c5, c6 = st.columns(3)
        siparis_durumu = c4.selectbox("Sipariş Durumu", DEFAULT_LISTS["siparis_durumlari"], index=0)
        odeme_durumu = c5.selectbox("Ödeme Durumu", DEFAULT_LISTS["odeme_durumlari"], index=0)
        sevkiyat_tipi = c6.selectbox("Sevkiyat Tipi", DEFAULT_LISTS["sevkiyat_tipleri"], index=0)

        c7, c8 = st.columns(2)
        kargo_firma = c7.text_input("Kargo / Nakliye Firması")
        takip_no = c8.text_input("Takip No")
        siparis_notu = st.text_area("Sipariş Notu", height=80)

        st.subheader("Ürün Kalemleri")
        line_count = st.number_input("Kalem sayısı", min_value=1, max_value=20, value=1, step=1)
        line_items: List[Dict[str, Any]] = []
        estimated_total = 0.0

        for i in range(int(line_count)):
            st.markdown(f"**{i + 1}. Kalem**")
            p1, p2, p3, p4, p5 = st.columns([2.2, 1, .8, 1, 1])
            product_label = p1.selectbox("Ürün", list(product_options.keys()), key=f"product_{i}")
            product = product_options[product_label]
            renk_default = clean_text(product.get("renk", "")) or DEFAULT_LISTS["renkler"][0]
            renk = p2.text_input("Renk", value=renk_default, key=f"renk_{i}")
            adet = p3.number_input("Adet", min_value=1, value=1, step=1, key=f"adet_{i}")
            birim_fiyat = p4.number_input("Birim Fiyat", min_value=0.0, value=safe_float(product.get("varsayilan_fiyat", 0)), step=50.0, key=f"fiyat_{i}")
            iskonto = p5.number_input("İskonto %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"iskonto_{i}")
            line_note = st.text_input("Kalem Notu", key=f"line_note_{i}")
            satir_toplami = float(adet) * float(birim_fiyat) * (1 - float(iskonto) / 100)
            estimated_total += satir_toplami
            line_items.append({
                "urun_id": clean_text(product.get("urun_id", "")),
                "urun_adi": clean_text(product.get("urun_adi", "")),
                "renk": renk,
                "adet": int(adet),
                "birim_fiyat": float(birim_fiyat),
                "iskonto_orani": float(iskonto),
                "satir_toplami": round(satir_toplami, 2),
                "not": line_note,
            })
            st.caption(f"Satır toplamı: {money(satir_toplami)}")

        st.info(f"Hesaplanan sipariş toplamı: **{money(estimated_total)}**")
        submitted = st.form_submit_button("Siparişi Kaydet", type="primary", use_container_width=True)

    if submitted:
        selected_firm = firm_options[firma_label]
        order_id = next_id("Siparisler", "siparis_id", "GH", width=4, year=True)
        order_record = {
            "siparis_id": order_id,
            "siparis_tarihi": siparis_tarihi.isoformat(),
            "teslim_tarihi": teslim_tarihi.isoformat(),
            "firma_id": clean_text(selected_firm.get("firma_id", "")),
            "firma_adi": clean_text(selected_firm.get("firma_adi", "")),
            "sube": clean_text(selected_firm.get("sube", "")),
            "siparis_durumu": siparis_durumu,
            "odeme_durumu": odeme_durumu,
            "sevkiyat_tipi": sevkiyat_tipi,
            "kargo_firma": kargo_firma,
            "takip_no": takip_no,
            "toplam_tutar": round(estimated_total, 2),
            "not": siparis_notu,
        }
        item_records = []
        first_item_id = next_id("Siparis_Kalemleri", "kalem_id", "K", width=4)
        item_base, item_start = first_item_id.rsplit("-", 1)
        for idx, item in enumerate(line_items):
            item = dict(item)
            item["kalem_id"] = f"{item_base}-{int(item_start) + idx:04d}"
            item["siparis_id"] = order_id
            item_records.append(item)

        try:
            append_record("Siparisler", order_record)
            append_records("Siparis_Kalemleri", item_records)
            clear_cache()
            st.success(f"Sipariş kaydedildi: {order_id}")
            st.rerun()
        except Exception as exc:
            st.error("Sipariş kaydedilemedi.")
            st.code(str(exc))


def orders_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("📋 Siparişler")
    if siparisler.empty:
        st.warning("Sipariş kaydı bulunamadı.")
        return

    f1, f2, f3 = st.columns(3)
    firma_filter = f1.multiselect("Firma", sorted([x for x in siparisler.get("firma_adi", pd.Series(dtype=str)).dropna().unique() if clean_text(x)]))
    status_filter = f2.multiselect("Sipariş Durumu", sorted([x for x in siparisler.get("siparis_durumu", pd.Series(dtype=str)).dropna().unique() if clean_text(x)]))
    pay_filter = f3.multiselect("Ödeme Durumu", sorted([x for x in siparisler.get("odeme_durumu", pd.Series(dtype=str)).dropna().unique() if clean_text(x)]))

    filtered = siparisler.copy()
    if firma_filter and "firma_adi" in filtered.columns:
        filtered = filtered[filtered["firma_adi"].isin(firma_filter)]
    if status_filter and "siparis_durumu" in filtered.columns:
        filtered = filtered[filtered["siparis_durumu"].isin(status_filter)]
    if pay_filter and "odeme_durumu" in filtered.columns:
        filtered = filtered[filtered["odeme_durumu"].isin(pay_filter)]

    cols = [c for c in [
        "siparis_id", "siparis_tarihi", "teslim_tarihi", "firma_adi", "sube", "siparis_durumu",
        "odeme_durumu", "sevkiyat_tipi", "kargo_firma", "takip_no", "hesaplanan_tutar", "odenen_tutar", "kalan_tutar", "not"
    ] if c in filtered.columns]
    st.dataframe(format_table(filtered[cols]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Sipariş Detayı / Güncelle")
    order_ids = filtered["siparis_id"].dropna().astype(str).tolist()
    selected_id = st.selectbox("Sipariş Seç", order_ids)
    selected_order = siparisler[siparisler["siparis_id"] == selected_id].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", money(selected_order.get("hesaplanan_tutar", 0)))
    c2.metric("Ödenen", money(selected_order.get("odenen_tutar", 0)))
    c3.metric("Kalan", money(selected_order.get("kalan_tutar", 0)))
    c4.metric("Durum", status_badge(selected_order.get("siparis_durumu", "")))

    detail_items = kalemler[kalemler["siparis_id"] == selected_id] if not kalemler.empty and "siparis_id" in kalemler.columns else pd.DataFrame()
    detail_payments = odemeler[odemeler["siparis_id"] == selected_id] if not odemeler.empty and "siparis_id" in odemeler.columns else pd.DataFrame()

    with st.expander("Ürün kalemleri", expanded=True):
        if detail_items.empty:
            st.info("Bu siparişe ait ürün kalemi bulunamadı.")
        else:
            item_cols = [c for c in ["kalem_id", "urun_adi", "renk", "adet", "birim_fiyat", "iskonto_orani", "satir_toplami", "not"] if c in detail_items.columns]
            st.dataframe(format_table(detail_items[item_cols]), use_container_width=True, hide_index=True)

    with st.expander("Ödemeler", expanded=False):
        if detail_payments.empty:
            st.info("Bu siparişe ait ödeme bulunamadı.")
        else:
            pay_cols = [c for c in ["odeme_id", "odeme_tarihi", "odeme_tipi", "tutar", "aciklama"] if c in detail_payments.columns]
            st.dataframe(format_table(detail_payments[pay_cols]), use_container_width=True, hide_index=True)

    with st.form("update_order"):
        u1, u2, u3 = st.columns(3)
        new_status = u1.selectbox(
            "Sipariş Durumu",
            DEFAULT_LISTS["siparis_durumlari"],
            index=DEFAULT_LISTS["siparis_durumlari"].index(clean_text(selected_order.get("siparis_durumu", ""))) if clean_text(selected_order.get("siparis_durumu", "")) in DEFAULT_LISTS["siparis_durumlari"] else 0,
        )
        new_payment_status = u2.selectbox(
            "Ödeme Durumu",
            DEFAULT_LISTS["odeme_durumlari"],
            index=DEFAULT_LISTS["odeme_durumlari"].index(clean_text(selected_order.get("odeme_durumu", ""))) if clean_text(selected_order.get("odeme_durumu", "")) in DEFAULT_LISTS["odeme_durumlari"] else 0,
        )
        new_shipping = u3.selectbox(
            "Sevkiyat Tipi",
            DEFAULT_LISTS["sevkiyat_tipleri"],
            index=DEFAULT_LISTS["sevkiyat_tipleri"].index(clean_text(selected_order.get("sevkiyat_tipi", ""))) if clean_text(selected_order.get("sevkiyat_tipi", "")) in DEFAULT_LISTS["sevkiyat_tipleri"] else 0,
        )
        u4, u5 = st.columns(2)
        new_kargo = u4.text_input("Kargo / Nakliye", value=clean_text(selected_order.get("kargo_firma", "")))
        new_tracking = u5.text_input("Takip No", value=clean_text(selected_order.get("takip_no", "")))
        new_note = st.text_area("Not", value=clean_text(selected_order.get("not", "")))
        save_update = st.form_submit_button("Güncelle", type="primary")

    if save_update:
        ok = update_record("Siparisler", "siparis_id", selected_id, {
            "siparis_durumu": new_status,
            "odeme_durumu": new_payment_status,
            "sevkiyat_tipi": new_shipping,
            "kargo_firma": new_kargo,
            "takip_no": new_tracking,
            "not": new_note,
        })
        if ok:
            st.success("Sipariş güncellendi.")
            st.rerun()
        else:
            st.error("Sipariş satırı bulunamadı veya kolon eşleşmedi.")


def payments_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("💳 Ödemeler")
    if siparisler.empty:
        st.warning("Ödeme girmek için önce sipariş oluştur.")
        return

    order_map = {}
    for _, row in siparisler.iterrows():
        label = f"{row.get('siparis_id', '')} | {row.get('firma_adi', '')} | Kalan: {money(row.get('kalan_tutar', 0))}"
        order_map[label] = row

    with st.form("payment_form"):
        selected = st.selectbox("Sipariş", list(order_map.keys()))
        row = order_map[selected]
        p1, p2, p3 = st.columns(3)
        odeme_tarihi = p1.date_input("Ödeme Tarihi", value=dt.date.today())
        odeme_tipi = p2.selectbox("Ödeme Tipi", DEFAULT_LISTS["odeme_tipleri"])
        tutar = p3.number_input("Tutar", min_value=0.0, value=max(0.0, safe_float(row.get("kalan_tutar", 0))), step=100.0)
        aciklama = st.text_area("Açıklama", height=90)
        submit = st.form_submit_button("Ödemeyi Kaydet", type="primary")

    if submit:
        if tutar <= 0:
            st.error("Ödeme tutarı 0'dan büyük olmalı.")
            return
        record = {
            "odeme_id": next_id("Odemeler", "odeme_id", "O", width=4),
            "siparis_id": clean_text(row.get("siparis_id", "")),
            "firma_id": clean_text(row.get("firma_id", "")),
            "odeme_tarihi": odeme_tarihi.isoformat(),
            "odeme_tipi": odeme_tipi,
            "tutar": round(float(tutar), 2),
            "aciklama": aciklama,
            "kayit_tarihi": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            append_record("Odemeler", record)
            clear_cache()
            recompute_order_payment_status(record["siparis_id"])
            st.success("Ödeme kaydedildi ve sipariş ödeme durumu güncellendi.")
            st.rerun()
        except Exception as exc:
            st.error("Ödeme kaydedilemedi.")
            st.code(str(exc))

    st.subheader("Ödeme Listesi")
    if odemeler.empty:
        st.info("Henüz ödeme kaydı yok.")
    else:
        cols = [c for c in ["odeme_id", "siparis_id", "firma_id", "odeme_tarihi", "odeme_tipi", "tutar", "aciklama", "kayit_tarihi"] if c in odemeler.columns]
        st.dataframe(format_table(odemeler[cols].sort_index(ascending=False)), use_container_width=True, hide_index=True)


def companies_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("🏢 Firmalar")
    with st.expander("Yeni Firma Ekle", expanded=False):
        with st.form("company_form"):
            c1, c2, c3 = st.columns(3)
            firma_adi = c1.text_input("Firma Adı *")
            sube = c2.text_input("Şube / Depo")
            durum = c3.selectbox("Durum", DEFAULT_LISTS["durumlar"])
            c4, c5 = st.columns(2)
            yetkili = c4.text_input("Yetkili Kişi")
            telefon = c5.text_input("Telefon")
            adres = st.text_area("Adres", height=70)
            c6, c7 = st.columns(2)
            vergi_dairesi = c6.text_input("Vergi Dairesi")
            vkn_tckn = c7.text_input("VKN / TCKN")
            note = st.text_area("Not", height=70)
            submit = st.form_submit_button("Firmayı Kaydet", type="primary")

        if submit:
            if not clean_text(firma_adi):
                st.error("Firma adı zorunlu.")
            else:
                record = {
                    "firma_id": next_id("Firmalar", "firma_id", "F", width=4),
                    "firma_adi": firma_adi,
                    "sube": sube,
                    "yetkili_kisi": yetkili,
                    "telefon": telefon,
                    "adres": adres,
                    "vergi_dairesi": vergi_dairesi,
                    "vkn_tckn": vkn_tckn,
                    "not": note,
                    "durum": durum,
                    "eklenme_tarihi": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                try:
                    append_record("Firmalar", record)
                    st.success("Firma kaydedildi.")
                    st.rerun()
                except Exception as exc:
                    st.error("Firma kaydedilemedi.")
                    st.code(str(exc))

    st.subheader("Firma Listesi")
    if firmalar.empty:
        st.info("Firma kaydı bulunamadı.")
    else:
        cols = [c for c in ["firma_id", "firma_adi", "sube", "yetkili_kisi", "telefon", "adres", "vergi_dairesi", "vkn_tckn", "durum", "not", "eklenme_tarihi"] if c in firmalar.columns]
        st.dataframe(firmalar[cols], use_container_width=True, hide_index=True)


def products_page(firmalar, urunler, siparisler, kalemler, odemeler):
    st.title("🪑 Ürünler")
    with st.expander("Yeni Ürün Ekle", expanded=False):
        with st.form("product_form"):
            c1, c2, c3 = st.columns(3)
            kategori = c1.text_input("Kategori")
            urun_adi = c2.text_input("Ürün Adı *")
            model = c3.text_input("Model")
            c4, c5, c6, c7 = st.columns(4)
            renk = c4.text_input("Renk", value="Naturel")
            birim = c5.text_input("Birim", value="Adet")
            varsayilan_fiyat = c6.number_input("Varsayılan Fiyat", min_value=0.0, value=0.0, step=50.0)
            stok = c7.number_input("Stok", min_value=0, value=0, step=1)
            durum = st.selectbox("Durum", DEFAULT_LISTS["durumlar"])
            note = st.text_area("Not", height=70)
            submit = st.form_submit_button("Ürünü Kaydet", type="primary")

        if submit:
            if not clean_text(urun_adi):
                st.error("Ürün adı zorunlu.")
            else:
                record = {
                    "urun_id": next_id("Urunler", "urun_id", "U", width=4),
                    "kategori": kategori,
                    "urun_adi": urun_adi,
                    "model": model,
                    "renk": renk,
                    "birim": birim,
                    "varsayilan_fiyat": float(varsayilan_fiyat),
                    "stok": int(stok),
                    "durum": durum,
                    "not": note,
                }
                try:
                    append_record("Urunler", record)
                    st.success("Ürün kaydedildi.")
                    st.rerun()
                except Exception as exc:
                    st.error("Ürün kaydedilemedi.")
                    st.code(str(exc))

    st.subheader("Ürün Listesi")
    if urunler.empty:
        st.info("Ürün kaydı bulunamadı.")
    else:
        cols = [c for c in ["urun_id", "kategori", "urun_adi", "model", "renk", "birim", "varsayilan_fiyat", "stok", "durum", "not"] if c in urunler.columns]
        st.dataframe(format_table(urunler[cols]), use_container_width=True, hide_index=True)


def settings_page():
    st.title("⚙️ Ayarlar / Kontrol")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Verileri Yenile", use_container_width=True):
            clear_cache()
            st.success("Önbellek temizlendi. Veriler Google Sheets'ten yeniden okunacak.")
            st.rerun()
    with c2:
        if st.button("Bağlantıyı Test Et", use_container_width=True):
            try:
                sh = get_spreadsheet()
                st.success(f"Bağlantı başarılı: {sh.title}")
            except Exception as exc:
                st.error("Bağlantı hatası")
                st.code(str(exc))

    st.subheader("Sheet / Kolon Kontrolü")
    st.dataframe(audit_schema(), use_container_width=True, hide_index=True)

    with st.expander("Başlık satırı tespiti"):
        for sheet_name in ["Firmalar", "Urunler", "Siparisler", "Siparis_Kalemleri", "Odemeler"]:
            try:
                meta = get_sheet_meta(sheet_name)
                st.markdown(f"**{sheet_name}** — başlık satırı: `{meta.header_row_index}`")
                st.caption(", ".join(meta.headers))
            except Exception as exc:
                st.warning(f"{sheet_name}: {exc}")

    st.info(
        "Bu uygulama başlık satırını ilk 10 satır içinde otomatik bulur. Böylece sheet'te başlık 1. satırda da olsa, "
        "üstte açıklama satırı olup kolonlar 2. satırda da olsa aynı kod çalışır."
    )


def main():
    st.sidebar.title("Gündays Home")
    st.sidebar.caption("Google Sheets tabanlı sipariş sistemi")
    page = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Yeni Sipariş", "Siparişler", "Ödemeler", "Firmalar", "Ürünler", "Ayarlar"],
        label_visibility="collapsed",
    )

    try:
        firmalar, urunler, siparisler, kalemler, odemeler = load_all()
    except Exception as exc:
        show_connection_error(exc)
        return

    st.sidebar.divider()
    if st.sidebar.button("↻ Verileri Yenile", use_container_width=True):
        clear_cache()
        st.rerun()

    if page == "Dashboard":
        dashboard_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Yeni Sipariş":
        new_order_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Siparişler":
        orders_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Ödemeler":
        payments_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Firmalar":
        companies_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Ürünler":
        products_page(firmalar, urunler, siparisler, kalemler, odemeler)
    elif page == "Ayarlar":
        settings_page()


if __name__ == "__main__":
    main()
