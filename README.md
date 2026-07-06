# Gündays Home Sipariş Takip Sistemi

Google Sheets + Streamlit tabanlı web sipariş takip uygulaması.

## Uygulama ne yapar?

- Google Sheet'teki mevcut sekmeleri okur.
- Yeni sipariş oluşturur.
- Sipariş kalemlerini ayrı `Siparis_Kalemleri` sayfasına işler.
- Firma ve ürün kartı ekler.
- Ödeme kaydı girer.
- Sipariş ödeme durumunu otomatik günceller.
- Ciroyu `Siparis_Kalemleri > satir_toplami` üzerinden hesaplar; kalem yoksa `Siparisler > toplam_tutar` değerine düşer.
- Kaydetme sonrası Streamlit önbelleğini temizler, böylece sheet'e gelen kayıt uygulamaya yansır.
- Başlık satırını ilk 10 satır içinde otomatik tespit eder. Bu yüzden başlık 1. satırda ya da 2. satırda olsa çalışır.

## Beklenen Google Sheet sekmeleri

Uygulama şu sekmelerle çalışır:

- `Dashboard`
- `Firmalar`
- `Urunler`
- `Siparisler`
- `Siparis_Kalemleri`
- `Odemeler`
- `Listeler`
- `Kullanim`
- `Kullanicilar`

Ana kullanılan sekmeler ve kolonlar:

### Firmalar

```text
firma_id, firma_adi, sube, yetkili_kisi, telefon, adres, vergi_dairesi, vkn_tckn, not, durum, eklenme_tarihi
```

### Urunler

```text
urun_id, kategori, urun_adi, model, renk, birim, varsayilan_fiyat, stok, durum, not
```

### Siparisler

```text
siparis_id, siparis_tarihi, teslim_tarihi, firma_id, firma_adi, sube, siparis_durumu, odeme_durumu, sevkiyat_tipi, kargo_firma, takip_no, toplam_tutar, not
```

### Siparis_Kalemleri

```text
kalem_id, siparis_id, urun_id, urun_adi, renk, adet, birim_fiyat, iskonto_orani, satir_toplami, not
```

### Odemeler

```text
odeme_id, siparis_id, firma_id, odeme_tarihi, odeme_tipi, tutar, aciklama, kayit_tarihi
```

> Not: Kod kolon eşleşmesini toleranslı yapar. Örneğin `Firma_ID`, `firma_id`, `Firma ID`, `Firma Adı`, `firma_adi` gibi varyasyonları anlayacak şekilde yazıldı.

## GitHub'a yükleme

1. Bu klasördeki dosyaları GitHub reposuna yükle.
2. Streamlit Cloud'da yeni app oluştur.
3. Main file path olarak `app.py` seç.
4. Secrets alanına servis hesabı bilgilerini ekle.

## Streamlit secrets ayarı

`secrets.example.toml` dosyasındaki içeriği kullan.

Önemli nokta:

```toml
SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
```

Servis hesabı bilgisi şu yapıda olmalı:

```toml
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
```

## Google Sheet paylaşımı

Google Cloud servis hesabındaki `client_email` adresini Google Sheet üzerinde **Düzenleyici** olarak paylaş.

Paylaşmazsan uygulama sheet'i okuyamaz/yazamaz.

## Lokal çalıştırma

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp secrets.example.toml .streamlit/secrets.toml
streamlit run app.py
```

## Sorun çözme

### Firmalar dropdown'da çıkmıyor

- `Firmalar` sekmesinde firma adı dolu olmalı.
- `durum` alanı boş veya `Aktif` olmalı.
- Ayarlar sayfasındaki **Sheet / Kolon Kontrolü** bölümüne bak.

### Ciro 0 görünüyor

- Sipariş kalemlerinde `adet`, `birim_fiyat`, `satir_toplami` alanları dolu olmalı.
- Uygulama ciroyu önce `Siparis_Kalemleri > satir_toplami` üzerinden hesaplar.
- Kalem yoksa `Siparisler > toplam_tutar` değerini kullanır.

### Sheet'e kayıt gidiyor ama uygulamada görünmüyor

- Sol menüdeki **Verileri Yenile** butonuna bas.
- Yeni kayıt formu zaten kayıt sonrası önbelleği temizler.
- Streamlit Cloud cache yüzünden gecikme olursa Ayarlar > Verileri Yenile kullan.

## Dosya yapısı

```text
.
├── app.py
├── requirements.txt
├── README.md
├── secrets.example.toml
├── .gitignore
├── .streamlit/
│   └── config.toml
└── src/
    └── gsheets_db.py
```
