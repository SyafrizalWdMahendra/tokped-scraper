import matplotlib.pyplot as plt
import numpy as np

# Data dari hasil eksperimen Anda
scenarios = ['Skenario 1\n(Baseline)', 'Skenario 2\n(Tuned)', 'Skenario 3\n(Full Optimized)']
accuracy = [0.78, 0.79, 0.77]
macro_f1 = [0.65, 0.66, 0.66]
recall_netral = [0.31, 0.33, 0.37]

x = np.arange(len(scenarios))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 6))

# Membuat bar chart
rects1 = ax.bar(x - width, accuracy, width, label='Accuracy', color='#3498db')
rects2 = ax.bar(x, macro_f1, width, label='Macro Avg F1-Score', color='#2ecc71')
rects3 = ax.bar(x + width, recall_netral, width, label='Recall Netral', color='#e74c3c')

# Menambahkan teks dan label
ax.set_ylabel('Scores')
ax.set_title('Perbandingan Performa Model XGBoost antar Skenario')
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend(loc='lower right')
ax.set_ylim(0, 1.0)

# Menambahkan label angka di atas bar
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)

plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()