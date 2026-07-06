"""
Opsiyonel kurulum aracı.

Kullanım:
1) Google service account JSON dosyanı bu dosyanın yanında GEÇİCİ olarak service_account.json adıyla tut.
2) Terminalde çalıştır:
   python tools/setup_sheet.py
3) İş bitince service_account.json dosyasını sil. GitHub'a yükleme.
"""

from __future__ import annotations

import json
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
MAX_ROWS = 10000

SCHEMA = {
    "Dashboard": ["Metrik", "Deger", "Aciklama"],
    "Firmalar": ["Firma_ID", "Firma_Adi", "Yetkili", "Telefon", "Email", "Adres", "Il", "Ilce", "Vergi_Dairesi", "VKN_TCKN", "Durum", "Kayit_Tarihi", "Not"],
    "Urunler": ["Urun_ID", "Urun_Adi", "Kategori", "Renk", "Birim", "Birim_Fiyat", "KDV_Orani", "Durum", "Stok_Kodu", "Not"],
    "Siparisler": ["Siparis_ID", "Tarih", "Firma_ID", "Firma_Adi", "Durum", "Teslim_Tarihi", "Sevk_Adresi", "Ara_Toplam", "KDV_Tutari", "Genel_Toplam", "Odenen", "Kalan", "Odeme_Durumu", "Not", "Olusturma_Tarihi"],
    "Siparis_Kalemleri": ["Kalem_ID", "Siparis_ID", "Urun_ID", "Urun_Adi", "Miktar", "Birim_Fiyat", "KDV_Orani", "Ara_Toplam", "KDV_Tutari", "Satir_Toplami", "Not"],
    "Odemeler": ["Odeme_ID", "Tarih", "Siparis_ID", "Firma_ID", "Firma_Adi", "Odeme_Tipi", "Tutar", "Aciklama"],
    "Listeler": ["Durum_Tipleri", "Odeme_Tipleri", "Urun_Kategorileri", "Birimler"],
    "Kullanim": ["Tarih", "Islem", "Kullanici", "Detay"],
    "Kullanicilar": ["Kullanici_ID", "Ad_Soyad", "Email", "Rol", "Durum"],
}

DEFAULT_LIST_ROWS = [
    ["Hazırlanıyor", "Nakit", "Dilsiz Uşak", "Adet"],
    ["Onaylandı", "Havale/EFT", "Mobilya", "Takım"],
    ["Üretimde", "Kredi Kartı", "Aksesuar", "Paket"],
    ["Sevke Hazır", "Çek/Senet", "Diğer", "Koli"],
    ["Teslim Edildi", "Diğer", "", "Metre"],
    ["İptal", "", "", "Kg"],
]


def col_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def main() -> None:
    json_path = Path(__file__).with_name("service_account.json")
    if not json_path.exists():
        raise FileNotFoundError(f"Bulunamadı: {json_path}")

    info = json.loads(json_path.read_text(encoding="utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    ss = client.open_by_key(SPREADSHEET_ID)

    existing = {ws.title: ws for ws in ss.worksheets()}
    for sheet_name, headers in SCHEMA.items():
        if sheet_name not in existing:
            ws = ss.add_worksheet(title=sheet_name, rows=MAX_ROWS, cols=max(26, len(headers)))
            print(f"Oluşturuldu: {sheet_name}")
        else:
            ws = existing[sheet_name]
            print(f"Bulundu: {sheet_name}")
        end_col = col_letter(len(headers))
        ws.update(f"A1:{end_col}1", [headers], value_input_option="USER_ENTERED")
        if sheet_name == "Listeler":
            current = ws.get("A2:D20")
            if not any(any(str(cell).strip() for cell in row) for row in current):
                ws.update("A2:D7", DEFAULT_LIST_ROWS, value_input_option="USER_ENTERED")

    print("Sheet yapısı hazır.")


if __name__ == "__main__":
    main()
