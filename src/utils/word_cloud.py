import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os

dataset_path = 'data/dataset/dataset_fix.csv'

def generate_wordclouds():
    if not os.path.exists(dataset_path):
        print(f"Error: File {dataset_path} tidak ditemukan!")
        return

    # Load dataset
    df = pd.read_csv(dataset_path)
    df = df.dropna(subset=['Cleaned_Review'])

    # Pengaturan warna untuk tiap sentimen
    sentiments = {
        'positif': 'Greens',
        'negatif': 'Reds',
        'netral': 'Blues'
    }

    print("Sedang menghasilkan Word Cloud...")

    for sentiment, color in sentiments.items():
        # Menggabungkan semua teks ulasan berdasarkan kategori sentimen
        text = " ".join(review for review in df[df['Sentiment'] == sentiment]['Cleaned_Review'])
        
        if not text.strip():
            print(f"Peringatan: Tidak ada data untuk sentimen {sentiment}")
            continue

        # Membuat objek WordCloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white', 
            colormap=color, 
            max_words=100
        ).generate(text)
        
        # Plotting
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.title(f'Word Cloud - Sentimen {sentiment.capitalize()}', fontsize=15, pad=20)
        plt.axis('off')
        
        # Simpan hasil
        filename = f'wordcloud_{sentiment}.png'
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"✅ Berhasil menyimpan: {filename}")

if __name__ == "__main__":
    generate_wordclouds()