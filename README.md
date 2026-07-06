# Günday's Home Sipariş Takip - Streamlit MVP

Bu proje Günday's Home için web tabanlı sipariş takip panelidir. PC ve mobil tarayıcıdan kullanılabilir.

## Özellikler

- Admin giriş ekranı
- Firma / müşteri kartları
- Ürün kartları
- Yeni sipariş oluşturma
- Siparişe birden fazla ürün kalemi ekleme
- Sipariş durumu ve ödeme durumu güncelleme
- Dashboard metrikleri
- Firma ve ürün bazlı raporlar
- Excel rapor indirme
- SQLite veritabanı yedeği indirme
- Mobil uyumlu arayüz

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Tarayıcıda açılır:

```text
http://localhost:8501
```

İlk giriş:

```text
Kullanıcı adı: admin
Şifre: admin123
```

Giriş yaptıktan sonra **Yedek / Ayarlar > Şifre değiştir** bölümünden şifreyi değiştir.

## Streamlit Cloud'a yükleme

1. GitHub'da yeni bir repo oluştur.
2. Bu klasördeki dosyaları repoya yükle:
   - `streamlit_app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `README.md`
3. Streamlit Cloud'da `Create app` / `New app` seç.
4. GitHub reposunu seç.
5. Main file path alanına şunu yaz:

```text
streamlit_app.py
```

6. App URL alanında istediğin kısa adı kullan:

```text
gundayssiparistakip
```

7. Deploy butonuna bas.

## Önemli not

Bu MVP sürüm SQLite dosyasıyla çalışır. Bilgisayarda kullanım için uygundur. Streamlit Cloud'da test ve düşük yoğunluklu kullanım için çalışır; ancak kalıcı ve profesyonel veri saklama için sonraki sürümde Supabase, Neon PostgreSQL veya Google Sheets bağlantısı önerilir.

