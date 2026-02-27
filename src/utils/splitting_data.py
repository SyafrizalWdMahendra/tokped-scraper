import pandas as pd
from sklearn.model_selection import train_test_split

# 1. Load Data
# Pastikan nama file sesuai dengan file gabungan terakhir Anda
nama_file = 'trimmed_sentiment_dataset.csv' 
print(f"--- Membaca file: {nama_file} ---")

try:
    df = pd.read_csv(nama_file)
    print(f"Total data awal: {len(df)} baris")
    
    # Cek nama kolom sentimen (sesuaikan jika di csv Anda namanya beda, misal 'label' atau 'sentiment')
    # Di sini saya asumsikan namanya 'Sentiment' berdasarkan output Anda sebelumnya
    col_sentiment = 'Sentiment' 
    
    # 2. Hapus Duplikat (Wajib dilakukan lagi untuk memastikan keamanan)
    df_clean = df.drop_duplicates()
    print(f"Total data setelah hapus duplikat: {len(df_clean)} baris")
    
    # 3. Lakukan Splitting 80:20 dengan Stratify
    # random_state=42 dikunci agar hasil acakannya SELALU SAMA setiap kali dirun
    # stratify=df_clean[col_sentiment] memastikan rasio Pos/Neg/Netral sama di train & test
    train, test = train_test_split(
        df_clean, 
        test_size=0.2, 
        stratify=df_clean[col_sentiment], 
        random_state=42
    )
    
    print("\n" + "="*30)
    print("HASIL SPLITTING (80:20)")
    print("="*30)
    
    # 4. Validasi Distribusi Data
    print(f"\n[DATA LATIH / TRAIN] - Akan di-SMOTE & Grid Search ({len(train)} baris):")
    print(train[col_sentiment].value_counts())
    print(f"Proporsi Latih: {len(train)/len(df_clean):.2%}")

    print(f"\n[DATA UJI / TEST] - Disimpan untuk Validasi Akhir ({len(test)} baris):")
    print(test[col_sentiment].value_counts())
    print(f"Proporsi Uji: {len(test)/len(df_clean):.2%}")
    
    train.to_csv('data_train_80.csv', index=False)
    test.to_csv('data_test_20.csv', index=False)
    
    print("\n" + "="*30)
    print("SUKSES! Dua file telah dibuat:")
    print("1. data_train_80.csv (Untuk Skenario 1, 2, 3)")
    print("2. data_test_20.csv (JANGAN DISENTUH sampai tahap evaluasi akhir)")
    print("="*30)

except FileNotFoundError:
    print(f"Error: File '{nama_file}' tidak ditemukan. Pastikan lokasinya benar.")
except KeyError:
    print(f"Error: Kolom '{col_sentiment}' tidak ditemukan. Cek nama kolom di CSV Anda.")