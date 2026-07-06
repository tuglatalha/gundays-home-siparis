# Gündays Home Sipariş Takip Sistemi

Bu paket sıfırdan kurulmuş Streamlit + Google Sheets sipariş takip sistemidir.

## En önemli fark

Eski sürümlerde uygulama her sekme için tekrar tekrar başlık araması yaptığı için Google Sheets API kotasına çarpıyordu. Bu sürümde:

- Ana dosya: `streamlit_app.py`
- `src` klasörü yoktur.
- Google Sheets verisi tek seferde `batch_get` ile okunur.
- Okunan veri 120 saniye cache'lenir.
- Başlıklar sabittir, her açılışta otomatik başlık arama yapılmaz.
- Sheet kurulum/onarma işlemi sadece `Sheet Kurulum` sayfasındaki butonla manuel çalışır.

## GitHub repo kökünde olması gerekenler

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

Şunları yükleme:

```text
service-account.json
*.json
.streamlit/secrets.toml
```

## Streamlit Cloud ayarı

Streamlit Cloud'da main file path:

```text
streamlit_app.py
```

## Secrets kurulumu

Streamlit Cloud > App > Settings > Secrets içine `secrets.example.toml` formatını kullanarak kendi servis hesabı bilgilerini gir.

Örnek başlık:

```toml
SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"""
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

## Google Sheet paylaşımı

Google servis hesabındaki `client_email` adresini Google Sheet'e **Düzenleyici** olarak ekle.

## İlk kurulum sırası

1. GitHub reposunu temizle.
2. Bu paketteki dosyaları repo köküne yükle.
3. Streamlit Cloud'da main file path alanını `streamlit_app.py` yap.
4. Secrets alanına servis hesabı bilgilerini gir.
5. Google Sheet'i servis hesabı e-postasına düzenleyici olarak paylaş.
6. Uygulamayı aç.
7. Sol menüden `Sheet Kurulum` sayfasına gir.
8. `Sheet yapısını oluştur / onar` butonuna bas.
9. `Firmalar` ve `Ürünler` sayfalarından kayıt gir.
10. `Yeni Sipariş` sayfasından sipariş oluştur.

## Google Sheets beklenen sekmeler

- Dashboard
- Firmalar
- Urunler
- Siparisler
- Siparis_Kalemleri
- Odemeler
- Listeler
- Kullanim
- Kullanicilar

Detaylı kolon listesi için `SHEET_SCHEMA.md` dosyasına bak.

## 429 quota hatası gelirse

Google tarafında dakika kotası dolduğunda geçici olarak 429 hatası verir. Bu sürüm bunu azaltmak için tek batch okuma + cache kullanır. Yine de çok hızlı peş peşe refresh yaparsan 1-2 dakika bekleyip tekrar dene.
