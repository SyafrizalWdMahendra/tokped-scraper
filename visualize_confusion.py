import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import confusion_matrix

# Data Confusion Matrix dari Skenario 3 (Pipeline + SMOTE)
# Baris: Aktual, Kolom: Prediksi
data_cm = np.array([
    [146, 34, 19],  # Aktual Negatif
    [60, 36, 28],   # Aktual Netral
    [29, 16, 280]   # Aktual Positif
])

# Label kategori
labels = ['Negatif', 'Netral', 'Positif']

# Membuat plot
plt.figure(figsize=(8, 6))
sns.set(font_scale=1.2) # Mengatur ukuran font

# Membuat heatmap
ax = sns.heatmap(data_cm, annot=True, fmt='d', cmap='Blues', 
                 xticklabels=labels, yticklabels=labels)

# Menambahkan label dan judul
plt.xlabel('Prediksi', fontsize=14, labelpad=15)
plt.ylabel('Aktual', fontsize=14, labelpad=15)
plt.title('Confusion Matrix Skenario 1 (Baseline)', fontsize=16, pad=20)

# Menampilkan plot
plt.show()