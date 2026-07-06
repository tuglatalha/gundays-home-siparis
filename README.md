# Gündays Home Sipariş Takip Sistemi - V4

Bu sürüm tek dosyalı ve Streamlit Cloud için hazırlanmıştır.

## Ana dosya

Streamlit Cloud > Main file path:

```text
streamlit_app.py
```

## GitHub kök dizini şöyle olmalı

```text
streamlit_app.py
app.py
requirements.txt
runtime.txt
README.md
secrets.example.toml
.streamlit/config.toml
.gitignore
```

Eski dosyaları sil:

```text
src/
gsheets_db.py
download
service_account.json
.streamlit/secrets.toml
```

## Google Sheets kurulum

Uygulama açıldıktan sonra sol menüden:

```text
Sheet Kurulum > Sheet yapısını oluştur / onar
```

Bu işlem eksik sekmeleri oluşturur, 1. satıra doğru başlıkları yazar ve mevcut kayıtları silmez.

## Beklenen sekmeler

- Dashboard
- Firmalar
- Urunler
- Siparisler
- Siparis_Kalemleri
- Odemeler
- Listeler
- Kullanim
- Kullanicilar

## Önemli

Google service account JSON dosyasını GitHub'a yükleme. Streamlit Cloud > Settings > Secrets alanına TOML formatında ekle.
