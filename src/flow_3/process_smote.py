import joblib
import pandas as pd
from imblearn.over_sampling import SMOTE
from collections import Counter
import os

# ==========================================
# KONFIGURASI
# ==========================================
# Gunakan relative path agar aman (sama seperti sebelumnya)
base_dir = os.path.dirname(os.path.abspath(__file__))

# Input files (hasil dari TF-IDF sebelumnya)
input_X = 'X_train_tfidf.pkl'
input_y = 'y_train.pkl'

# Output files (hasil SMOTE)
output_X = 'new_X_train_smote.pkl'
output_y = 'new_y_train_smote.pkl'

print("--- MEMULAI PROSES SMOTE (Skenario 3) ---")

try:
    # 1. Load Data TF-IDF (Data Latih Saja)
    print("1. Memuat data latih TF-IDF...")
    # Cek apakah file ada di folder yang sama atau perlu path khusus
    if os.path.exists(os.path.join(base_dir, input_X)):
        X_train = joblib.load(os.path.join(base_dir, input_X))
        y_train = joblib.load(os.path.join(base_dir, input_y))
    else:
        # Fallback jika file ada di current directory
        X_train = joblib.load(input_X)
        y_train = joblib.load(input_y)

    print(f"   - Dimensi Awal: {X_train.shape}")
    print(f"   - Distribusi Kelas Awal: {Counter(y_train)}")
    # Contoh output: {0: 1964, 1: 485, 2: 303} (tergantung mapping label encoder)

    # 2. Eksekusi SMOTE
    print("\n2. Menjalankan SMOTE (Synthetic Minority Over-sampling)...")
    print("   (Sedang membuat data sintetis untuk kelas minoritas...)")
    
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

    # 3. Validasi Hasil
    print("\n3. Validasi Hasil SMOTE:")
    print(f"   - Dimensi Setelah SMOTE: {X_train_resampled.shape}")
    print(f"   - Distribusi Kelas Baru: {Counter(y_train_resampled)}")
    
    # Pastikan semua kelas jumlahnya sama
    counts = list(Counter(y_train_resampled).values())
    if len(set(counts)) == 1:
        print("   ✅ SUCCESS: Dataset sekarang SEIMBANG!")
    else:
        print("   ⚠️ WARNING: Dataset belum seimbang sempurna.")

    # 4. Simpan Data SMOTE
    print("\n4. Menyimpan data hasil SMOTE...")
    joblib.dump(X_train_resampled, output_X)
    joblib.dump(y_train_resampled, output_y)
    
    print("="*40)
    print(f"File tersimpan: {output_X} & {output_y}")
    print("Siap untuk tahap selanjutnya: Feature Selection (Chi-Square) atau Grid Search!")
    print("="*40)

except FileNotFoundError:
    print("ERROR: File .pkl tidak ditemukan. Pastikan Anda sudah menjalankan 'process_tfidf.py' sebelumnya.")
except Exception as e:
    print(f"ERROR: Terjadi kesalahan: {e}")