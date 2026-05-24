from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from connection import prisma
from schemas import ComparisonResponse, RecommendationRequest
import ml_core
import services

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏳ Menghubungkan ke Database Neon...")
    await prisma.connect()
    
    print("🤖 Memuat Asset Machine Learning (XGBoost)...")
    ml_core.load_ml_assets()
    
    yield  
    
    print("🔌 Memutuskan koneksi database...")
    await prisma.disconnect()

app = FastAPI(
    title="Tokopedia Laptop Recommendation API",
    description="Backend analisis sentimen ulasan laptop menggunakan XGBoost - Syafrizal Wd Mahendra",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/recommend", response_model=ComparisonResponse)
async def recommend_laptop(request: Request, data: RecommendationRequest): 
    if not ml_core.model_optimized:
        raise HTTPException(
            status_code=500, 
            detail="Model Machine Learning belum siap atau gagal dimuat."
        )

    results = []
    
    for index, candidate in enumerate(data.candidates):
        if await request.is_disconnected():
            print("🛑 Sinyal Cancel diterima! Menghentikan proses AI.")
            return Response(status_code=204)

        print(f"🔄 Memproses ulasan untuk: {candidate.name}...")
        
        try:
            result = await services.process_product_reviews(
                candidate=candidate, 
                user_email=data.user_email,
                metric_id=data.metric_id,
                brand_id=data.brand_id,
                request=request
            )
            
            if result:
                results.append(result)
                
        except Exception as e:
            print(f"⚠️ Gagal memproses {candidate.name}: {str(e)}")
            continue 

    if not results:
        raise HTTPException(
            status_code=400, 
            detail="Tidak ada ulasan valid yang berhasil dianalisis dari produk yang diberikan."
        )

    try:
        sorted_results = sorted(
            results, 
            key=lambda x: x.general_score if hasattr(x, 'general_score') else x["general_score"], 
            reverse=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengurutkan hasil analisis: {str(e)}")

    winner = sorted_results[0]

    return {
        "user_email": data.user_email,
        "analysis_type": "ASPECT_BASED",
        "winning_product": winner.name if hasattr(winner, 'name') else winner["name"],
        "details": sorted_results,
    }