import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer

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

# Pisahkan fitur dan target
X = df.drop(columns=[target_col])
y = df[target_col].copy()

# Identifikasi kolom berdasarkan tipe
cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
num_cols = X.select_dtypes(include=['int64', 'float64']).columns.tolist()

# 1. Imputasi nilai hilang
imp_num = SimpleImputer(strategy='median')   # numerik: median (robust outlier)
imp_cat = SimpleImputer(strategy='most_frequent')  # kategorik: modus

X[num_cols] = imp_num.fit_transform(X[num_cols])
X[cat_cols] = imp_cat.fit_transform(X[cat_cols])

# 2. Label encoding kolom kategorik
le_dict = {}
for col in cat_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    le_dict[col] = le  # simpan untuk inverse transform nanti

# 3. Encode target jika berupa string
if y.dtype == 'object':
    le_target = LabelEncoder()
    y = le_target.fit_transform(y)

print(f"Fitur setelah preprocessing: {X.shape}")
print(X.head())