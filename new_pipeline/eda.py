import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = pd.read_csv('robust_data/dataset/trimmed_sentiment_dataset.csv')

# Nama kolom target (sesuaikan)
target_col = 'label'

# 1. Distribusi kelas (deteksi imbalance)
print("Distribusi kelas:")
print(df[target_col].value_counts())
print(df[target_col].value_counts(normalize=True) * 100)

df[target_col].value_counts().plot(kind='bar', title='Distribusi Kelas')
plt.tight_layout()
plt.show()

# 2. Cek nilai hilang
missing = df.isnull().sum()
print("\nNilai hilang per kolom:")
print(missing[missing > 0])

# 3. Distribusi fitur numerik
num_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
df[num_cols].hist(bins=20, figsize=(14, 8))
plt.suptitle('Distribusi Fitur Numerik')
plt.tight_layout()
plt.show()

# 4. Boxplot untuk deteksi outlier
for col in num_cols[:6]:  # tampilkan 6 pertama
    plt.figure(figsize=(6, 3))
    sns.boxplot(x=df[col])
    plt.title(f'Boxplot: {col}')
    plt.show()