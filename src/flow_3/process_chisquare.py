import joblib
import os
from sklearn.feature_selection import SelectKBest, chi2

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

input_X_train = 'new_X_train_smote.pkl'
input_y_train = 'new_y_train_smote.pkl'
input_X_test  = 'X_test_tfidf.pkl' 

output_X_train = 'X_train_chi2.pkl'
output_X_test  = 'X_test_chi2.pkl'
output_selector = 'chisquare_selector.pkl'

K_FEATURES = 1000 

print("--- MEMULAI FEATURE SELECTION (CHI-SQUARE) ---")

try:
    print("1. Memuat data...")
    X_train = joblib.load(os.path.join(base_dir, input_X_train))
    y_train = joblib.load(os.path.join(base_dir, input_y_train))
    
    X_test = joblib.load(os.path.join(base_dir, input_X_test))

    print(f"   - Dimensi Awal Train: {X_train.shape}")
    print(f"   - Dimensi Awal Test:  {X_test.shape}")
    
    total_features = X_train.shape[1]
    print(f"   - Total kata/fitur saat ini: {total_features}")

    if isinstance(K_FEATURES, int) and K_FEATURES > total_features:
        print(f"   ⚠️ WARNING: Target k={K_FEATURES} lebih besar dari total fitur ({total_features}). Mengambil semua fitur.")
        k_final = 'all'
    else:
        k_final = K_FEATURES

    print(f"\n2. Menjalankan Chi-Square (Mengambil Top {k_final} Fitur)...")
    
    selector = SelectKBest(score_func=chi2, k=k_final)
    
    selector.fit(X_train, y_train)
    
    X_train_selected = selector.transform(X_train)
    X_test_selected = selector.transform(X_test)

    print("\n3. Hasil Seleksi:")
    print(f"   - Dimensi Train Baru: {X_train_selected.shape}")
    print(f"   - Dimensi Test Baru:  {X_test_selected.shape}")
    
    print("   - Proses seleksi selesai. Dimensi kolom (fitur) telah berkurang.")

    print("\n4. Menyimpan hasil...")
    joblib.dump(X_train_selected, output_X_train)
    joblib.dump(X_test_selected, output_X_test)
    joblib.dump(selector, output_selector) 
    
    print("="*40)
    print(f"SUKSES! Data siap untuk Training XGBoost.")
    print(f"File Train: {output_X_train}")
    print(f"File Test:  {output_X_test}")
    print("="*40)

except FileNotFoundError as e:
    print(f"ERROR: File tidak ditemukan ({e}). Pastikan script sebelumnya (SMOTE) sukses.")
except Exception as e:
    print(f"ERROR: Terjadi kesalahan: {e}")