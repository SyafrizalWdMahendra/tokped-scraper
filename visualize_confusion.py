import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import confusion_matrix

data_cm = np.array([
    [146, 34, 19],  
    [60, 36, 28],   
    [29, 16, 280]   
])

labels = ['Negatif', 'Netral', 'Positif']

plt.figure(figsize=(8, 6))
sns.set(font_scale=1.2) 

ax = sns.heatmap(data_cm, annot=True, fmt='d', cmap='Blues', 
                 xticklabels=labels, yticklabels=labels)

plt.xlabel('Prediksi', fontsize=14, labelpad=15)
plt.ylabel('Aktual', fontsize=14, labelpad=15)
plt.title('Confusion Matrix Skenario 1 (Baseline)', fontsize=16, pad=20)

plt.show()