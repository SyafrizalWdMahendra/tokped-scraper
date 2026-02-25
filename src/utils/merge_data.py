import pandas as pd

# 1. Baca kedua file
df_lama = pd.read_csv('data/dataset/dataset_fix.csv')    
# File hasil scrap filter bintang 1-3
# df_lama = pd.read_csv('dataset_fix_balanced.csv')
df_baru = pd.read_csv('dataset_fix_balanced.csv')
df_baru_2 = pd.read_csv('dataset_fix_balanced_2.csv')
df_baru_3 = pd.read_csv('dataset_fix_balanced_3.csv')

# 2. Cek Kolom (Wajib Sama Persis)
print("Kolom File Lama:", df_lama.columns.tolist())
print("Kolom File Baru 1:", df_baru.columns.tolist())
print("Kolom File Baru 2:", df_baru_2.columns.tolist())
print("Kolom File Baru 3:", df_baru_3.columns.tolist())

# 3. Gabungkan (Concatenate)
# ignore_index=True penting agar nomor baris diurutkan ulang dari 0 sampai selesai
df_gabungan = pd.concat([df_lama, df_baru, df_baru_2, df_baru_3, ], ignore_index=True)

# 4. (Opsional tapi Bagus) Acak Urutan Data
# Biar data positif tidak mengumpul di atas dan negatif di bawah
# Ini bagus saat nanti proses splitting data train/test
df_gabungan = df_gabungan.sample(frac=1).reset_index(drop=True)

# 5. Cek Komposisi Akhir
print("\n=== Komposisi Data Final ===")
print(df_gabungan['Sentiment'].value_counts())

# 6. Simpan jadi Master Dataset
# df_gabungan.to_csv('final_dataset.csv', index=False)
# print("Sukses! File tersimpan sebagai final_dataset.csv")
df_gabungan.to_csv('new_final_dataset.csv', index=False)
print("Sukses! File tersimpan sebagai new_final_dataset.csv")
