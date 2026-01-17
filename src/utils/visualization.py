import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. INPUT DATA HASIL EKSPERIMEN
# ==========================================
# Masukkan angka hasil run Anda di sini
scenarios = ['Skenario 1\n(Baseline)', 'Skenario 2\n(Tuned)', 'Skenario 3\n(SMOTE + Opt)']

# Data Metrik (Salin dari Classification Report Anda)
accuracy   = [0.80, 0.81, 0.81] # Akurasi Global
macro_f1   = [0.56, 0.58, 0.60] # Keseimbangan Model
f1_negatif = [0.61, 0.65, 0.64] # Kemampuan Deteksi Komplain
f1_netral  = [0.16, 0.17, 0.24] # Kemampuan Deteksi Ambigu

# ==========================================
# 2. KONFIGURASI PLOT
# ==========================================
x = np.arange(len(scenarios))  # Label lokasi
width = 0.2  # Lebar batang

fig, ax = plt.subplots(figsize=(12, 7)) # Ukuran gambar

# Membuat 4 batang untuk setiap skenario
rects1 = ax.bar(x - 1.5*width, accuracy,   width, label='Accuracy',      color='#d3d3d3', edgecolor='grey') # Abu-abu
rects2 = ax.bar(x - 0.5*width, macro_f1,   width, label='Macro F1-Score',color='#3498db') # Biru
rects3 = ax.bar(x + 0.5*width, f1_negatif, width, label='F1 Negatif',    color='#2ecc71') # Hijau
rects4 = ax.bar(x + 1.5*width, f1_netral,  width, label='F1 Netral',     color='#e74c3c') # Merah (Highlight Peningkatan)

# ==========================================
# 3. PERCANTIK TAMPILAN
# ==========================================
ax.set_ylabel('Skor (0.0 - 1.0)', fontsize=12)
ax.set_title('Perbandingan Performa Model XGBoost (Skenario 1 vs 2 vs 3)', fontsize=16, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=12)
ax.legend(loc='upper left', fontsize=11)
ax.set_ylim(0, 1.1) # Batas atas sumbu Y sedikit dilebihkan agar label masuk
ax.grid(axis='y', linestyle='--', alpha=0.5)

# Fungsi otomatis memberi label angka di atas batang
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 5),  # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)

# ==========================================
# 4. SIMPAN HASIL
# ==========================================
plt.tight_layout()
filename = 'grafik_perbandingan_skripsi.png'
plt.savefig(filename, dpi=300) # dpi=300 agar gambar tajam saat dicetak
print(f"✅ Grafik berhasil disimpan sebagai: {filename}")
plt.show()