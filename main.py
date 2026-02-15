from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from connection import prisma
from schemas import ComparisonResponse, RecommendationRequest
import ml_core
import services

app = FastAPI(title="Tokopedia Laptop Recommendation API (Profession Based)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("⏳ Menghubungkan ke Database...")
    await prisma.connect()
    
    ml_core.load_ml_assets()

@app.on_event("shutdown")
async def shutdown_event():
    print("🔌 Memutuskan koneksi database...")
    await prisma.disconnect()

@app.post("/recommend", response_model=ComparisonResponse)
async def recommend_laptop(request: RecommendationRequest):
    """
    Menerima list produk dan profesi beserta email user.
    Mengembalikan hasil analisis komparasi.
    """
    if not ml_core.model_optimized:
        raise HTTPException(status_code=500, detail="Model Machine Learning belum siap.")

    results = []
    
    for candidate in request.candidates:
        result = await services.process_product_reviews(
            candidate=candidate, 
            profession=request.profession, 
            user_email=request.user_email
        )
        if result:
            results.append(result)

    if not results:
        raise HTTPException(status_code=400, detail="Tidak ada review yang valid untuk diproses.")

    sorted_results = sorted(results, key=lambda x: x.profession_compatibility_score, reverse=True)
    winner = sorted_results[0]

    return {
        "user_email": request.user_email,
        "profession_target": request.profession,
        "winning_product": winner.name,
        "details": results
    }