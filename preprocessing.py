import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# 1. Load Data
df = pd.read_csv('final_dataset.csv')

# Hapus data kosong (ada 6 baris kosong di Cleaned_Review hasil cek tadi)
df = df.dropna(subset=['Cleaned_Review'])

# 2. Siapkan Stemmer & Stopword Remover
factory_stem = StemmerFactory()
stemmer = factory_stem.create_stemmer()

factory_stop = StopWordRemoverFactory()
stopword = factory_stop.create_stop_word_remover()

# 3. Fungsi Preprocessing Lanjutan
def finish_preprocessing(text):
    # a. Stopword Removal
    text = stopword.remove(text)
    # b. Stemming
    text = stemmer.stem(text)
    return text

print("Sedang memproses Stopword & Stemming... (Bisa memakan waktu beberapa menit)")
# Terapkan ke kolom Cleaned_Review
df['Cleaned_Review'] = df['Cleaned_Review'].apply(finish_preprocessing)

# 4. Simpan hasilnya
df.to_csv('dataset_fix_preprocessed.csv', index=False)
print("Selesai! File tersimpan sebagai 'dataset_fix_preprocessed.csv'")