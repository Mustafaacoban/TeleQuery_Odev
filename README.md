# TeleQuery API v2.0

Telekomünikasyon müşteri ve abonelik yönetim sistemi.

## Kurulum

```bash
pip install -r requirements.txt
```

## Çalıştırma

```bash
uvicorn app.main:app --reload
```

API dokümantasyonu: http://localhost:8000/docs

## Veritabanını Doldurma

```bash
python seeder.py          # 1000 kayıt (varsayılan)
python seeder.py 500      # 500 kayıt
```

## Testleri Çalıştırma

```bash
pytest tests/ -v
```

## Proje Yapısı

```
tele_query/
├── app/
│   ├── main.py           # FastAPI uygulama başlangıcı
│   ├── database.py       # SQLite bağlantı yönetimi
│   ├── models.py         # Pydantic request/response şemaları
│   └── routers/
│       ├── regions.py    # Bölge endpoint'leri
│       ├── packages.py   # Paket endpoint'leri
│       ├── customers.py  # Müşteri endpoint'leri
│       └── subscriptions.py  # Abonelik endpoint'leri
├── tests/
│   └── test_api.py       # 20+ entegrasyon testi
├── seeder.py             # Gerçekçi test verisi üreteci
├── .env.example          # Ortam değişkenleri şablonu
└── requirements.txt
```

## Endpoint'ler

| Method | URL | Açıklama |
|--------|-----|----------|
| GET | /regions/ | Tüm bölgeler |
| POST | /regions/ | Yeni bölge ekle |
| DELETE | /regions/{id} | Bölge sil |
| GET | /packages/ | Tüm paketler |
| POST | /packages/ | Yeni paket ekle |
| PATCH | /packages/{id} | Paket güncelle |
| DELETE | /packages/{id} | Paket sil |
| GET | /customers/ | Müşteri listesi (filtrelenebilir) |
| POST | /customers/ | Yeni müşteri ekle |
| GET | /customers/{id} | Tek müşteri |
| PATCH | /customers/{id} | Müşteri güncelle |
| DELETE | /customers/{id} | Müşteri sil |
| GET | /customers/{id}/subscriptions | Müşteri abonelikleri |
| GET | /subscriptions/ | Abonelik listesi |
| POST | /subscriptions/ | Yeni abonelik |
| PATCH | /subscriptions/{id} | Abonelik durumu güncelle |
| GET | /subscriptions/stats/by-package | Paket bazında istatistik |
| GET | /subscriptions/stats/by-region | Bölge bazında istatistik |
