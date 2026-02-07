# Tokopedia Review Scraper & Sentiment Analysis (XGBoost)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![ML Framework](https://img.shields.io/badge/ML-XGBoost-orange)](https://xgboost.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Proyek ini merupakan implementasi *end-to-end* analisis sentimen ulasan produk Tokopedia. Mulai dari pengambilan data (*scraping*), pra-pemrosesan teks bahasa Indonesia, seleksi fitur, hingga klasifikasi menggunakan algoritma **XGBoost** dengan perbandingan tiga skenario eksperimen.

## 📌 Fitur Utama
- **Automated Scraping**: Mengambil data ulasan dari Tokopedia menggunakan Selenium & BeautifulSoup.
- **Indonesian NLP Pipeline**: Pembersihan data, *case folding*, filtering, hingga *stemming* menggunakan Sastrawi.
- **Tiga Skenario Eksperimen**:
  - **Skenario 1**: Baseline (TF-IDF + XGBoost).
  - **Skenario 2**: Seleksi Fitur (Grid Search + XGBoost).
  - **Skenario 3**: Penanganan Imbalance Data (SMOTE + Chi-Square + Grid Search +  XGBoost).
- **Model Persistence**: Model disimpan dalam format `.pkl` untuk digunakan kembali tanpa melatih ulang.

## 📂 Struktur Repositori
```text
├── data/                  # Koleksi dataset (Raw, Clean, Balanced) dan pkl files
├── models/                # Hasil training model (.pkl) untuk tiap skenario
├── src/
│   ├── mining/            # Script untuk scraping data Tokopedia
│   ├── flow_1/            # Implementasi eksperimen skenario 1
│   ├── flow_2/            # Implementasi eksperimen skenario 2
│   ├── flow_3/            # Implementasi eksperimen skenario 3 (SMOTE & Pipeline)
│   └── utils/             # Helper fungsi (preprocessing, visualisasi, TF-IDF)
├── requirements.txt       # Daftar library Python yang dibutuhkan
└── grafik_perbandingan.png # Hasil visualisasi performa model
