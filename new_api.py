import sys
import joblib
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from prisma import Prisma
from prisma.enums import Sentiment
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

app = FastAPI(title="Tokopedia Laptop Recommendation API (Profession Based)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prisma = Prisma()

# ==========================================
# 1. CONFIG & PATHS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TOKENIZE_DIR = DATA_DIR / "tokenize"

# Global Variables
model_optimized = None 
vectorizer = None
label_encoder = None
stemmer = None
stopword = None

PROFESSION_KEYWORDS = {
    "programmer": [
        # Core Tech
        "keyboard", "ketik", "ngetik", "tuts", "travel", "pencet", # Keyboard penting buat koding
        "ram", "memory", "memori", "multitasking", "buka banyak", "chrome", # RAM
        "layar", "screen", "monitor", "mata", "jernih", "tajam", # Layar buat baca kode
        "cepat", "kencang", "kenceng", "ngebut", "sat set", "lancar", # Performa
        "ssd", "booting", "nyala", "loading", # Storage
        "coding", "koding", "code", "program", "docker", "virtual", "wsl", "linux", # Dev terms
        "panas", "adem", "dingin", "fan", "kipas", # Suhu
        "kerja", "work", "kantor", "tugas" # General usage
    ],
    "designer": [
        "warna", "color", "srgb", "akurat", "gonjreng", "pucat", # Warna
        "layar", "screen", "panel", "ips", "oled", "resolusi", "pixel", # Display
        "render", "rendering", "export", "gpu", "vga", "grafis", # Performance
        "adobe", "photoshop", "illustrator", "premiere", "corel", "canva", # Apps
        "berat", "ringan", "bawa", "tas", # Portability (sering mobile)
        "baterai", "awet", "tahan lama" 
    ],
    "student": [
        "baterai", "awet", "tahan", "cas", "charge", # Battery life
        "ringan", "enteng", "tipis", "bawa", # Portability
        "kamera", "cam", "webcam", "zoom", "meet", "gmeet", "teams", # Meeting
        "murah", "harga", "budget", "kantong", "worth", # Price
        "ngetik", "tugas", "skripsi", "makalah", "word", "excel", "office", # Usage
        "speaker", "suara", "mic"
    ],
    "gamer": [
        "fps", "frame", "rata kanan", "smooth", "patah", "drop", # Performance
        "panas", "overheat", "hangat", "kipas", "berisik", "cooling", "adem", # Thermal
        "vga", "gpu", "rtx", "gtx", "radeon", "nvidia", # Specs
        "layar", "hz", "hertz", "refresh", "ms", # Display
        "game", "gaming", "main", "valorant", "dota", "genshin", "pubg" # Games
    ],
}

SENTIMENT_MAP_RAW = {
    "positif": "positive",
    "negatif": "negative",
    "netral": "neutral"
}

# ==========================================
# 2. DATA MODELS (INPUT/OUTPUT)
# ==========================================
class ProductCandidate(BaseModel):
    name: str
    url: str
    reviews: List[str] 

class RecommendationRequest(BaseModel):
    user_email: str
    profession: str 
    candidates: List[ProductCandidate]

class ProductAnalysisResult(BaseModel):
    name: str
    url: str
    general_sentiment_score: float 
    profession_compatibility_score: float 
    total_reviews: int
    positive_count: int
    negative_count: int
    top_keywords: List[str]
    verdict: str  

class ComparisonResponse(BaseModel):
    user_email: str
    profession_target: str
    winning_product: str
    details: List[ProductAnalysisResult]

# ==========================================
# 3. UTILS & LOADERS
# ==========================================
@app.on_event("startup")
async def startup_event():
    global model_optimized, vectorizer, label_encoder, stemmer, stopword, prisma
    
    print("⏳ Connecting to Database & Loading Optimized Model...")
    await prisma.connect()

    stemmer = StemmerFactory().create_stemmer()
    stopword = StopWordRemoverFactory().create_stop_word_remover()

    try:
        # Load Vectorizer
        vectorizer = joblib.load(TOKENIZE_DIR / "vectorizer_tfidf.pkl")
        label_encoder = joblib.load(TOKENIZE_DIR / "label_encoder.pkl")
        
        # LOAD ONLY OPTIMIZED MODEL
        model_path = MODEL_DIR / "pipeline_scenario3.pkl"
        if model_path.exists():
            model_optimized = joblib.load(model_path)
            print("✅ Model 'Optimized' (Scenario 3) Loaded Successfully")
        else:
            print(f"❌ CRITICAL: Model optimized not found at {model_path}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error loading assets: {e}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    await prisma.disconnect()

def preprocess_text(text: str) -> str:
    text = text.lower()
    text = stopword.remove(text)
    text = stemmer.stem(text)
    return text

def extract_keywords_batch(texts: List[str], vectorizer_model, top_n=5) -> List[str]:
    """Mengambil keyword paling sering muncul dari kumpulan review positif"""
    try:
        combined_text = " ".join(texts)
        if not combined_text: return []
        
        tfidf_matrix = vectorizer_model.transform([combined_text])
        feature_names = vectorizer_model.get_feature_names_out()
        
        indices = np.argsort(tfidf_matrix.toarray()).flatten()[::-1]
        top_indices = indices[:top_n]
        
        return [feature_names[i] for i in top_indices]
    except:
        return []

# ==========================================
# 4. CORE LOGIC (WEIGHTED ANALYSIS)
# ==========================================
async def process_product_reviews(candidate: ProductCandidate, profession: str, user_email: str):
    keywords_target = PROFESSION_KEYWORDS.get(profession.lower(), [])
    
    print(f"🔍 Analisis untuk {candidate.name[:20]}... | Profesi: {profession} | Target Keywords: {len(keywords_target)}")

    # ==========================================
    # 1. DATABASE FETCHING & CREATION (PRODUCT & MODEL)
    # ==========================================
    model_db = await prisma.model.find_first(
        where={"modelName": "Model XGBoost (Baseline)"}
    )
    if not model_db:
        print("❌ ERROR: Model tidak ditemukan di DB!")
        return None
    model_id = model_db.id

    product_db = await prisma.product.find_first(
        where={"url": candidate.url}
    )

    if product_db:
        print(f"📦 Produk ditemukan di DB: {product_db.name}")
    else:
        guessed_brand = candidate.name.split()[0] if candidate.name else "Unknown"
        
        product_db = await prisma.product.create(
            data={
                "name": candidate.name,
                "url": candidate.url,
                "brand": guessed_brand 
            }
        )
        print(f"➕ Produk BARU berhasil dibuat di DB: {product_db.name}")

    processed_reviews = []
    positive_reviews_text = [] 
    reviews_data_to_save = [] 
    
    total_reviews = len(candidate.reviews)
    if total_reviews == 0:
        return None

    pos_count = 0
    neg_count = 0
    profession_relevant_count = 0 
    profession_pos_score = 0      

    # ==========================================
    # 2. PROSES NLP & PREDIKSI (LOOP REVIEW)
    # ==========================================
    for raw_text in candidate.reviews:
        clean_text = preprocess_text(raw_text) 
        original_lower = raw_text.lower()      
        
        vec = vectorizer.transform([clean_text])
        pred_idx = model_optimized.predict(vec)[0]
        label = label_encoder.inverse_transform([pred_idx])[0].lower()
        
        try:
            probas = model_optimized.predict_proba(vec)[0]
            confidence_score = float(max(probas))
        except:
            confidence_score = 1.0

        is_positive = label == "positif"
        
        if is_positive:
            pos_count += 1
            positive_reviews_text.append(clean_text)
        elif label == "negatif":
            neg_count += 1
            
        matched_keywords = []
        for k in keywords_target:
            if k in clean_text or k in original_lower:
                matched_keywords.append(k)
        
        if len(matched_keywords) > 0:
            profession_relevant_count += 1
            if is_positive:
                profession_pos_score += 1
                if len(matched_keywords) > 1:
                    profession_pos_score += 0.2 

        if product_db:
            sentiment_enum_map = {
                "positif": Sentiment.POSITIVE,
                "negatif": Sentiment.NEGATIVE,
                "netral": Sentiment.NEUTRAL
            }
            prisma_sentiment = sentiment_enum_map.get(label, Sentiment.NEUTRAL)

            reviews_data_to_save.append({
                "content": raw_text,
                "sentiment": prisma_sentiment,
                "confidenceScore": confidence_score,
                "keywords": matched_keywords,
                "productId": product_db.id,
                "modelId": model_id
            })

    if reviews_data_to_save and product_db:
        try:
            await prisma.review.delete_many(where={"productId": product_db.id})
            await prisma.review.create_many(data=reviews_data_to_save)
            print(f"✅ Tersimpan {len(reviews_data_to_save)} review ke DB.")
        except Exception as e:
            print(f"❌ Gagal menyimpan review: {e}")

    general_score = (pos_count / total_reviews) * 100
    
    if profession_relevant_count > 0:
        raw_comp_score = (profession_pos_score / profession_relevant_count) * 100
        comp_score = min(raw_comp_score, 100.0)
    else:
        comp_score = general_score * 0.85 

    if comp_score > 85: verdict = "Sangat Cocok"
    elif comp_score > 65: verdict = "Cocok"
    elif comp_score > 40: verdict = "Cukup"
    else: verdict = "Kurang Disarankan"

    top_kwd = extract_keywords_batch(positive_reviews_text, vectorizer, top_n=5)

    user_db = await prisma.user.find_unique(
        where={"email": user_email}
    )
    if not user_db:
        print(f"⚠️ Peringatan: User dengan email {user_email} tidak ditemukan. Riwayat tidak disimpan.")
    else:
        try:
            await prisma.analysis.create(
                data={
                    "targetProfession": profession,
                    "generalSentiment": round(general_score, 1),
                    "compatibilityScore": round(comp_score, 1),
                    "verdict": verdict,
                    "topKeywords": top_kwd, 
                    "userId": user_db.id,
                    "productId": product_db.id,
                    "modelId": model_id
                }
            )
            print(f"📊 Riwayat Analisis berhasil disimpan untuk {candidate.name[:15]}!")
        except Exception as e:
            print(f"❌ Gagal menyimpan data ke tabel Analysis: {e}")

    return ProductAnalysisResult(
        name=candidate.name,
        url=candidate.url,
        general_sentiment_score=round(general_score, 1),
        profession_compatibility_score=round(comp_score, 1),
        total_reviews=total_reviews,
        positive_count=pos_count,
        negative_count=neg_count,
        top_keywords=top_kwd,
        verdict=verdict
    )

# ==========================================
# 5. ENDPOINT UTAMA
# ==========================================
@app.post("/recommend", response_model=ComparisonResponse)
async def recommend_laptop(request: RecommendationRequest):
    """
    Menerima list produk dan profesi beserta email user.
    Mengembalikan hasil analisis komparasi.
    """
    if not model_optimized:
        raise HTTPException(status_code=500, detail="Model belum siap.")

    results = []
    
    # Proses setiap kandidat produk dengan melempar user_email
    for candidate in request.candidates:
        result = await process_product_reviews(candidate, request.profession, request.user_email)
        if result:
            results.append(result)

    if not results:
        raise HTTPException(status_code=400, detail="Tidak ada review yang valid untuk diproses.")

    # Tentukan Pemenang (Berdasarkan Compatibility Score tertinggi)
    sorted_results = sorted(results, key=lambda x: x.profession_compatibility_score, reverse=True)
    winner = sorted_results[0]

    return {
        "user_email": request.user_email,
        "profession_target": request.profession,
        "winning_product": winner.name,
        "details": results
    }