# Google Sheets Şema Dosyası

Aşağıdaki sekme adları ve kolonlar birebir kullanılmalıdır.

## Dashboard

```text
Metrik | Deger | Aciklama
```

## Firmalar

```text
Firma_ID | Firma_Adi | Yetkili | Telefon | Email | Adres | Il | Ilce | Vergi_Dairesi | VKN_TCKN | Durum | Kayit_Tarihi | Not
```

## Urunler

```text
Urun_ID | Urun_Adi | Kategori | Renk | Birim | Birim_Fiyat | KDV_Orani | Durum | Stok_Kodu | Not
```

## Siparisler

```text
Siparis_ID | Tarih | Firma_ID | Firma_Adi | Durum | Teslim_Tarihi | Sevk_Adresi | Ara_Toplam | KDV_Tutari | Genel_Toplam | Odenen | Kalan | Odeme_Durumu | Not | Olusturma_Tarihi
```

## Siparis_Kalemleri

```text
Kalem_ID | Siparis_ID | Urun_ID | Urun_Adi | Miktar | Birim_Fiyat | KDV_Orani | Ara_Toplam | KDV_Tutari | Satir_Toplami | Not
```

## Odemeler

```text
Odeme_ID | Tarih | Siparis_ID | Firma_ID | Firma_Adi | Odeme_Tipi | Tutar | Aciklama
```

## Listeler

```text
Durum_Tipleri | Odeme_Tipleri | Urun_Kategorileri | Birimler
```

## Kullanim

```text
Tarih | Islem | Kullanici | Detay
```

## Kullanicilar

```text
Kullanici_ID | Ad_Soyad | Email | Rol | Durum
```
