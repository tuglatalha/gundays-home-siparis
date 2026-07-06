# Günday's Home Sipariş Takip - V5 Clean

Bu sürüm Google Sheets tablosundaki bozuk başlıkları, boş satırları ve eski şablon kaymalarını otomatik onaracak şekilde baştan yazıldı.

## Streamlit Secrets

```toml
SPREADSHEET_ID = "GOOGLE_SHEET_ID"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

## İlk giriş
- Kullanıcı adı: `admin`
- Şifre: `admin123`

## Kritik
GitHub'da şu dosyalar kalmamalı:
- `pyproject.toml`
- `uv.lock`
- `.python-version`

Sadece şu dosyalar yeterli:
- `streamlit_app.py`
- `requirements.txt`
- `runtime.txt`
- `README.md`
- `.streamlit/config.toml`
