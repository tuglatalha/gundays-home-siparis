# Gündays Home Sipariş Takip Sistemi

Bu sürüm Streamlit Cloud için tek dosya mantığıyla hazırlanmıştır. Ana dosya `streamlit_app.py` dosyasıdır. `src` klasörü gerektirmez.

## Kurulum

1. Bu klasördeki dosyaları GitHub reposunun köküne yükleyin.
2. Streamlit Cloud uygulamasında **Main file path** değerini `streamlit_app.py` yapın.
3. Streamlit Cloud > Settings > Secrets bölümüne servis hesabı TOML bilgisini yapıştırın.
4. Google Sheet dosyasını servis hesabı e-postasına Düzenleyici olarak paylaşın.
5. Uygulamayı reboot edin.

## Dosya yapısı

```text
streamlit_app.py
app.py
requirements.txt
runtime.txt
secrets.example.toml
.streamlit/config.toml
.gitignore
```

## Önemli

Servis hesabı JSON/private key dosyasını GitHub'a yüklemeyin. Sadece Streamlit Secrets alanına ekleyin.
