# Gündays Home Sipariş Sistemi

Google Sheets + Streamlit tabanlı web sipariş takip uygulaması.

## En önemli düzeltme

Streamlit Cloud logunda görünen hata şuydu:

```text
The main module file does not exist: /mount/src/gundays-home-siparis/streamlit_app.py
```

Bu pakette artık repo kökünde **streamlit_app.py** var. Streamlit Cloud'da main module/path olarak şunu seç:

```text
streamlit_app.py
```

İstersen `app.py` de bırakıldı; ama Streamlit Cloud şu an `streamlit_app.py` aradığı için bu dosya kesin bulunacak.

## Dosya yapısı

```text
.
├── streamlit_app.py
├── app.py
├── requirements.txt
├── runtime.txt
├── README.md
├── secrets.example.toml
├── .gitignore
├── .streamlit/
│   └── config.toml
└── src/
    ├── __init__.py
    └── gsheets_db.py
```

## GitHub'a yüklenecek dosyalar

Bu klasörün içindeki dosyaları repo köküne yükle. Yani GitHub'da dosyalar şu şekilde görünmeli:

```text
gundays-home-siparis/streamlit_app.py
gundays-home-siparis/requirements.txt
gundays-home-siparis/src/gsheets_db.py
```

Şu şekilde iç içe klasör olmasın:

```text
gundays-home-siparis/gundays-home-siparis-fixed/streamlit_app.py
```

## Streamlit Cloud ayarı

1. Streamlit Cloud uygulamasına gir.
2. Settings > General bölümünde main file/path:

```text
streamlit_app.py
```

3. Settings > Secrets bölümüne servis hesabı TOML içeriğini yapıştır.
4. Google Sheet'i servis hesabı e-postasıyla **Düzenleyici** olarak paylaş.
5. App'i reboot/restart et.

## Sheet ID

Kod varsayılan olarak bu Google Sheet'e bağlıdır:

```text
1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk
```

Secrets içine ayrıca şu değer de eklenir:

```toml
SPREADSHEET_ID = "1nOIO-sodcXTx1v-dp1Do9Zj-mev6O5rbYkyT204m-Vk"
```

## Beklenen sekmeler

Uygulama şu sekmelerle çalışır:

- Dashboard
- Firmalar
- Urunler
- Siparisler
- Siparis_Kalemleri
- Odemeler
- Listeler
- Kullanim
- Kullanicilar

## Ana kolonlar

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

## Uygulama özellikleri

- Dashboard ciro, tahsilat, açık bakiye ve sipariş sayısı gösterir.
- Yeni sipariş oluşturur.
- Bir siparişe birden çok ürün kalemi ekler.
- Sipariş kalemlerini `Siparis_Kalemleri` sekmesine yazar.
- Sipariş ana kaydını `Siparisler` sekmesine yazar.
- Ödeme girişi yapar.
- Ödeme sonrası siparişin ödeme durumunu otomatik günceller.
- Firma ekler.
- Ürün ekler.
- Ayarlar sayfasında bağlantı ve kolon kontrolü yapar.
- Kayıt sonrası Streamlit cache temizler, böylece Sheet'e yazılan veri uygulamada görünür.

## Kolon eşleşmesi

Kod başlıkları toleranslı eşleştirir. Örneğin aşağıdakiler aynı kabul edilir:

```text
Firma_ID / firma_id / Firma ID
Firma Adı / firma_adi / firma adi
Sipariş ID / siparis_id / siparis id
Ürün Adı / urun_adi / ürün adı
```

## Lokal çalıştırma

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp secrets.example.toml .streamlit/secrets.toml
streamlit run streamlit_app.py
```

Lokal çalıştırırken gerçek servis hesabı bilgilerini `.streamlit/secrets.toml` içine koy.

## GitHub'a asla yükleme

Aşağıdakileri GitHub'a koyma:

- Google servis hesabı `.json` dosyası
- `.streamlit/secrets.toml`
- `streamlit_cloud_secrets...toml` benzeri gerçek anahtar içeren dosyalar

Bunlar sadece Streamlit Cloud > Secrets alanına girilmeli.
