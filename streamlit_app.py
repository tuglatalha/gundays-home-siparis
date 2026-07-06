import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from io import BytesIO
import zipfile
import re
import uuid

st.set_page_config(
    page_title="Günday's Home Sipariş Takip",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Premium CSS
# -----------------------------
st.markdown(
    """
    <style>
    :root {
        --gh-bg: #060913;
        --gh-card: #0f172a;
        --gh-card-2: #111827;
        --gh-gold: #D6A84F;
        --gh-gold-2: #F4D27A;
        --gh-text: #F8FAFC;
        --gh-muted: #CBD5E1;
        --gh-line: rgba(214,168,79,.28);
    }
    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(214,168,79,.18) 0, rgba(214,168,79,0) 24%),
            radial-gradient(circle at 90% 15%, rgba(37,99,235,.14) 0, rgba(37,99,235,0) 28%),
            linear-gradient(135deg, #070A12 0%, #0B1220 45%, #05070D 100%) !important;
        color: var(--gh-text) !important;
    }
    .block-container { padding-top: 3.2rem !important; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090F1D 0%, #111827 60%, #070A12 100%) !important;
        border-right: 1px solid var(--gh-line) !important;
        box-shadow: 12px 0 40px rgba(0,0,0,.28);
    }
    [data-testid="stSidebar"] * { color: #F8FAFC !important; }
    h1, h2, h3, h4, h5, h6, p, label, span, div { color: inherit; }
    .main-title {
        font-size: 34px;
        font-weight: 950;
        letter-spacing: -0.7px;
        color: #fff !important;
        margin-bottom: 2px;
        text-shadow: 0 8px 32px rgba(0,0,0,.35);
    }
    .sub-title { color: var(--gh-muted) !important; font-size: 14px; margin-top: 4px; }
    .gold { color: var(--gh-gold-2) !important; }
    .metric-card {
        padding: 22px 20px !important;
        border-radius: 20px !important;
        background:
            linear-gradient(145deg, rgba(214,168,79,.16), rgba(15,23,42,.98) 34%, rgba(17,24,39,.94)) !important;
        border: 1px solid rgba(214,168,79,.42) !important;
        box-shadow: 0 18px 48px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06) !important;
        min-height: 118px !important;
        color: #F8FAFC !important;
    }
    .metric-label { color: #E2E8F0 !important; font-size: 13px !important; margin-bottom: 10px !important; font-weight: 800 !important; }
    .metric-value { color: #FFFFFF !important; font-size: 31px !important; font-weight: 950 !important; line-height: 1.05 !important; }
    .metric-foot { color: #F4D27A !important; font-size: 12px !important; margin-top: 8px !important; font-weight: 700 !important; }
    .panel-box {
        padding: 18px;
        border-radius: 18px;
        background: rgba(17,24,39,.82) !important;
        border: 1px solid rgba(255,255,255,.10) !important;
    }
    .status-pill { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 900; }
    .stButton > button, .stDownloadButton > button {
        border-radius: 13px !important;
        border: 1px solid rgba(214,168,79,.48) !important;
        background: linear-gradient(135deg, rgba(214,168,79,.20), rgba(15,23,42,.86)) !important;
        color: #F8FAFC !important;
        font-weight: 850 !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: rgba(244,210,122,.86) !important;
        color: #fff !important;
        box-shadow: 0 10px 24px rgba(214,168,79,.16) !important;
    }
    div[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,.10); border-radius: 16px; overflow: hidden; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; }
    [data-testid="stMetricLabel"] { color: #CBD5E1 !important; }
    hr { border-color: rgba(255,255,255,.10) !important; }
    .small-muted { color:#94a3b8 !important; font-size:12px; }
    .danger-box {
        border: 1px solid rgba(248,113,113,.35);
        background: rgba(127,29,29,.16);
        border-radius: 16px;
        padding: 14px 16px;
        color: #FEE2E2 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Constants
# -----------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = {
    "Firmalar": ["Firma_ID", "Firma_Adi", "Sube", "Yetkili", "Telefon", "Adres", "Vergi_No", "Vergi_Dairesi", "Not", "Aktif", "Kayit_Tarihi"],
    "Urunler": ["Urun_ID", "Urun_Adi", "Model", "Renk", "Birim_Fiyat", "Stok", "Not", "Aktif", "Kayit_Tarihi"],
    "Siparisler": ["Siparis_ID", "Siparis_No", "Firma_ID", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Sevkiyat_Notu", "Genel_Not", "Olusturan", "Guncelleme_Tarihi"],
    "Siparis_Kalemleri": ["Kalem_ID", "Siparis_ID", "Siparis_No", "Urun_ID", "Urun_Adi", "Model", "Renk", "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"],
    "Odemeler": ["Odeme_ID", "Siparis_ID", "Siparis_No", "Firma_Adi", "Tarih", "Tutar", "Odeme_Tipi", "Not"],
    "Kullanicilar": ["Kullanici_Adi", "Sifre", "Rol", "Aktif"],
    "Listeler": ["Tip", "Deger", "Sira"],
}

ORDER_STATUSES = ["Sipariş Alındı", "Üretime Aktarıldı", "Üretimde", "Hazır", "Sevkiyat Bekliyor", "Gönderildi", "Teslim Edildi", "İptal Edildi"]
PAYMENT_STATUSES = ["Bekliyor", "Kısmi Ödendi", "Ödendi", "İptal / İade"]
PAYMENT_TYPES = ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet", "Diğer"]

# -----------------------------
# Helper functions
# -----------------------------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return date.today().strftime("%Y-%m-%d")


def make_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"


def clean_money(value):
    try:
        if value in [None, ""]:
            return 0.0
        s = str(value).replace("TL", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
        return float(s)
    except Exception:
        return 0.0


def fmt_tl(value) -> str:
    try:
        value = float(value)
    except Exception:
        value = 0
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def as_number_df(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(clean_money)
    return df


@st.cache_resource(show_spinner=False)
def get_google_client():
    if "gcp_service_account" not in st.secrets or "SPREADSHEET_ID" not in st.secrets:
        raise RuntimeError("Streamlit Secrets içinde SPREADSHEET_ID ve gcp_service_account eksik.")
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and "\\n" in info["private_key"]:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def open_spreadsheet():
    gc = get_google_client()
    return gc.open_by_key(st.secrets["SPREADSHEET_ID"])


def get_or_create_ws(name: str):
    sh = open_spreadsheet()
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=max(12, len(SHEET_HEADERS.get(name, []))))
        if name in SHEET_HEADERS:
            ws.append_row(SHEET_HEADERS[name])
        return ws

    headers = SHEET_HEADERS.get(name)
    if headers:
        existing = ws.row_values(1)
        if not existing:
            ws.update("A1", [headers])
        else:
            merged = existing[:]
            changed = False
            for h in headers:
                if h not in merged:
                    merged.append(h)
                    changed = True
            if changed:
                end_col = chr(64 + len(merged)) if len(merged) <= 26 else "AZ"
                ws.update(f"A1:{end_col}1", [merged])
    return ws


def initialize_book():
    for name in SHEET_HEADERS:
        get_or_create_ws(name)

    # Default user
    users = read_sheet("Kullanicilar")
    if users.empty:
        append_row("Kullanicilar", {
            "Kullanici_Adi": "admin",
            "Sifre": "admin123",
            "Rol": "Admin",
            "Aktif": "Evet",
        })

    # Default lists
    lists_df = read_sheet("Listeler")
    if lists_df.empty:
        rows = []
        for i, d in enumerate(ORDER_STATUSES, start=1):
            rows.append({"Tip": "Siparis_Durumu", "Deger": d, "Sira": i})
        for i, d in enumerate(PAYMENT_STATUSES, start=1):
            rows.append({"Tip": "Odeme_Durumu", "Deger": d, "Sira": i})
        ws = get_or_create_ws("Listeler")
        ws.append_rows([[r.get(h, "") for h in SHEET_HEADERS["Listeler"]] for r in rows])


def read_sheet(name: str) -> pd.DataFrame:
    ws = get_or_create_ws(name)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=SHEET_HEADERS.get(name, []))
    headers = values[0]
    rows = values[1:]
    if not rows:
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame(rows, columns=headers)
    df = df.dropna(how="all")
    df = df.loc[~(df.astype(str).apply(lambda row: "".join(row).strip(), axis=1) == "")]
    return df


def append_row(name: str, data: dict):
    ws = get_or_create_ws(name)
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")
    st.cache_data.clear()


def update_row_by_id(sheet_name: str, id_col: str, id_value: str, updates: dict) -> bool:
    ws = get_or_create_ws(sheet_name)
    values = ws.get_all_values()
    if not values:
        return False
    headers = values[0]
    if id_col not in headers:
        return False
    id_idx = headers.index(id_col)
    target_row = None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > id_idx and str(row[id_idx]) == str(id_value):
            target_row = i
            break
    if not target_row:
        return False
    for col_name, value in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            ws.update_cell(target_row, col_idx, value)
    st.cache_data.clear()
    return True


def delete_rows_matching(sheet_name: str, match_col: str, match_value: str) -> int:
    """Belirli değeri taşıyan satırları kalıcı olarak siler. Alt satırdan başlayarak siler."""
    ws = get_or_create_ws(sheet_name)
    values = ws.get_all_values()
    if not values:
        return 0
    headers = values[0]
    if match_col not in headers:
        return 0
    idx = headers.index(match_col)
    rows_to_delete = []
    for row_no, row in enumerate(values[1:], start=2):
        if len(row) > idx and str(row[idx]).strip() == str(match_value).strip():
            rows_to_delete.append(row_no)
    for row_no in reversed(rows_to_delete):
        ws.delete_rows(row_no)
    if rows_to_delete:
        st.cache_data.clear()
    return len(rows_to_delete)


def is_active_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Aktif" not in df.columns:
        return df
    return df[df["Aktif"].astype(str).str.lower().str.strip() != "hayır"].copy()


@st.cache_data(ttl=20, show_spinner=False)
def load_all_data():
    data = {name: read_sheet(name) for name in SHEET_HEADERS}
    data["Urunler"] = as_number_df(data["Urunler"], ["Birim_Fiyat", "Stok"])
    data["Siparisler"] = as_number_df(data["Siparisler"], ["Toplam_Tutar"])
    data["Siparis_Kalemleri"] = as_number_df(data["Siparis_Kalemleri"], ["Adet", "Birim_Fiyat", "Satir_Toplam"])
    data["Odemeler"] = as_number_df(data["Odemeler"], ["Tutar"])
    return data


def make_backup_file(data: dict):
    """Excel yedeği üretir. openpyxl kurulu değilse hata vermeden CSV zip üretir."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for name, df in data.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        return (
            output.getvalue(),
            f"gundays_home_yedek_{timestamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Excel"
        )
    except Exception:
        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, df in data.items():
                zf.writestr(f"{name}.csv", df.to_csv(index=False).encode("utf-8-sig"))
        return (
            output.getvalue(),
            f"gundays_home_yedek_{timestamp}.zip",
            "application/zip",
            "CSV Zip"
        )


def export_excel(data: dict) -> bytes:
    return make_backup_file(data)[0]


def status_badge(status):
    colors = {
        "Sipariş Alındı": ("#2563eb", "#dbeafe"),
        "Üretime Aktarıldı": ("#7c3aed", "#ede9fe"),
        "Üretimde": ("#f59e0b", "#fff7ed"),
        "Hazır": ("#9333ea", "#f3e8ff"),
        "Sevkiyat Bekliyor": ("#ca8a04", "#fef9c3"),
        "Gönderildi": ("#0891b2", "#cffafe"),
        "Teslim Edildi": ("#16a34a", "#dcfce7"),
        "İptal Edildi": ("#dc2626", "#fee2e2"),
    }
    bg, fg = colors.get(status, ("#475569", "#f8fafc"))
    return f"<span class='status-pill' style='background:{bg}; color:{fg};'>{status}</span>"


def require_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = ""
    if st.session_state.logged_in:
        return True

    st.markdown("<div class='main-title'>Günday's Home <span class='gold'>Sipariş Takip</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Sipariş, firma, ürün, sevkiyat ve ödeme durumlarını tek panelden yönetin.</div>", unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns([1.1, 1.2, 1.1])
    with c2:
        st.markdown("### Yönetim Paneli Girişi")
        username = st.text_input("Kullanıcı adı")
        password = st.text_input("Şifre", type="password")
        login = st.button("Giriş yap", use_container_width=True)
        st.info("İlk kurulum bilgisi: admin / admin123. Yayına almadan önce şifreyi değiştirin.")
        if login:
            try:
                initialize_book()
                users = read_sheet("Kullanicilar")
                users = users.fillna("")
                ok = False
                role = ""
                for _, row in users.iterrows():
                    if str(row.get("Kullanici_Adi", "")) == username and str(row.get("Sifre", "")) == password and str(row.get("Aktif", "Evet")) != "Hayır":
                        ok = True
                        role = str(row.get("Rol", "Admin"))
                        break
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
            except Exception as e:
                st.error("Google Sheets bağlantısı kurulamadı.")
                st.code(str(e))
                st.warning("Secrets bilgilerinin doğru girildiğini ve service account mailinin Google Sheet'e Düzenleyici olarak eklendiğini kontrol edin.")
    return False


def sidebar():
    with st.sidebar:
        st.markdown("## Günday's Home")
        st.caption(f"Kullanıcı: {st.session_state.get('user','')} / {st.session_state.get('role','')}")
        page = st.radio(
            "Menü",
            ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Ödemeler", "Raporlar", "Yedek / Ayarlar"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Çıkış yap", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = ""
            st.rerun()
    return page


def header(title, subtitle=""):
    st.markdown(f"<div class='main-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='sub-title'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


def dashboard(data):
    orders = data["Siparisler"]
    lines = data["Siparis_Kalemleri"]
    payments = data["Odemeler"]

    total_orders = len(orders)
    active_orders = len(orders[~orders["Durum"].isin(["Teslim Edildi", "İptal Edildi"])]) if not orders.empty and "Durum" in orders.columns else 0
    revenue = orders["Toplam_Tutar"].sum() if not orders.empty and "Toplam_Tutar" in orders.columns else 0
    paid = payments["Tutar"].sum() if not payments.empty and "Tutar" in payments.columns else 0
    pending = max(revenue - paid, 0)

    header("Dashboard", "Günday's Home genel sipariş özeti")

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Toplam Sipariş", total_orders, "Tüm kayıtlar"),
        ("Aktif Sipariş", active_orders, "Teslim/iptal hariç"),
        ("Ciro", fmt_tl(revenue), "Sipariş toplamı"),
        ("Ödeme Bekleyen", fmt_tl(pending), "Tahsilat farkı"),
    ]
    for c, (label, val, foot) in zip([c1, c2, c3, c4], cards):
        with c:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div><div class='metric-foot'>{foot}</div></div>", unsafe_allow_html=True)

    st.divider()
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("### Son Siparişler")
        if orders.empty:
            st.info("Henüz sipariş eklenmedi.")
        else:
            view = orders.copy().tail(10).iloc[::-1]
            show_cols = [c for c in ["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar"] if c in view.columns]
            st.dataframe(view[show_cols], use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Durum Dağılımı")
        if orders.empty or "Durum" not in orders.columns:
            st.info("Grafik için veri yok.")
        else:
            counts = orders["Durum"].value_counts().reset_index()
            counts.columns = ["Durum", "Adet"]
            st.bar_chart(counts, x="Durum", y="Adet", use_container_width=True)

    st.markdown("### Hızlı Uyarılar")
    warnings = []
    if not orders.empty and "Durum" in orders.columns:
        waiting_ship = len(orders[orders["Durum"] == "Sevkiyat Bekliyor"])
        production = len(orders[orders["Durum"] == "Üretimde"])
        if waiting_ship:
            warnings.append(f"🚚 Sevkiyat bekleyen {waiting_ship} sipariş var.")
        if production:
            warnings.append(f"🛠️ Üretimde {production} sipariş var.")
    if pending > 0:
        warnings.append(f"💰 Toplam tahsilat bekleyen: {fmt_tl(pending)}")
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success("Şu an kritik uyarı yok.")


def firmalar_page(data):
    header("Firmalar", "Bayi, müşteri ve şube kartlarını yönetin")
    firms = data["Firmalar"]
    orders = data["Siparisler"]

    with st.expander("+ Yeni firma / şube ekle", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            firma_adi = st.text_input("Firma adı *")
            sube = st.text_input("Şube")
            yetkili = st.text_input("Yetkili kişi")
        with c2:
            telefon = st.text_input("Telefon")
            vergi_no = st.text_input("Vergi No / VKN")
            vergi_dairesi = st.text_input("Vergi Dairesi")
        with c3:
            adres = st.text_area("Adres", height=90)
            notlar = st.text_area("Not", height=90)
        if st.button("Firmayı kaydet", use_container_width=True):
            if not firma_adi.strip():
                st.error("Firma adı zorunlu.")
            else:
                append_row("Firmalar", {
                    "Firma_ID": make_id("FIRMA"),
                    "Firma_Adi": firma_adi.strip(),
                    "Sube": sube.strip(),
                    "Yetkili": yetkili.strip(),
                    "Telefon": telefon.strip(),
                    "Adres": adres.strip(),
                    "Vergi_No": vergi_no.strip(),
                    "Vergi_Dairesi": vergi_dairesi.strip(),
                    "Not": notlar.strip(),
                    "Aktif": "Evet",
                    "Kayit_Tarihi": now_str(),
                })
                st.success("Firma kaydedildi.")
                st.rerun()

    st.markdown("### Kayıtlı Firmalar")
    if firms.empty:
        st.info("Henüz firma yok.")
        return

    st.dataframe(firms, use_container_width=True, hide_index=True)

    st.markdown("### Firma Düzelt / Sil")
    st.caption("Hatalı girilen firma bilgilerini buradan düzeltebilir veya silmeden pasife alabilirsin.")
    options = [f"{r.get('Firma_Adi','')} / {r.get('Sube','')} [{r.get('Firma_ID','')}]" for _, r in firms.iterrows()]
    selected = st.selectbox("Firma seç", options, key="firma_edit_select")
    selected_id = selected.split("[")[-1].replace("]", "").strip()
    row = firms[firms["Firma_ID"].astype(str) == selected_id].iloc[0]

    with st.form("firma_duzenle_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_firma = st.text_input("Firma adı", value=str(row.get("Firma_Adi", "")), key="e_firma")
            e_sube = st.text_input("Şube", value=str(row.get("Sube", "")), key="e_sube")
            e_yetkili = st.text_input("Yetkili", value=str(row.get("Yetkili", "")), key="e_yetkili")
        with c2:
            e_tel = st.text_input("Telefon", value=str(row.get("Telefon", "")), key="e_tel")
            e_vkn = st.text_input("Vergi No / VKN", value=str(row.get("Vergi_No", "")), key="e_vkn")
            e_vd = st.text_input("Vergi Dairesi", value=str(row.get("Vergi_Dairesi", "")), key="e_vd")
        with c3:
            e_adres = st.text_area("Adres", value=str(row.get("Adres", "")), height=88, key="e_adres")
            e_not = st.text_area("Not", value=str(row.get("Not", "")), height=88, key="e_not")
            e_aktif = st.selectbox("Aktif", ["Evet", "Hayır"], index=0 if str(row.get("Aktif", "Evet")) != "Hayır" else 1, key="e_aktif")
        kaydet = st.form_submit_button("Firma bilgilerini güncelle", use_container_width=True)
        if kaydet:
            ok = update_row_by_id("Firmalar", "Firma_ID", selected_id, {
                "Firma_Adi": e_firma.strip(),
                "Sube": e_sube.strip(),
                "Yetkili": e_yetkili.strip(),
                "Telefon": e_tel.strip(),
                "Adres": e_adres.strip(),
                "Vergi_No": e_vkn.strip(),
                "Vergi_Dairesi": e_vd.strip(),
                "Not": e_not.strip(),
                "Aktif": e_aktif,
            })
            if ok:
                st.success("Firma güncellendi.")
                st.rerun()
            else:
                st.error("Firma güncellenemedi.")

    used = (not orders.empty and "Firma_ID" in orders.columns and selected_id in orders["Firma_ID"].astype(str).tolist())
    st.markdown("#### Firma Silme / Pasife Alma")
    if used:
        st.warning("Bu firma siparişlerde kullanılmış. Kayıt geçmişi bozulmasın diye kalıcı silme yerine pasife alman daha güvenli.")
        if st.button("Bu firmayı pasife al", use_container_width=True, key="firma_pasif"):
            update_row_by_id("Firmalar", "Firma_ID", selected_id, {"Aktif": "Hayır"})
            st.success("Firma pasife alındı. Yeni siparişte listelenmez.")
            st.rerun()
    else:
        confirm = st.checkbox("Bu firmayı kalıcı silmek istediğimi onaylıyorum", key="firma_sil_onay")
        if st.button("Firmayı kalıcı sil", use_container_width=True, key="firma_sil"):
            if not confirm:
                st.error("Silmek için onay kutusunu işaretle.")
            else:
                deleted = delete_rows_matching("Firmalar", "Firma_ID", selected_id)
                st.success(f"Firma silindi. Silinen satır: {deleted}")
                st.rerun()


def urunler_page(data):
    header("Ürünler", "Ürün kartları, renkler, fiyatlar ve stok bilgisi")
    products = data["Urunler"]
    lines = data["Siparis_Kalemleri"]

    with st.expander("+ Yeni ürün ekle", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            urun_adi = st.text_input("Ürün adı *")
            model = st.text_input("Model")
        with c2:
            renk = st.text_input("Renk")
            fiyat = st.number_input("Birim fiyat", min_value=0.0, step=100.0)
        with c3:
            stok = st.number_input("Stok", min_value=0, step=1)
            notlar = st.text_area("Not", height=90)
        if st.button("Ürünü kaydet", use_container_width=True):
            if not urun_adi.strip():
                st.error("Ürün adı zorunlu.")
            else:
                append_row("Urunler", {
                    "Urun_ID": make_id("URUN"),
                    "Urun_Adi": urun_adi.strip(),
                    "Model": model.strip(),
                    "Renk": renk.strip(),
                    "Birim_Fiyat": fiyat,
                    "Stok": stok,
                    "Not": notlar.strip(),
                    "Aktif": "Evet",
                    "Kayit_Tarihi": now_str(),
                })
                st.success("Ürün kaydedildi.")
                st.rerun()

    st.markdown("### Kayıtlı Ürünler")
    if products.empty:
        st.info("Henüz ürün yok.")
        return

    st.dataframe(products, use_container_width=True, hide_index=True)

    st.markdown("### Ürün Düzelt / Sil")
    options = [f"{r.get('Urun_Adi','')} / {r.get('Model','')} / {r.get('Renk','')} [{r.get('Urun_ID','')}]" for _, r in products.iterrows()]
    selected = st.selectbox("Ürün seç", options, key="urun_edit_select")
    selected_id = selected.split("[")[-1].replace("]", "").strip()
    row = products[products["Urun_ID"].astype(str) == selected_id].iloc[0]

    with st.form("urun_duzenle_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_urun = st.text_input("Ürün adı", value=str(row.get("Urun_Adi", "")), key="e_urun")
            e_model = st.text_input("Model", value=str(row.get("Model", "")), key="e_model")
        with c2:
            e_renk = st.text_input("Renk", value=str(row.get("Renk", "")), key="e_renk")
            e_fiyat = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=float(clean_money(row.get("Birim_Fiyat", 0))), key="e_fiyat")
        with c3:
            e_stok = st.number_input("Stok", min_value=0, step=1, value=int(clean_money(row.get("Stok", 0))), key="e_stok")
            e_not = st.text_area("Not", value=str(row.get("Not", "")), height=88, key="e_urun_not")
            e_aktif = st.selectbox("Aktif", ["Evet", "Hayır"], index=0 if str(row.get("Aktif", "Evet")) != "Hayır" else 1, key="e_urun_aktif")
        kaydet = st.form_submit_button("Ürün bilgilerini güncelle", use_container_width=True)
        if kaydet:
            ok = update_row_by_id("Urunler", "Urun_ID", selected_id, {
                "Urun_Adi": e_urun.strip(),
                "Model": e_model.strip(),
                "Renk": e_renk.strip(),
                "Birim_Fiyat": e_fiyat,
                "Stok": e_stok,
                "Not": e_not.strip(),
                "Aktif": e_aktif,
            })
            if ok:
                st.success("Ürün güncellendi.")
                st.rerun()
            else:
                st.error("Ürün güncellenemedi.")

    used = (not lines.empty and "Urun_ID" in lines.columns and selected_id in lines["Urun_ID"].astype(str).tolist())
    st.markdown("#### Ürün Silme / Pasife Alma")
    if used:
        st.warning("Bu ürün siparişlerde kullanılmış. Geçmiş raporlar bozulmasın diye kalıcı silme yerine pasife alman daha güvenli.")
        if st.button("Bu ürünü pasife al", use_container_width=True, key="urun_pasif"):
            update_row_by_id("Urunler", "Urun_ID", selected_id, {"Aktif": "Hayır"})
            st.success("Ürün pasife alındı. Yeni siparişte listelenmez.")
            st.rerun()
    else:
        confirm = st.checkbox("Bu ürünü kalıcı silmek istediğimi onaylıyorum", key="urun_sil_onay")
        if st.button("Ürünü kalıcı sil", use_container_width=True, key="urun_sil"):
            if not confirm:
                st.error("Silmek için onay kutusunu işaretle.")
            else:
                deleted = delete_rows_matching("Urunler", "Urun_ID", selected_id)
                st.success(f"Ürün silindi. Silinen satır: {deleted}")
                st.rerun()


def yeni_siparis_page(data):
    header("Yeni Sipariş", "Firma seçin, ürünleri ekleyin, siparişi Google Sheets'e kaydedin")
    firms = is_active_df(data["Firmalar"])
    products = is_active_df(data["Urunler"])

    if firms.empty:
        st.warning("Önce Firmalar ekranından en az bir firma eklemelisin.")
        return
    if products.empty:
        st.warning("Önce Ürünler ekranından en az bir ürün eklemelisin.")
        return

    if "cart" not in st.session_state:
        st.session_state.cart = []

    firm_options = []
    firm_lookup = {}
    for _, r in firms.iterrows():
        label = f"{r.get('Firma_Adi','')}" + (f" / {r.get('Sube','')}" if str(r.get('Sube','')).strip() else "")
        label += f"  [{r.get('Firma_ID','')}]"
        firm_options.append(label)
        firm_lookup[label] = r

    product_options = []
    product_lookup = {}
    for _, r in products.iterrows():
        label = f"{r.get('Urun_Adi','')}" + (f" - {r.get('Renk','')}" if str(r.get('Renk','')).strip() else "")
        label += (f" / {r.get('Model','')}" if str(r.get('Model','')).strip() else "")
        label += f"  [{r.get('Urun_ID','')}]"
        product_options.append(label)
        product_lookup[label] = r

    st.markdown("### Sipariş Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_firm_label = st.selectbox("Firma / Şube", firm_options)
        siparis_tarihi = st.date_input("Sipariş tarihi", value=date.today())
    with c2:
        teslim_tarihi = st.date_input("Tahmini teslim tarihi", value=date.today())
        durum = st.selectbox("Sipariş durumu", ORDER_STATUSES)
    with c3:
        odeme_durumu = st.selectbox("Ödeme durumu", PAYMENT_STATUSES)
        olusturan = st.text_input("Oluşturan", value=st.session_state.get("user", "admin"))

    sevkiyat_notu = st.text_area("Sevkiyat notu")
    genel_not = st.text_area("Genel not")

    st.markdown("### Ürün Kalemi Ekle")
    c1, c2, c3, c4 = st.columns([2.2, .8, .9, 1])
    with c1:
        selected_product_label = st.selectbox("Ürün", product_options)
    selected_product = product_lookup[selected_product_label]
    default_price = clean_money(selected_product.get("Birim_Fiyat", 0))
    with c2:
        adet = st.number_input("Adet", min_value=1, step=1, value=1)
    with c3:
        birim_fiyat = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=float(default_price))
    with c4:
        satir_toplam = adet * birim_fiyat
        st.metric("Satır toplamı", fmt_tl(satir_toplam))
    kalem_notu = st.text_input("Kalem notu")

    if st.button("+ Kalemi sepete ekle", use_container_width=True):
        st.session_state.cart.append({
            "Urun_ID": selected_product.get("Urun_ID", ""),
            "Urun_Adi": selected_product.get("Urun_Adi", ""),
            "Model": selected_product.get("Model", ""),
            "Renk": selected_product.get("Renk", ""),
            "Adet": adet,
            "Birim_Fiyat": birim_fiyat,
            "Satir_Toplam": satir_toplam,
            "Not": kalem_notu,
        })
        st.success("Kalem eklendi.")
        st.rerun()

    st.markdown("### Sipariş Sepeti")
    if not st.session_state.cart:
        st.info("Henüz kalem eklenmedi.")
    else:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        toplam = float(cart_df["Satir_Toplam"].sum())
        st.markdown(f"#### Sipariş Toplamı: <span class='gold'>{fmt_tl(toplam)}</span>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sepeti temizle", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
        with c2:
            if st.button("Siparişi kaydet", use_container_width=True, type="primary"):
                firm = firm_lookup[selected_firm_label]
                siparis_id = make_id("SIP")
                orders = data["Siparisler"]
                next_no = len(orders) + 1
                siparis_no = f"GH-{datetime.now().year}-{next_no:04d}"
                append_row("Siparisler", {
                    "Siparis_ID": siparis_id,
                    "Siparis_No": siparis_no,
                    "Firma_ID": firm.get("Firma_ID", ""),
                    "Firma_Adi": firm.get("Firma_Adi", ""),
                    "Sube": firm.get("Sube", ""),
                    "Siparis_Tarihi": siparis_tarihi.strftime("%Y-%m-%d"),
                    "Teslim_Tarihi": teslim_tarihi.strftime("%Y-%m-%d"),
                    "Durum": durum,
                    "Odeme_Durumu": odeme_durumu,
                    "Toplam_Tutar": toplam,
                    "Sevkiyat_Notu": sevkiyat_notu,
                    "Genel_Not": genel_not,
                    "Olusturan": olusturan,
                    "Guncelleme_Tarihi": now_str(),
                })
                for item in st.session_state.cart:
                    append_row("Siparis_Kalemleri", {
                        "Kalem_ID": make_id("KLM"),
                        "Siparis_ID": siparis_id,
                        "Siparis_No": siparis_no,
                        **item,
                    })
                st.session_state.cart = []
                st.success(f"Sipariş kaydedildi: {siparis_no}")
                st.rerun()


def siparisler_page(data):
    header("Siparişler", "Siparişleri filtreleyin, durum ve ödeme bilgisini güncelleyin")
    orders = data["Siparisler"]
    lines = data["Siparis_Kalemleri"]
    if orders.empty:
        st.info("Henüz sipariş yok.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        firma_filter = st.text_input("Firma ara")
    with c2:
        status_filter = st.selectbox("Durum filtresi", ["Tümü"] + ORDER_STATUSES)
    with c3:
        payment_filter = st.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_STATUSES)

    view = orders.copy()
    if firma_filter.strip() and "Firma_Adi" in view.columns:
        view = view[view["Firma_Adi"].astype(str).str.contains(firma_filter, case=False, na=False)]
    if status_filter != "Tümü" and "Durum" in view.columns:
        view = view[view["Durum"] == status_filter]
    if payment_filter != "Tümü" and "Odeme_Durumu" in view.columns:
        view = view[view["Odeme_Durumu"] == payment_filter]

    show_cols = [c for c in ["Siparis_No", "Firma_Adi", "Sube", "Siparis_Tarihi", "Teslim_Tarihi", "Durum", "Odeme_Durumu", "Toplam_Tutar", "Sevkiyat_Notu"] if c in view.columns]
    st.dataframe(view[show_cols], use_container_width=True, hide_index=True)

    st.markdown("### Sipariş Detayı / Güncelleme")
    options = [f"{r.get('Siparis_No','')} - {r.get('Firma_Adi','')} / {r.get('Sube','')}" for _, r in view.iterrows()]
    if not options:
        st.info("Filtreye uygun sipariş yok.")
        return
    selected = st.selectbox("Sipariş seç", options)
    selected_no = selected.split(" - ")[0]
    row = orders[orders["Siparis_No"] == selected_no].iloc[0]
    st.markdown(f"#### {row.get('Siparis_No')} - {row.get('Firma_Adi')} {status_badge(row.get('Durum',''))}", unsafe_allow_html=True)

    detail_lines = lines[lines["Siparis_No"] == selected_no] if not lines.empty and "Siparis_No" in lines.columns else pd.DataFrame()
    if not detail_lines.empty:
        st.dataframe(detail_lines[[c for c in ["Urun_Adi", "Model", "Renk", "Adet", "Birim_Fiyat", "Satir_Toplam", "Not"] if c in detail_lines.columns]], use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        new_status = st.selectbox("Yeni durum", ORDER_STATUSES, index=ORDER_STATUSES.index(row.get("Durum")) if row.get("Durum") in ORDER_STATUSES else 0)
        new_ship_note = st.text_area("Sevkiyat notu", value=str(row.get("Sevkiyat_Notu", "")), height=80)
    with c2:
        new_payment = st.selectbox("Yeni ödeme durumu", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(row.get("Odeme_Durumu")) if row.get("Odeme_Durumu") in PAYMENT_STATUSES else 0)
        new_general_note = st.text_area("Genel not", value=str(row.get("Genel_Not", "")), height=80)
    with c3:
        st.write("")
        st.write("")
        if st.button("Siparişi güncelle", use_container_width=True, type="primary"):
            ok = update_row_by_id("Siparisler", "Siparis_ID", row.get("Siparis_ID"), {
                "Durum": new_status,
                "Odeme_Durumu": new_payment,
                "Sevkiyat_Notu": new_ship_note,
                "Genel_Not": new_general_note,
                "Guncelleme_Tarihi": now_str(),
            })
            if ok:
                st.success("Sipariş güncellendi.")
                st.rerun()
            else:
                st.error("Güncelleme yapılamadı.")

    st.markdown("### Hatalı Siparişi Sil")
    st.markdown("<div class='danger-box'>Bu işlem seçili siparişi, sipariş kalemlerini ve bu siparişe bağlı ödeme kayıtlarını Google Sheets'ten kalıcı olarak siler.</div>", unsafe_allow_html=True)
    confirm_delete = st.checkbox(f"{selected_no} numaralı siparişi kalıcı silmek istediğimi onaylıyorum", key=f"delete_order_confirm_{selected_no}")
    if st.button("Seçili siparişi kalıcı sil", use_container_width=True, key=f"delete_order_btn_{selected_no}"):
        if not confirm_delete:
            st.error("Silmek için onay kutusunu işaretle.")
        else:
            deleted_lines = delete_rows_matching("Siparis_Kalemleri", "Siparis_No", selected_no)
            deleted_payments = delete_rows_matching("Odemeler", "Siparis_No", selected_no)
            deleted_orders = delete_rows_matching("Siparisler", "Siparis_ID", row.get("Siparis_ID"))
            st.success(f"Sipariş silindi. Sipariş: {deleted_orders}, Kalem: {deleted_lines}, Ödeme: {deleted_payments}")
            st.rerun()


def odemeler_page(data):
    header("Ödemeler", "Tahsilatları siparişe bağlayın")
    orders = data["Siparisler"]
    payments = data["Odemeler"]
    if orders.empty:
        st.info("Ödeme eklemek için önce sipariş girmelisin.")
        return
    options = [f"{r.get('Siparis_No','')} - {r.get('Firma_Adi','')} - {fmt_tl(r.get('Toplam_Tutar',0))}" for _, r in orders.iterrows()]
    with st.expander("+ Ödeme ekle", expanded=True):
        selected = st.selectbox("Sipariş", options)
        selected_no = selected.split(" - ")[0]
        order = orders[orders["Siparis_No"] == selected_no].iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            tarih = st.date_input("Ödeme tarihi", value=date.today())
        with c2:
            tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
        with c3:
            tip = st.selectbox("Ödeme tipi", PAYMENT_TYPES)
        notlar = st.text_area("Not")
        if st.button("Ödemeyi kaydet", use_container_width=True):
            if tutar <= 0:
                st.error("Tutar sıfırdan büyük olmalı.")
            else:
                append_row("Odemeler", {
                    "Odeme_ID": make_id("ODM"),
                    "Siparis_ID": order.get("Siparis_ID", ""),
                    "Siparis_No": order.get("Siparis_No", ""),
                    "Firma_Adi": order.get("Firma_Adi", ""),
                    "Tarih": tarih.strftime("%Y-%m-%d"),
                    "Tutar": tutar,
                    "Odeme_Tipi": tip,
                    "Not": notlar,
                })
                st.success("Ödeme kaydedildi.")
                st.rerun()

    st.markdown("### Ödeme Kayıtları")
    if payments.empty:
        st.info("Henüz ödeme kaydı yok.")
    else:
        st.dataframe(payments, use_container_width=True, hide_index=True)
        st.markdown("### Hatalı Ödeme Kaydını Sil")
        pay_options = [f"{r.get('Siparis_No','')} - {r.get('Firma_Adi','')} - {fmt_tl(r.get('Tutar',0))} [{r.get('Odeme_ID','')}]" for _, r in payments.iterrows()]
        selected_pay = st.selectbox("Silinecek ödeme kaydı", pay_options, key="payment_delete_select")
        selected_pay_id = selected_pay.split("[")[-1].replace("]", "").strip()
        confirm_pay_delete = st.checkbox("Bu ödeme kaydını kalıcı silmek istediğimi onaylıyorum", key="payment_delete_confirm")
        if st.button("Ödeme kaydını kalıcı sil", use_container_width=True, key="payment_delete_btn"):
            if not confirm_pay_delete:
                st.error("Silmek için onay kutusunu işaretle.")
            else:
                deleted = delete_rows_matching("Odemeler", "Odeme_ID", selected_pay_id)
                st.success(f"Ödeme kaydı silindi. Silinen satır: {deleted}")
                st.rerun()


def raporlar_page(data):
    header("Raporlar", "Firma, ürün ve ödeme bazlı özetler")
    orders = data["Siparisler"]
    lines = data["Siparis_Kalemleri"]
    payments = data["Odemeler"]

    if orders.empty:
        st.info("Rapor için sipariş verisi yok.")
        return

    st.markdown("### Firma Bazlı Satış")
    if "Firma_Adi" in orders.columns:
        firm_report = orders.groupby("Firma_Adi", as_index=False).agg(Siparis_Adedi=("Siparis_No", "count"), Toplam_Ciro=("Toplam_Tutar", "sum"))
        st.dataframe(firm_report, use_container_width=True, hide_index=True)
        st.bar_chart(firm_report, x="Firma_Adi", y="Toplam_Ciro", use_container_width=True)

    st.markdown("### Ürün Bazlı Satış")
    if not lines.empty and "Urun_Adi" in lines.columns:
        product_report = lines.groupby("Urun_Adi", as_index=False).agg(Toplam_Adet=("Adet", "sum"), Toplam_Tutar=("Satir_Toplam", "sum"))
        st.dataframe(product_report, use_container_width=True, hide_index=True)
        st.bar_chart(product_report, x="Urun_Adi", y="Toplam_Adet", use_container_width=True)

    st.markdown("### Ödeme Özeti")
    total_revenue = orders["Toplam_Tutar"].sum() if "Toplam_Tutar" in orders.columns else 0
    total_paid = payments["Tutar"].sum() if not payments.empty and "Tutar" in payments.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Sipariş Toplamı", fmt_tl(total_revenue))
    c2.metric("Tahsil Edilen", fmt_tl(total_paid))
    c3.metric("Kalan", fmt_tl(max(total_revenue - total_paid, 0)))

    st.markdown("### Rapor Dışa Aktar")
    backup_bytes, backup_name, backup_mime, backup_type = make_backup_file({
        "Siparisler": orders,
        "Siparis_Kalemleri": lines,
        "Odemeler": payments,
    })
    st.download_button(
        f"Raporları indir ({backup_type})",
        data=backup_bytes,
        file_name=backup_name,
        mime=backup_mime,
        use_container_width=True,
    )


def settings_page(data):
    header("Yedek / Ayarlar", "Excel dışa aktarım, bağlantı kontrolü ve şifre değişimi")
    st.markdown("### Google Sheets Bağlantısı")
    st.success("Google Sheets bağlantısı aktif.")
    st.code(f"SPREADSHEET_ID = {st.secrets.get('SPREADSHEET_ID', '')}")

    st.markdown("### Excel Yedeği İndir")
    backup_bytes, backup_name, backup_mime, backup_type = make_backup_file(data)
    st.download_button(
        f"Tüm verileri indir ({backup_type})",
        data=backup_bytes,
        file_name=backup_name,
        mime=backup_mime,
        use_container_width=True,
    )

    st.markdown("### Şifre Değiştir")
    users = data["Kullanicilar"]
    old = st.text_input("Mevcut şifre", type="password")
    new1 = st.text_input("Yeni şifre", type="password")
    new2 = st.text_input("Yeni şifre tekrar", type="password")
    if st.button("Şifreyi değiştir", use_container_width=True):
        username = st.session_state.get("user", "admin")
        user_rows = users[users["Kullanici_Adi"] == username] if not users.empty and "Kullanici_Adi" in users.columns else pd.DataFrame()
        if user_rows.empty:
            st.error("Kullanıcı bulunamadı.")
        elif str(user_rows.iloc[0].get("Sifre", "")) != old:
            st.error("Mevcut şifre yanlış.")
        elif not new1 or len(new1) < 6:
            st.error("Yeni şifre en az 6 karakter olmalı.")
        elif new1 != new2:
            st.error("Yeni şifreler eşleşmiyor.")
        else:
            ok = update_row_by_id("Kullanicilar", "Kullanici_Adi", username, {"Sifre": new1})
            if ok:
                st.success("Şifre değiştirildi. Tekrar giriş yapman gerekebilir.")
            else:
                st.error("Şifre değiştirilemedi.")


def main():
    if not require_login():
        return
    try:
        initialize_book()
        data = load_all_data()
    except Exception as e:
        st.error("Google Sheets bağlantısı kurulamadı veya tablolar okunamadı.")
        st.code(str(e))
        st.stop()

    page = sidebar()
    if page == "Dashboard":
        dashboard(data)
    elif page == "Yeni Sipariş":
        yeni_siparis_page(data)
    elif page == "Siparişler":
        siparisler_page(data)
    elif page == "Firmalar":
        firmalar_page(data)
    elif page == "Ürünler":
        urunler_page(data)
    elif page == "Ödemeler":
        odemeler_page(data)
    elif page == "Raporlar":
        raporlar_page(data)
    elif page == "Yedek / Ayarlar":
        settings_page(data)


if __name__ == "__main__":
    main()
