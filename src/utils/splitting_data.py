import pandas as pd
from sklearn.model_selection import train_test_split

nama_file = 'robust_data/dataset/trimmed_sentiment_dataset.csv' 
col_sentiment = 'Sentiment' 

try:
    df = pd.read_csv(nama_file)
    
    df[col_sentiment] = df[col_sentiment].astype(str).str.strip().str.lower()
    
    print(f"Distribusi data keseluruhan sebelum splitting:")
    print(df[col_sentiment].value_counts())
    print("-" * 30)

    df_clean = df.drop_duplicates().reset_index(drop=True)
    
    train, test = train_test_split(
        df_clean, 
        test_size=0.20, 
        stratify=df_clean[col_sentiment], 
        random_state=42,
        shuffle=True 
    )
    
    print("\n" + "="*35)
    print(f"HASIL SPLITTING AKHIR (Total: {len(df_clean)})")
    print("="*35)

    print(f"\n[1] DATA LATIH (80%) - Total: {len(train)} baris")
    dist_train = train[col_sentiment].value_counts()
    for kelas, jumlah in dist_train.items():
        print(f" - {kelas.upper()}: {jumlah} baris")

    print(f"\n[2] DATA UJI (20%) - Total: {len(test)} baris")
    dist_test = test[col_sentiment].value_counts()
    for kelas, jumlah in dist_test.items():
        print(f" - {kelas.upper()}: {jumlah} baris")
    
    train.to_csv('data_train_80.csv', index=False)
    test.to_csv('data_test_20.csv', index=False)
    print("\nSUKSES: File 'data_train_80.csv' dan 'data_test_20.csv' telah dibuat.")

except Exception as e:
    print(f"Terjadi kesalahan: {e}")