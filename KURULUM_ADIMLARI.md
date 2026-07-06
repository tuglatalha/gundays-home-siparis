# Kurulum Adımları

## 1. Google Cloud'da servis hesabı oluştur

1. Google Cloud Console'a gir.
2. Yeni proje oluştur veya mevcut projeyi seç.
3. APIs & Services > Library bölümünden şu API'leri aç:
   - Google Sheets API
   - Google Drive API
4. IAM & Admin > Service Accounts bölümüne gir.
5. Yeni service account oluştur.
6. Keys > Add key > Create new key > JSON seç.
7. JSON dosyasını indir.

## 2. Google Sheet'i servis hesabına aç

JSON içinde `client_email` alanı olacak. Örnek:

```text
cari-takip@proje-adi.iam.gserviceaccount.com
```

Google Sheet'te:

1. Sağ üstten Paylaş'a bas.
2. Bu e-postayı ekle.
3. Yetkiyi **Düzenleyici** yap.

## 3. Streamlit secrets gir

`.streamlit/secrets.toml.template` dosyasını `.streamlit/secrets.toml` olarak kopyala.

JSON içindeki değerleri ilgili alanlara yapıştır.

Önemli: `private_key` içinde satır sonları `\n` olarak kalmalı.

## 4. Uygulamayı çalıştır

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 5. Test sırası

1. Dashboard açılıyor mu?
2. Satış Girişi ekranından 1 test kaydı gir.
3. Google Sheet > `CARI_HAREKETLER` sayfasına satır düştü mü kontrol et.
4. Tahsilat Girişi ekranından ödeme gir.
5. Cari Detay ekranında bakiye doğru düşüyor mu kontrol et.
6. Notlar ekranından not gir.
7. Google Sheet > `CARI_NOTLARI` sayfasına satır düştü mü kontrol et.
