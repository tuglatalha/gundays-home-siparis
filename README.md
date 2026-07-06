# Günday's Cari Takip - Streamlit

Google Sheets'i veri merkezi gibi kullanan cari takip paneli.

## Özellikler

- Dashboard: toplam satış, tahsilat, açık cari, firma bazlı bakiye
- Satış girişi: cari, ürün, adet, fiyat, tahsilat, vade ve not
- Tahsilat girişi: firmaya ödeme/tahsilat işleme
- Cari detay: firma bazlı hareket dökümü ve notlar
- Notlar: cari notu, vade hatırlatma, problem ve sevkiyat notu
- Raporlar: tarih, cari ve ürün bazlı filtreleme + CSV indirme
- Yönetim: yeni firma ve ürün ekleme

## Bağlı Google Sheet

Varsayılan spreadsheet ID:

```text
1vIWF8SNBxS1pt47bmnvmsbxh0r-4q-5HweIkIDT0aZw
```

Uygulama şu sayfalarla çalışır:

- `CARI_HAREKETLER`
- `FIRMALAR`
- `URUNLER`
- `AYARLAR`
- `CARI_NOTLARI`

Eksik kolon varsa uygulama otomatik olarak başlık satırına ekler.

## Lokal kurulum

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

`.streamlit/secrets.toml.template` dosyasını kopyala:

```bash
copy .streamlit\secrets.toml.template .streamlit\secrets.toml
```

Sonra `secrets.toml` içine Google servis hesabı JSON bilgilerini gir.

Çalıştır:

```bash
streamlit run app.py
```

## Streamlit Cloud kurulumu

1. Bu klasörü GitHub reposuna yükle.
2. `secrets.toml` dosyasını GitHub'a yükleme.
3. Streamlit Cloud'da uygulamayı deploy et.
4. App > Settings > Secrets alanına `secrets.toml` içeriğini yapıştır.
5. Google Sheet'i servis hesabı e-posta adresiyle **Düzenleyici** olarak paylaş.

## Güvenlik

Servis hesabı private key bilgisini kimseyle paylaşma. GitHub'a yükleme. `.gitignore` bu dosyayı özellikle dışarıda bırakır.
