import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. INPUT DATA HASIL EKSPERIMEN
# ==========================================
scenarios = ['Skenario 1\n(Baseline)', 'Skenario 2\n(Tuned)', 'Skenario 3\n(Tuned + SMOTE + Chi-Square)']

# Data Metrik
accuracy   = [0.71, 0.73, 0.73] 
macro_f1   = [0.62, 0.66, 0.67] 
f1_negatif = [0.67, 0.69, 0.68] 
f1_netral  = [0.34, 0.42, 0.45] 
f1_positif = [0.86, 0.86, 0.87] 

# ==========================================
# 2. KONFIGURASI PLOT (Disesuaikan untuk 5 Batang)
# ==========================================
x = np.arange(len(scenarios))  # Label lokasi
width = 0.15  # Lebar batang diperkecil agar 5 batang muat berdampingan

fig, ax = plt.subplots(figsize=(14, 8)) # Ukuran sedikit diperlebar

# Membuat 5 batang dengan offset yang simetris
# Posisi: -2, -1, 0, +1, +2 kali lebar batang
rects1 = ax.bar(x - 2*width, accuracy,   width, label='Accuracy',      color='#d3d3d3', edgecolor='grey')
rects2 = ax.bar(x - 1*width, macro_f1,   width, label='Macro F1-Score', color='#3498db')
rects3 = ax.bar(x + 0*width, f1_negatif, width, label='F1 Negatif',     color='#e74c3c')
rects4 = ax.bar(x + 1*width, f1_netral,  width, label='F1 Netral',      color="#ffd468")
rects5 = ax.bar(x + 2*width, f1_positif, width, label='F1 Positif',     color="#2ecc71") # Hijau Emerald

# ==========================================
# 3. PERCANTIK TAMPILAN
# ==========================================
ax.set_ylabel('Skor (0.0 - 1.0)', fontsize=12, fontweight='bold')
ax.set_title('Perbandingan Performa Model per Skenario', fontsize=14, pad=20, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=11)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, fontsize=10) # Legend diletakkan di bawah agar rapi
ax.set_ylim(0, 1.1) 
ax.grid(axis='y', linestyle='--', alpha=0.3)

# Fungsi otomatis memberi label angka di atas batang
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 5),  
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)
autolabel(rects5)

# ==========================================
# 4. SIMPAN HASIL
# ==========================================
plt.tight_layout()
filename = 'final_grafik_perbandingan_skripsi.png'
plt.savefig(filename, dpi=300, bbox_inches='tight') 
print(f"✅ Grafik berhasil disimpan sebagai: {filename}")
plt.show()