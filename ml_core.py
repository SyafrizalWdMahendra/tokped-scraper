import sys
import joblib
import numpy as np
from typing import List
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import config

model_optimized = None 
vectorizer = None
label_encoder = None
stemmer = None
stopword = None

def load_ml_assets():
    """Fungsi ini dipanggil sekali saat server menyala"""
    global model_optimized, vectorizer, label_encoder, stemmer, stopword
    
    print("🧠 Memuat modul NLP Sastrawi...")
    stemmer = StemmerFactory().create_stemmer()
    stopword = StopWordRemoverFactory().create_stop_word_remover()

    print("🧠 Memuat model Machine Learning...")
    try:
        vectorizer = joblib.load(config.TOKENIZE_DIR / "vectorizer_tfidf.pkl")
        label_encoder = joblib.load(config.TOKENIZE_DIR / "label_encoder.pkl")
        
        model_path = config.MODEL_DIR / "pipeline_scenario3.pkl"
        if model_path.exists():
            model_optimized = joblib.load(model_path)
            print("✅ Model ML Loaded Successfully")
        else:
            print(f"❌ CRITICAL: Model tidak ditemukan di {model_path}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error memuat aset ML: {e}")
        sys.exit(1)

def preprocess_text(text: str) -> str:
    text = text.lower()
    text = stopword.remove(text)
    text = stemmer.stem(text)
    return text

def extract_keywords_batch(texts: List[str], top_n=5) -> List[str]:
    try:
        combined_text = " ".join(texts)
        if not combined_text: return []
        
        tfidf_matrix = vectorizer.transform([combined_text])
        feature_names = vectorizer.get_feature_names_out()
        
        indices = np.argsort(tfidf_matrix.toarray()).flatten()[::-1]
        top_indices = indices[:top_n]
        
        return [feature_names[i] for i in top_indices]
    except Exception:
        return []