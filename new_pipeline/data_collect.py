import pandas as pd
import numpy as np

# Muat dataset (ganti path sesuai file Anda)
df = pd.read_csv('robust_data/dataset/trimmed_sentiment_dataset.csv')

# Tampilkan ukuran dataset
print(f"Shape: {df.shape}")

# Preview 5 baris pertama
print(df.head())

# Ringkasan tipe data dan nilai kosong
print(df.info())

# Statistik deskriptif
print(df.describe(include='all'))
