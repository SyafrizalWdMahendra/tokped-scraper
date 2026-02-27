import pandas as pd

# 1. Load data
df = pd.read_csv('new_final_dataset.csv')

# 2. Pisahkan tiap kelas
df_pos = df[df['Sentiment'] == 'positif']
df_neg = df[df['Sentiment'] == 'negatif']
df_net = df[df['Sentiment'] == 'netral']

# 3. Hitung target (Jumlah Negatif + Netral)
target_count = len(df_neg) + len(df_net) # Hasilnya 1622

# 4. Ambil sampel acak dari kelas positif sebanyak target_count
df_pos_trimmed = df_pos.sample(n=target_count, random_state=42)

# 5. Gabungkan kembali semua data
df_final = pd.concat([df_pos_trimmed, df_neg, df_net])

# 6. Acak urutan data agar tidak mengumpul
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

# Simpan hasil
df_final.to_csv('trimmed_sentiment_dataset.csv', index=False)