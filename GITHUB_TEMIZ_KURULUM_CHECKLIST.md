# Temiz GitHub Kurulum Checklist

## 1) Repo temizliği

GitHub reposunda eski karışmış dosyaları sil:

```text
src/
gsheets_db.py
download
service_account.json
.streamlit/secrets.toml
```

## 2) Yeni dosyaları yükle

Bu paketteki dosyaları repo köküne yükle:

```text
streamlit_app.py
app.py
requirements.txt
runtime.txt
README.md
SHEET_SCHEMA.md
secrets.example.toml
.streamlit/config.toml
tools/setup_sheet.py
templates/google_sheets_template.xlsx
.gitignore
```

## 3) Streamlit Cloud

Main file path:

```text
streamlit_app.py
```

## 4) Secrets

Servis hesabı JSON dosyasını GitHub'a yükleme. İçeriğini TOML formatında Streamlit Cloud > Settings > Secrets alanına gir.

## 5) Google Sheet

Sheet'i service account `client_email` adresine Düzenleyici olarak paylaş.

## 6) İlk uygulama açılışı

Uygulamada sol menü:

```text
Sheet Kurulum > Sheet yapısını oluştur / onar
```

Bu işlem sekmeleri ve 1. satır başlıklarını sabitler.
