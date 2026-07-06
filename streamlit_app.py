import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st

APP_TITLE = "Günday's Home Sipariş Takip"
DB_PATH = Path("gundays_home.db")
STATUS_OPTIONS = [
    "Sipariş Alındı",
    "Üretime Aktarıldı",
    "Üretimde",
    "Hazır",
    "Sevkiyat Bekliyor",
    "Gönderildi",
    "Teslim Edildi",
    "İptal Edildi",
]
PAYMENT_OPTIONS = ["Bekliyor", "Kısmi Ödendi", "Ödendi", "Vadeli", "İptal"]

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        [data-testid="stSidebar"] {background: #111827;}
        [data-testid="stSidebar"] * {color: #f9fafb !important;}
        div[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e5e7eb; padding: 16px; border-radius: 16px; box-shadow: 0 8px 22px rgba(17, 24, 39, .06);} 
        .gh-card {background:#ffffff; border:1px solid #e5e7eb; border-radius:18px; padding:18px; box-shadow: 0 8px 22px rgba(17, 24, 39, .06);}
        .gh-small {font-size:13px; color:#6b7280;}
        .gh-title {font-size:28px; font-weight:800; letter-spacing:-.02em;}
        .status-pill {display:inline-block; padding:4px 10px; border-radius:999px; background:#f3f4f6; font-size:12px; font-weight:700; color:#111827;}
        .success-pill {background:#ecfdf5; color:#065f46;}
        .warning-pill {background:#fffbeb; color:#92400e;}
        .danger-pill {background:#fef2f2; color:#991b1b;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Database helpers
# -----------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=(), many=False):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if many:
            cur.executemany(query, params)
        else:
            cur.execute(query, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def query_df(query, params=()):
    conn = get_conn()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def query_one(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        return cur.fetchone()
    finally:
        conn.close()


def query_all(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, digest


def verify_password(password: str, salt: str, digest: str):
    _, check_digest = hash_password(password, salt)
    return secrets.compare_digest(check_digest, digest)


def init_db():
    execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Admin',
            created_at TEXT NOT NULL
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS firms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            branch TEXT,
            authorized_person TEXT,
            phone TEXT,
            address TEXT,
            tax_no TEXT,
            tax_office TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            model TEXT,
            colors TEXT,
            default_price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            firm_id INTEGER,
            branch TEXT,
            order_date TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            shipping_method TEXT,
            shipping_note TEXT,
            general_note TEXT,
            total_amount REAL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(firm_id) REFERENCES firms(id)
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            model TEXT,
            color TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            note TEXT,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )

    user_count = query_one("SELECT COUNT(*) AS c FROM users")["c"]
    if user_count == 0:
        default_user = st.secrets.get("ADMIN_USERNAME", "admin") if hasattr(st, "secrets") else "admin"
        default_pass = st.secrets.get("ADMIN_PASSWORD", "admin123") if hasattr(st, "secrets") else "admin123"
        salt, digest = hash_password(default_pass)
        execute(
            "INSERT INTO users (username, password_salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (default_user, salt, digest, "Admin", datetime.now().isoformat(timespec="seconds")),
        )

    product_count = query_one("SELECT COUNT(*) AS c FROM products")["c"]
    if product_count == 0:
        now = datetime.now().isoformat(timespec="seconds")
        demo_products = [
            ("İkili Dilsiz Uşak", "Premium", "Naturel, Ceviz, Siyah, Lake Beyaz", 1250, 0, 0, 1, "", now),
            ("Elit Dilsiz Uşak", "Standart", "Naturel, Ceviz, Siyah, Lake Beyaz", 950, 0, 0, 1, "", now),
            ("Katlanır Basamak", "Ahşap", "Naturel, Ceviz, Siyah, Lake Beyaz", 750, 0, 0, 1, "", now),
        ]
        execute(
            """
            INSERT INTO products (name, model, colors, default_price, cost, stock, active, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            demo_products,
            many=True,
        )


def next_order_no():
    year = datetime.now().year
    prefix = f"GH-{year}-"
    row = query_one("SELECT order_no FROM orders WHERE order_no LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",))
    if not row:
        return prefix + "0001"
    last = row["order_no"].split("-")[-1]
    return prefix + str(int(last) + 1).zfill(4)


def money(x):
    try:
        return f"{float(x):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 TL"


def to_excel_bytes(sheets: dict[str, pd.DataFrame]):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, index=False, sheet_name=safe_name)
    output.seek(0)
    return output.getvalue()

# -----------------------------
# Auth
# -----------------------------

def login_page():
    st.markdown("<div class='gh-title'>Günday's Home Sipariş Takip</div>", unsafe_allow_html=True)
    st.caption("Sipariş, firma, ürün, sevkiyat ve ödeme durumlarını tek panelden yönetin.")
    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("### Yönetim Paneli Girişi")
        with st.form("login_form"):
            username = st.text_input("Kullanıcı adı")
            password = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş yap", use_container_width=True)
        if submitted:
            user = query_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
            if user and verify_password(password, user["password_salt"], user["password_hash"]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = user["username"]
                st.session_state["role"] = user["role"]
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")
        st.info("İlk kurulum bilgisi: admin / admin123. Yayına almadan önce şifreyi değiştirin.")


def require_login():
    if not st.session_state.get("logged_in"):
        login_page()
        st.stop()

# -----------------------------
# Pages
# -----------------------------

def page_dashboard():
    st.markdown("<div class='gh-title'>Dashboard</div>", unsafe_allow_html=True)
    st.caption("Günday's Home genel sipariş özeti")

    orders = query_df(
        """
        SELECT o.*, COALESCE(f.name, 'Firma Silinmiş') AS firm_name
        FROM orders o
        LEFT JOIN firms f ON f.id = o.firm_id
        ORDER BY o.id DESC
        """
    )
    total_orders = len(orders)
    total_revenue = orders[orders["status"] != "İptal Edildi"]["total_amount"].sum() if not orders.empty else 0
    active_orders = len(orders[~orders["status"].isin(["Teslim Edildi", "İptal Edildi"])]) if not orders.empty else 0
    unpaid = len(orders[orders["payment_status"].isin(["Bekliyor", "Kısmi Ödendi", "Vadeli"])]) if not orders.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Sipariş", total_orders)
    c2.metric("Aktif Sipariş", active_orders)
    c3.metric("Ciro", money(total_revenue))
    c4.metric("Ödeme Bekleyen", unpaid)

    st.divider()
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Son Siparişler")
        if orders.empty:
            st.info("Henüz sipariş eklenmedi.")
        else:
            show = orders[["order_no", "firm_name", "branch", "order_date", "due_date", "status", "payment_status", "total_amount"]].head(10).copy()
            show["total_amount"] = show["total_amount"].apply(money)
            show.columns = ["Sipariş No", "Firma", "Şube", "Sipariş Tarihi", "Teslim Tarihi", "Durum", "Ödeme", "Toplam"]
            st.dataframe(show, hide_index=True, use_container_width=True)
    with right:
        st.subheader("Durum Dağılımı")
        if orders.empty:
            st.info("Grafik için veri yok.")
        else:
            status_df = orders.groupby("status").size().reset_index(name="adet")
            st.bar_chart(status_df.set_index("status"))

    st.subheader("Hızlı Uyarılar")
    if orders.empty:
        st.write("Şu an uyarı yok.")
        return

    ready = orders[orders["status"].isin(["Hazır", "Sevkiyat Bekliyor"])]
    late = orders[(orders["due_date"].notna()) & (orders["due_date"] != "") & (pd.to_datetime(orders["due_date"], errors="coerce") < pd.Timestamp(date.today())) & (~orders["status"].isin(["Teslim Edildi", "İptal Edildi"]))]
    if not ready.empty:
        st.warning(f"{len(ready)} sipariş hazır/sevkiyat bekliyor.")
    if not late.empty:
        st.error(f"{len(late)} siparişin teslim tarihi geçmiş görünüyor.")
    if ready.empty and late.empty:
        st.success("Kritik bekleyen durum görünmüyor.")


def page_new_order():
    st.markdown("<div class='gh-title'>Yeni Sipariş</div>", unsafe_allow_html=True)
    st.caption("Firma seç, ürün kalemlerini ekle, siparişi oluştur.")

    if "cart_items" not in st.session_state:
        st.session_state["cart_items"] = []

    firms = query_all("SELECT id, name, branch FROM firms ORDER BY name, branch")
    products = query_all("SELECT * FROM products WHERE active = 1 ORDER BY name")

    if not firms:
        st.warning("Sipariş oluşturmak için önce en az bir firma eklemelisin.")
        return
    if not products:
        st.warning("Sipariş oluşturmak için önce en az bir ürün eklemelisin.")
        return

    firm_options = {f"{r['name']}" + (f" / {r['branch']}" if r['branch'] else ""): r["id"] for r in firms}
    product_options = {f"{r['name']}" + (f" - {r['model']}" if r['model'] else ""): r for r in products}

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            firm_label = st.selectbox("Firma / Şube", list(firm_options.keys()))
            firm_id = firm_options[firm_label]
        with c2:
            order_date = st.date_input("Sipariş tarihi", value=date.today())
        with c3:
            due_date = st.date_input("Planlanan teslim tarihi", value=None)
        c4, c5, c6 = st.columns(3)
        with c4:
            status = st.selectbox("Durum", STATUS_OPTIONS, index=0)
        with c5:
            payment_status = st.selectbox("Ödeme durumu", PAYMENT_OPTIONS, index=0)
        with c6:
            shipping_method = st.text_input("Sevkiyat şekli", placeholder="Kargo, kendi araç, ambar...")
        shipping_note = st.text_area("Sevkiyat notu", placeholder="Adres detayı, teslim notu, araç bilgisi...")
        general_note = st.text_area("Genel not", placeholder="Özel üretim, renk uyarısı, müşteri talebi...")

    st.subheader("Ürün Kalemi Ekle")
    with st.form("add_item_form", clear_on_submit=False):
        c1, c2, c3, c4, c5 = st.columns([2, 1.1, .8, 1, 1.3])
        with c1:
            product_label = st.selectbox("Ürün", list(product_options.keys()))
            product = product_options[product_label]
        colors = [c.strip() for c in (product["colors"] or "").split(",") if c.strip()]
        with c2:
            color = st.selectbox("Renk", colors or ["-"])
        with c3:
            quantity = st.number_input("Adet", min_value=1, step=1, value=1)
        with c4:
            unit_price = st.number_input("Birim fiyat", min_value=0.0, step=50.0, value=float(product["default_price"] or 0))
        with c5:
            item_note = st.text_input("Kalem notu", placeholder="Opsiyonel")
        add = st.form_submit_button("Kalemi ekle", use_container_width=True)
        if add:
            st.session_state["cart_items"].append(
                {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "model": product["model"] or "",
                    "color": color,
                    "quantity": int(quantity),
                    "unit_price": float(unit_price),
                    "line_total": int(quantity) * float(unit_price),
                    "note": item_note,
                }
            )
            st.success("Kalem eklendi.")
            st.rerun()

    st.subheader("Sipariş Kalemleri")
    if st.session_state["cart_items"]:
        items_df = pd.DataFrame(st.session_state["cart_items"])
        display = items_df[["product_name", "model", "color", "quantity", "unit_price", "line_total", "note"]].copy()
        display["unit_price"] = display["unit_price"].apply(money)
        display["line_total"] = display["line_total"].apply(money)
        display.columns = ["Ürün", "Model", "Renk", "Adet", "Birim Fiyat", "Toplam", "Not"]
        st.dataframe(display, hide_index=True, use_container_width=True)
        total = sum(i["line_total"] for i in st.session_state["cart_items"])
        st.markdown(f"### Toplam: {money(total)}")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Kalemleri temizle", use_container_width=True):
                st.session_state["cart_items"] = []
                st.rerun()
        with c2:
            if st.button("Siparişi kaydet", type="primary", use_container_width=True):
                order_no = next_order_no()
                now = datetime.now().isoformat(timespec="seconds")
                cur = execute(
                    """
                    INSERT INTO orders (
                        order_no, firm_id, branch, order_date, due_date, status, payment_status,
                        shipping_method, shipping_note, general_note, total_amount, created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_no,
                        firm_id,
                        "",
                        order_date.isoformat(),
                        due_date.isoformat() if due_date else "",
                        status,
                        payment_status,
                        shipping_method,
                        shipping_note,
                        general_note,
                        total,
                        st.session_state.get("username", "admin"),
                        now,
                        now,
                    ),
                )
                order_id = cur.lastrowid
                item_rows = [
                    (
                        order_id,
                        i["product_id"],
                        i["product_name"],
                        i["model"],
                        i["color"],
                        i["quantity"],
                        i["unit_price"],
                        i["line_total"],
                        i["note"],
                    )
                    for i in st.session_state["cart_items"]
                ]
                execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, model, color, quantity, unit_price, line_total, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    item_rows,
                    many=True,
                )
                st.session_state["cart_items"] = []
                st.success(f"Sipariş oluşturuldu: {order_no}")
                st.balloons()
    else:
        st.info("Henüz ürün kalemi eklenmedi.")


def page_orders():
    st.markdown("<div class='gh-title'>Siparişler</div>", unsafe_allow_html=True)

    orders = query_df(
        """
        SELECT o.id, o.order_no, COALESCE(f.name, 'Firma Silinmiş') AS firm_name, COALESCE(f.branch, '') AS firm_branch,
               o.order_date, o.due_date, o.status, o.payment_status, o.total_amount, o.shipping_method, o.created_at
        FROM orders o
        LEFT JOIN firms f ON f.id = o.firm_id
        ORDER BY o.id DESC
        """
    )
    if orders.empty:
        st.info("Henüz sipariş yok.")
        return

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        status_filter = c1.selectbox("Durum filtresi", ["Tümü"] + STATUS_OPTIONS)
        payment_filter = c2.selectbox("Ödeme filtresi", ["Tümü"] + PAYMENT_OPTIONS)
        search = c3.text_input("Firma / sipariş no ara")

    filtered = orders.copy()
    if status_filter != "Tümü":
        filtered = filtered[filtered["status"] == status_filter]
    if payment_filter != "Tümü":
        filtered = filtered[filtered["payment_status"] == payment_filter]
    if search:
        s = search.lower()
        filtered = filtered[filtered.apply(lambda r: s in str(r["order_no"]).lower() or s in str(r["firm_name"]).lower(), axis=1)]

    display = filtered[["order_no", "firm_name", "firm_branch", "order_date", "due_date", "status", "payment_status", "total_amount"]].copy()
    display["total_amount"] = display["total_amount"].apply(money)
    display.columns = ["Sipariş No", "Firma", "Şube", "Sipariş Tarihi", "Teslim Tarihi", "Durum", "Ödeme", "Toplam"]
    st.dataframe(display, hide_index=True, use_container_width=True)

    st.subheader("Sipariş Detayı / Güncelle")
    order_labels = {f"{r['order_no']} - {r['firm_name']} - {money(r['total_amount'])}": int(r["id"]) for _, r in filtered.iterrows()}
    if not order_labels:
        st.info("Filtreye uygun sipariş yok.")
        return
    selected_label = st.selectbox("Sipariş seç", list(order_labels.keys()))
    order_id = order_labels[selected_label]
    order = query_one(
        """
        SELECT o.*, COALESCE(f.name, 'Firma Silinmiş') AS firm_name, COALESCE(f.branch, '') AS firm_branch,
               COALESCE(f.phone, '') AS firm_phone, COALESCE(f.address, '') AS firm_address
        FROM orders o LEFT JOIN firms f ON f.id = o.firm_id WHERE o.id = ?
        """,
        (order_id,),
    )
    items = query_df("SELECT product_name, model, color, quantity, unit_price, line_total, note FROM order_items WHERE order_id = ?", (order_id,))
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"### {order['order_no']}")
        st.write(f"**Firma:** {order['firm_name']} {('/ ' + order['firm_branch']) if order['firm_branch'] else ''}")
        st.write(f"**Telefon:** {order['firm_phone']}")
        st.write(f"**Adres:** {order['firm_address']}")
        st.write(f"**Toplam:** {money(order['total_amount'])}")
        st.write(f"**Not:** {order['general_note'] or '-'}")
    with c2:
        with st.form("update_order_form"):
            new_status = st.selectbox("Durum", STATUS_OPTIONS, index=STATUS_OPTIONS.index(order["status"]) if order["status"] in STATUS_OPTIONS else 0)
            new_payment = st.selectbox("Ödeme durumu", PAYMENT_OPTIONS, index=PAYMENT_OPTIONS.index(order["payment_status"]) if order["payment_status"] in PAYMENT_OPTIONS else 0)
            new_ship = st.text_input("Sevkiyat şekli", value=order["shipping_method"] or "")
            new_ship_note = st.text_area("Sevkiyat notu", value=order["shipping_note"] or "")
            save = st.form_submit_button("Güncelle", type="primary", use_container_width=True)
        if save:
            execute(
                "UPDATE orders SET status=?, payment_status=?, shipping_method=?, shipping_note=?, updated_at=? WHERE id=?",
                (new_status, new_payment, new_ship, new_ship_note, datetime.now().isoformat(timespec="seconds"), order_id),
            )
            st.success("Sipariş güncellendi.")
            st.rerun()

    if not items.empty:
        item_show = items.copy()
        item_show["unit_price"] = item_show["unit_price"].apply(money)
        item_show["line_total"] = item_show["line_total"].apply(money)
        item_show.columns = ["Ürün", "Model", "Renk", "Adet", "Birim Fiyat", "Toplam", "Not"]
        st.dataframe(item_show, hide_index=True, use_container_width=True)

    with st.expander("Yazdırılabilir sipariş metni"):
        text_lines = [
            f"GÜNDAY'S HOME SİPARİŞ FORMU",
            f"Sipariş No: {order['order_no']}",
            f"Firma: {order['firm_name']} {('/ ' + order['firm_branch']) if order['firm_branch'] else ''}",
            f"Sipariş Tarihi: {order['order_date']}",
            f"Teslim Tarihi: {order['due_date'] or '-'}",
            f"Durum: {order['status']}",
            f"Ödeme: {order['payment_status']}",
            "",
            "Ürünler:",
        ]
        for _, row in items.iterrows():
            text_lines.append(f"- {row['product_name']} {row['model']} / {row['color']} | {row['quantity']} adet x {money(row['unit_price'])} = {money(row['line_total'])}")
        text_lines += ["", f"Toplam: {money(order['total_amount'])}", "", f"Not: {order['general_note'] or '-'}"]
        st.code("\n".join(text_lines), language="text")


def page_firms():
    st.markdown("<div class='gh-title'>Firmalar</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Firma Listesi", "Yeni Firma"])

    with tab2:
        with st.form("new_firm_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Firma adı *")
            branch = c2.text_input("Şube")
            c3, c4 = st.columns(2)
            authorized = c3.text_input("Yetkili kişi")
            phone = c4.text_input("Telefon")
            address = st.text_area("Adres")
            c5, c6 = st.columns(2)
            tax_no = c5.text_input("VKN / TCKN")
            tax_office = c6.text_input("Vergi dairesi")
            notes = st.text_area("Not")
            submitted = st.form_submit_button("Firmayı kaydet", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Firma adı zorunlu.")
            else:
                execute(
                    """
                    INSERT INTO firms (name, branch, authorized_person, phone, address, tax_no, tax_office, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name.strip(), branch.strip(), authorized, phone, address, tax_no, tax_office, notes, datetime.now().isoformat(timespec="seconds")),
                )
                st.success("Firma kaydedildi.")
                st.rerun()

    with tab1:
        firms = query_df("SELECT * FROM firms ORDER BY id DESC")
        if firms.empty:
            st.info("Henüz firma eklenmedi.")
        else:
            show = firms[["name", "branch", "authorized_person", "phone", "address", "tax_no", "tax_office"]].copy()
            show.columns = ["Firma", "Şube", "Yetkili", "Telefon", "Adres", "VKN/TCKN", "Vergi Dairesi"]
            st.dataframe(show, hide_index=True, use_container_width=True)

            with st.expander("Firma bazlı sipariş özeti"):
                summary = query_df(
                    """
                    SELECT f.name AS Firma, COALESCE(f.branch, '') AS Şube, COUNT(o.id) AS Sipariş,
                           COALESCE(SUM(o.total_amount), 0) AS Toplam
                    FROM firms f LEFT JOIN orders o ON o.firm_id = f.id
                    GROUP BY f.id
                    ORDER BY Toplam DESC
                    """
                )
                if not summary.empty:
                    summary["Toplam"] = summary["Toplam"].apply(money)
                st.dataframe(summary, hide_index=True, use_container_width=True)


def page_products():
    st.markdown("<div class='gh-title'>Ürünler</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Ürün Listesi", "Yeni Ürün"])

    with tab2:
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Ürün adı *")
            model = c2.text_input("Model")
            colors = st.text_input("Renk seçenekleri", placeholder="Naturel, Ceviz, Siyah, Lake Beyaz")
            c3, c4, c5 = st.columns(3)
            default_price = c3.number_input("Varsayılan satış fiyatı", min_value=0.0, step=50.0)
            cost = c4.number_input("Maliyet", min_value=0.0, step=50.0)
            stock = c5.number_input("Stok", min_value=0, step=1)
            notes = st.text_area("Not")
            active = st.checkbox("Aktif", value=True)
            submitted = st.form_submit_button("Ürünü kaydet", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Ürün adı zorunlu.")
            else:
                execute(
                    """
                    INSERT INTO products (name, model, colors, default_price, cost, stock, active, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name.strip(), model.strip(), colors.strip(), default_price, cost, stock, 1 if active else 0, notes, datetime.now().isoformat(timespec="seconds")),
                )
                st.success("Ürün kaydedildi.")
                st.rerun()

    with tab1:
        products = query_df("SELECT * FROM products ORDER BY id DESC")
        if products.empty:
            st.info("Henüz ürün eklenmedi.")
        else:
            show = products[["name", "model", "colors", "default_price", "cost", "stock", "active"]].copy()
            show["default_price"] = show["default_price"].apply(money)
            show["cost"] = show["cost"].apply(money)
            show["active"] = show["active"].map({1: "Aktif", 0: "Pasif"})
            show.columns = ["Ürün", "Model", "Renkler", "Satış Fiyatı", "Maliyet", "Stok", "Durum"]
            st.dataframe(show, hide_index=True, use_container_width=True)


def page_reports():
    st.markdown("<div class='gh-title'>Raporlar</div>", unsafe_allow_html=True)
    orders = query_df(
        """
        SELECT o.*, COALESCE(f.name, 'Firma Silinmiş') AS firm_name, COALESCE(f.branch, '') AS firm_branch
        FROM orders o LEFT JOIN firms f ON f.id = o.firm_id
        """
    )
    items = query_df("SELECT * FROM order_items")

    if orders.empty:
        st.info("Rapor için sipariş verisi yok.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Firma Bazlı Satış")
        firm_report = orders[orders["status"] != "İptal Edildi"].groupby(["firm_name", "firm_branch"], dropna=False).agg(
            Sipariş=("id", "count"), Toplam=("total_amount", "sum")
        ).reset_index().sort_values("Toplam", ascending=False)
        show = firm_report.copy()
        show["Toplam"] = show["Toplam"].apply(money)
        show.columns = ["Firma", "Şube", "Sipariş", "Toplam"]
        st.dataframe(show, hide_index=True, use_container_width=True)
    with c2:
        st.subheader("Durum Bazlı Sipariş")
        status_report = orders.groupby("status").agg(Sipariş=("id", "count"), Toplam=("total_amount", "sum")).reset_index()
        st.bar_chart(status_report.set_index("status")[["Sipariş"]])

    st.subheader("Ürün Bazlı Satış")
    if items.empty:
        st.info("Ürün kalemi yok.")
    else:
        product_report = items.groupby(["product_name", "model", "color"], dropna=False).agg(
            Adet=("quantity", "sum"), Toplam=("line_total", "sum")
        ).reset_index().sort_values("Toplam", ascending=False)
        product_show = product_report.copy()
        product_show["Toplam"] = product_show["Toplam"].apply(money)
        product_show.columns = ["Ürün", "Model", "Renk", "Adet", "Toplam"]
        st.dataframe(product_show, hide_index=True, use_container_width=True)

    st.subheader("Excel Dışa Aktar")
    orders_export = orders.copy()
    items_export = items.copy()
    excel_bytes = to_excel_bytes({"Siparişler": orders_export, "Kalemler": items_export, "Firma Raporu": firm_report})
    st.download_button(
        "Raporları Excel indir",
        data=excel_bytes,
        file_name=f"gundays_home_rapor_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def page_backup():
    st.markdown("<div class='gh-title'>Yedek / Ayarlar</div>", unsafe_allow_html=True)
    st.subheader("Veritabanı yedeği")
    if DB_PATH.exists():
        st.download_button(
            "SQLite veritabanı yedeğini indir",
            data=DB_PATH.read_bytes(),
            file_name=f"gundays_home_db_yedek_{date.today().isoformat()}.db",
            mime="application/octet-stream",
            use_container_width=True,
        )
    else:
        st.info("Veritabanı henüz oluşmadı.")

    st.divider()
    st.subheader("Şifre değiştir")
    with st.form("change_pass"):
        current = st.text_input("Mevcut şifre", type="password")
        new_pass = st.text_input("Yeni şifre", type="password")
        new_pass2 = st.text_input("Yeni şifre tekrar", type="password")
        submitted = st.form_submit_button("Şifreyi değiştir", type="primary")
    if submitted:
        username = st.session_state.get("username")
        user = query_one("SELECT * FROM users WHERE username = ?", (username,))
        if not user or not verify_password(current, user["password_salt"], user["password_hash"]):
            st.error("Mevcut şifre hatalı.")
        elif len(new_pass) < 6:
            st.error("Yeni şifre en az 6 karakter olmalı.")
        elif new_pass != new_pass2:
            st.error("Yeni şifreler eşleşmiyor.")
        else:
            salt, digest = hash_password(new_pass)
            execute("UPDATE users SET password_salt=?, password_hash=? WHERE username=?", (salt, digest, username))
            st.success("Şifre değiştirildi.")

# -----------------------------
# App shell
# -----------------------------

init_db()
require_login()

with st.sidebar:
    st.markdown("## Günday's Home")
    st.caption(f"Kullanıcı: {st.session_state.get('username')} / {st.session_state.get('role')}")
    page = st.radio(
        "Menü",
        ["Dashboard", "Yeni Sipariş", "Siparişler", "Firmalar", "Ürünler", "Raporlar", "Yedek / Ayarlar"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Çıkış yap", use_container_width=True):
        st.session_state.clear()
        st.rerun()

if page == "Dashboard":
    page_dashboard()
elif page == "Yeni Sipariş":
    page_new_order()
elif page == "Siparişler":
    page_orders()
elif page == "Firmalar":
    page_firms()
elif page == "Ürünler":
    page_products()
elif page == "Raporlar":
    page_reports()
elif page == "Yedek / Ayarlar":
    page_backup()
