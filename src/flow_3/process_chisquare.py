import joblib
import os
from sklearn.feature_selection import SelectKBest, chi2

# ==========================================
# KONFIGURASI
# ==========================================
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Input (Kita butuh Data Train hasil SMOTE dan Data Test asli)
input_X_train = 'data/smote/X_train_smote.pkl'
input_y_train = 'data/smote/y_train_smote.pkl'
input_X_test  = 'data/tokenize/test/X_test_tfidf.pkl' # Test set asli (belum diapa-apakan selain TFIDF)

# Output
output_X_train = 'data/chi2/X_train_chi2.pkl'
output_X_test  = 'data/chi2/X_test_chi2.pkl'
output_selector = 'data/chi2/chisquare_selector.pkl' # Simpan logikanya

# JUMLAH FITUR YANG INGIN DIAMBIL (Parameter K)
# Silakan ubah angka ini. 1000 adalah angka start yang bagus untuk Skripsi S1.
# Jika fitur awal Anda < 1000, ubah jadi 'all' atau angka lebih kecil (misal 500).
K_FEATURES = 1000 

print("--- MEMULAI FEATURE SELECTION (CHI-SQUARE) ---")

try:
    # 1. Load Data
    print("1. Memuat data...")
    # Load Train (SMOTE)
    X_train = joblib.load(os.path.join(base_dir, input_X_train))
    y_train = joblib.load(os.path.join(base_dir, input_y_train))
    
    # Load Test (TF-IDF Asli)
    # Kita butuh ini agar dimensi Test sama dengan Train nanti
    X_test = joblib.load(os.path.join(base_dir, input_X_test))

    print(f"   - Dimensi Awal Train: {X_train.shape}")
    print(f"   - Dimensi Awal Test:  {X_test.shape}")
    
    # Cek jumlah fitur total
    total_features = X_train.shape[1]
    print(f"   - Total kata/fitur saat ini: {total_features}")

    # Validasi K
    if isinstance(K_FEATURES, int) and K_FEATURES > total_features:
        print(f"   ⚠️ WARNING: Target k={K_FEATURES} lebih besar dari total fitur ({total_features}). Mengambil semua fitur.")
        k_final = 'all'
    else:
        k_final = K_FEATURES

    # 2. Proses Chi-Square
    print(f"\n2. Menjalankan Chi-Square (Mengambil Top {k_final} Fitur)...")
    
    # Inisialisasi SelectKBest dengan skor func chi2
    selector = SelectKBest(score_func=chi2, k=k_final)
    
    # FIT hanya pada Data Train! (Pelajari mana kata penting dari data latih)
    selector.fit(X_train, y_train)
    
    # TRANSFORM pada Train DAN Test
    X_train_selected = selector.transform(X_train)
    X_test_selected = selector.transform(X_test)

    # 3. Validasi Hasil
    print("\n3. Hasil Seleksi:")
    print(f"   - Dimensi Train Baru: {X_train_selected.shape}")
    print(f"   - Dimensi Test Baru:  {X_test_selected.shape}")
    
    # Menampilkan beberapa skor fitur (opsional, untuk info saja)
    print("   - Proses seleksi selesai. Dimensi kolom (fitur) telah berkurang.")

    # 4. Simpan Data
    print("\n4. Menyimpan hasil...")
    joblib.dump(X_train_selected, output_X_train)
    joblib.dump(X_test_selected, output_X_test)
    joblib.dump(selector, output_selector) # Penting untuk prediksi data baru nanti
    
    print("="*40)
    print(f"SUKSES! Data siap untuk Training XGBoost.")
    print(f"File Train: {output_X_train}")
    print(f"File Test:  {output_X_test}")
    print("="*40)

except FileNotFoundError as e:
    print(f"ERROR: File tidak ditemukan ({e}). Pastikan script sebelumnya (SMOTE) sukses.")
except Exception as e:
    print(f"ERROR: Terjadi kesalahan: {e}")