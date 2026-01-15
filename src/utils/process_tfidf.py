import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

# ==========================================
# KONFIGURASI
# ==========================================
file_train = 'data/train/data_train_80.csv'
file_test = 'data/test/data_test_20.csv'
col_text = 'Cleaned_Review'  # Pastikan nama kolom teks sesuai
col_label = 'Sentiment'      # Pastikan nama kolom label sesuai

print("--- MEMULAI PROSES TF-IDF ---")

# 1. Load Data
try:
    print(f"1. Membaca file {file_train} dan {file_test}...")
    df_train = pd.read_csv(file_train)
    df_test = pd.read_csv(file_test)
    
    # Handling NaN (Jaga-jaga jika ada text kosong setelah preprocessing)
    df_train[col_text] = df_train[col_text].fillna('')
    df_test[col_text] = df_test[col_text].fillna('')

    print(f"   - Data Latih: {df_train.shape}")
    print(f"   - Data Uji: {df_test.shape}")

    # 2. Label Encoding (Ubah Positif/Negatif/Netral jadi 0, 1, 2)
    # XGBoost mewajibkan target berupa angka
    print("\n2. Melakukan Label Encoding pada target...")
    le = LabelEncoder()
    
    # Fit pada train, transform pada train & test
    y_train = le.fit_transform(df_train[col_label])
    y_test = le.transform(df_test[col_label])
    
    # Tampilkan mapping agar tidak bingung nanti
    mapping = dict(zip(le.classes_, le.transform(le.classes_)))
    print(f"   - Mapping Label: {mapping}")

    # 3. TF-IDF Vectorization
    print("\n3. Melakukan TF-IDF Vectorization...")
    # Anda bisa mengatur max_features jika laptop lemot (misal: max_features=3000)
    # Default dibiarkan All Features untuk akurasi maksimal skripsi
    tfidf = TfidfVectorizer() 

    # PENTING: Fit hanya di Train, Test hanya Transform (Mencegah Data Leakage)
    X_train_tfidf = tfidf.fit_transform(df_train[col_text])
    X_test_tfidf = tfidf.transform(df_test[col_text])

    print(f"   - Dimensi Fitur Train: {X_train_tfidf.shape}")
    print(f"   - Dimensi Fitur Test:  {X_test_tfidf.shape}")

    # 4. Simpan Hasil (Pickle/Joblib)
    # Kita simpan objek sparse matrix agar hemat memori & cepat diload
    print("\n4. Menyimpan file output...")
    
    # Simpan Fitur (X)
    joblib.dump(X_train_tfidf, 'X_train_tfidf.pkl')
    joblib.dump(X_test_tfidf, 'X_test_tfidf.pkl')
    
    # Simpan Target (y)
    joblib.dump(y_train, 'y_train.pkl')
    joblib.dump(y_test, 'y_test.pkl')
    
    # Simpan Objek Vectorizer & Encoder (Penting untuk prediksi nanti)
    joblib.dump(tfidf, 'vectorizer_tfidf.pkl')
    joblib.dump(le, 'label_encoder.pkl')

    print("="*40)
    print("SUKSES! File output tersimpan:")
    print("1. X_train_tfidf.pkl & y_train.pkl (Siap untuk SMOTE)")
    print("2. X_test_tfidf.pkl & y_test.pkl   (Siap untuk Evaluasi)")
    print("3. vectorizer_tfidf.pkl            (Simpan untuk skripsi)")
    print("="*40)

except FileNotFoundError:
    print("ERROR: File CSV tidak ditemukan. Pastikan 'data_train_80.csv' dan 'data_test_20.csv' ada di folder ini.")
except KeyError as e:
    print(f"ERROR: Kolom tidak ditemukan: {e}. Cek nama kolom di CSV Anda.")