import pandas as pd

# 1. Baca kedua file
df_lama = pd.read_csv('dataset_fix.csv')      # File yang isinya positif semua
# File hasil scrap filter bintang 1-3
df_baru = pd.read_csv('dataset_fix_balanced.csv')

# 2. Cek Kolom (Wajib Sama Persis)
print("Kolom File Lama:", df_lama.columns.tolist())
print("Kolom File Baru:", df_baru.columns.tolist())

# 3. Gabungkan (Concatenate)
# ignore_index=True penting agar nomor baris diurutkan ulang dari 0 sampai selesai
df_gabungan = pd.concat([df_lama, df_baru], ignore_index=True)

# 4. (Opsional tapi Bagus) Acak Urutan Data
# Biar data positif tidak mengumpul di atas dan negatif di bawah
# Ini bagus saat nanti proses splitting data train/test
df_gabungan = df_gabungan.sample(frac=1).reset_index(drop=True)

# 5. Cek Komposisi Akhir
print("\n=== Komposisi Data Final ===")
print(df_gabungan['Sentiment'].value_counts())

# 6. Simpan jadi Master Dataset
df_gabungan.to_csv('MASTER_DATASET_FINAL.csv', index=False)
print("Sukses! File tersimpan sebagai MASTER_DATASET_FINAL.csv")
