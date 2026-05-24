import pandas as pd
import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# 1. Load Data
df = pd.read_csv('robust_data/dataset/final_updated_dataset.csv')

# Hapus baris yang tidak memiliki teks ulasan sama sekali pada data mentah
df = df.dropna(subset=['Review'])

# 2. Siapkan Stemmer & Stopword Remover
print("Inisialisasi library Sastrawi...")
factory_stem = StemmerFactory()
stemmer = factory_stem.create_stemmer()

factory_stop = StopWordRemoverFactory()
stopword = factory_stop.create_stop_word_remover()

# 3. Fungsi Full Preprocessing
def full_preprocessing(text):
    # Pastikan teks berformat string
    text = str(text)
    
    text = text.lower()
    
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    text = stopword.remove(text)
    
    text = stemmer.stem(text)
    
    return text

print("Sedang memproses Cleansing, Case Folding, Stopword, & Stemming...")
print("Proses ini memakan waktu cukup lama karena stemming pada Sastrawi memproses kata per kata.")

df['Cleaned_Review'] = df['Review'].apply(full_preprocessing)

df = df[df['Cleaned_Review'].str.strip() != '']
df = df.dropna(subset=['Cleaned_Review'])

df.to_csv('robust_data/dataset/dataset_fix_preprocessed.csv', index=False)
print("Selesai! File tersimpan sebagai 'robust_data/dataset/dataset_fix_preprocessed.csv'")