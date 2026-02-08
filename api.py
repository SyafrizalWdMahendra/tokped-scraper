import sys
import joblib
import asyncio
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from prisma import Prisma
from prisma.enums import Sentiment
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# ==========================================
# 1. KONFIGURASI
# ==========================================
app = FastAPI(title="Tokopedia Sentiment Analysis API")
prisma = Prisma()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TOKENIZE_DIR = DATA_DIR / "tokenize"

models = {}
vectorizer = None
label_encoder = None
stemmer = None
stopword = None

SENTIMENT_MAP_RAW = {
    "positif": "positive",
    "negatif": "negative",
    "netral": "neutral"
}

MODEL_ID_MAP = {
    "baseline": 1,
    "tuned": 2,
    "optimized": 3
}

class SentimentRequest(BaseModel):
    laptop_name: str
    review_text: str
    model_type: str

class SentimentResponse(BaseModel):
    sentiment: str
    confidenceScore: float
    model_used: str
    keywords: list[str]

# ==========================================
# 2. LOADERS & UTILS
# ==========================================
@app.on_event("startup")
async def startup_event():
    global models, vectorizer, label_encoder, stemmer, stopword, prisma
    
    print("⏳ Connecting to Database & Loading Models...")
    await prisma.connect()

    stemmer = StemmerFactory().create_stemmer()
    stopword = StopWordRemoverFactory().create_stop_word_remover()

    try:
        vectorizer = joblib.load(TOKENIZE_DIR / "vectorizer_tfidf.pkl")
        label_encoder = joblib.load(TOKENIZE_DIR / "label_encoder.pkl")
        print("✅ Vectorizer & Label Encoder Loaded")
    except FileNotFoundError:
        print("❌ CRITICAL: File pickle tidak ditemukan")
        sys.exit(1)

    model_files = {
        "baseline": MODEL_DIR / "xgboost_scenario1.pkl",
        "tuned": MODEL_DIR / "xgboost_scenario2.pkl",
        "optimized": MODEL_DIR / "pipeline_scenario3.pkl"
    }

    for key, path in model_files.items():
        if path.exists():
            models[key] = joblib.load(path)
            print(f"✅ Model '{key}' loaded")
        else:
            print(f"⚠️ Model '{key}' not found at {path}")

@app.on_event("shutdown")
async def shutdown_event():
    await prisma.disconnect()

def preprocess_text(text: str) -> str:
    text = text.lower()
    text = stopword.remove(text)
    text = stemmer.stem(text)
    return text

def extract_keywords(text: str, vectorizer_model, top_n=5) -> list:
    try:
        tfidf_matrix = vectorizer_model.transform([text])
        
        if hasattr(vectorizer_model, 'get_feature_names_out'):
            feature_names = vectorizer_model.get_feature_names_out()
        else:
            feature_names = vectorizer_model.get_feature_names()

        feature_index = tfidf_matrix.nonzero()[1]
        word_scores = []
        for idx in feature_index:
            word_scores.append((feature_names[idx], tfidf_matrix[0, idx]))
        
        word_scores.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in word_scores[:top_n]]
    except Exception as e:
        print(f"⚠️ Gagal extract keywords: {e}")
        return []

def get_valid_sentiment_enum(sentiment_str: str):
    target = sentiment_str.lower()
    for member in Sentiment:
        if member.name.lower() == target:
            return member
    return sentiment_str.upper()

async def save_to_db(laptop_name: str, content: str, sentiment_en: str, score: float, keywords: list, model_id: int):
    try:
        # 1. Cari atau Buat Product
        product = await prisma.product.find_first(where={"name": laptop_name})
        if not product:
            print(f"🆕 Membuat produk baru: {laptop_name}")
            extracted_brand = laptop_name.split()[0] if laptop_name else "Generic"
            product = await prisma.product.create(
                data={"name": laptop_name, "brand": extracted_brand}
            )

        # 2. Resolve Enum
        final_enum = get_valid_sentiment_enum(sentiment_en)

        # 3. Simpan Review dengan Model Relation
        await prisma.review.create(
            data={
                "productId": product.id,
                "modelId": model_id,
                "content": content,
                "sentiment": final_enum,
                "confidenceScore": score,
                "keywords": keywords
            }
        )
        print(f"📝 Saved: {laptop_name} | {final_enum} | Model ID: {model_id}")

    except Exception as e:
        print(f"❌ Database Error: {e}")

# ==========================================
# 3. ENDPOINT
# ==========================================
@app.post("/predict", response_model=SentimentResponse)
async def predict_sentiment(request: SentimentRequest, background_tasks: BackgroundTasks):
    
    # A. Normalisasi Input Model Key
    # Mapping input user yang panjang ke key sederhana ("baseline", "tuned", "optimized")
    input_key_map = {
        "model xgboost (baseline)": "baseline",
        "model xgboost (tuned)": "tuned",
        "model xgboost (optimized)": "optimized"
    }
    # Ambil key sederhana (misal: "optimized")
    simple_key = input_key_map.get(request.model_type.lower(), request.model_type.lower())

    # Validasi keberadaan model di memori
    if simple_key not in models:
        raise HTTPException(status_code=400, detail=f"Model '{request.model_type}' tidak tersedia.")
    
    selected_model = models[simple_key]

    db_model_id = MODEL_ID_MAP.get(simple_key, 1) 

    try:
        # B. Proses NLP
        clean_text = preprocess_text(request.review_text)
        tfidf_vec = vectorizer.transform([clean_text])
        extracted_keywords = extract_keywords(clean_text, vectorizer, top_n=5)

        # C. Prediksi
        pred_idx = selected_model.predict(tfidf_vec)[0]
        proba = selected_model.predict_proba(tfidf_vec)[0]
        
        raw_label = label_encoder.inverse_transform([pred_idx])[0]
        final_sentiment = SENTIMENT_MAP_RAW.get(raw_label.lower(), raw_label.lower())
        confidence_score = float(max(proba))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")

    background_tasks.add_task(
        save_to_db,
        request.laptop_name,
        request.review_text,
        final_sentiment,
        confidence_score,
        extracted_keywords,
        db_model_id
    )

    return {
        "sentiment": final_sentiment,
        "confidenceScore": round(confidence_score, 2),
        "model_used": simple_key, 
        "keywords": extracted_keywords
    }