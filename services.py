import re
from connection import prisma
from prisma.enums import Sentiment
from schemas import ProductCandidate, ProductAnalysisResult
import config
import ml_core

def clean_product_name(name: str) -> str:
    name = re.sub(r'【.*?】', '', name)
    return name.strip()

async def process_product_reviews(candidate: ProductCandidate, user_email: str):
    # 1. SETUP ASPEK (Initialize score 0 untuk setiap kategori)
    # Categories: performa, layar, baterai, harga
    aspect_stats = {
        aspect: {"positive": 0, "total": 0} 
        for aspect in config.ASPECT_KEYWORDS.keys()
    }
    
    print(f"🔍 Memulai Analisis ABSA: {candidate.name[:30]}...")

    # 2. DATABASE PRE-CHECK (Model & User)
    model_db = await prisma.model.find_first(where={"modelName": "Model XGBoost (Baseline)"})
    if not model_db:
        print("❌ ERROR: Model XGBoost tidak ditemukan di database!")
        return None
        
    user_db = await prisma.user.find_unique(where={"email": user_email})
    if not user_db:
        print(f"⚠️ User {user_email} tidak ditemukan!")
        return None

    # 3. PRODUCT PERSISTENCE
    product_db = await prisma.product.find_first(where={"url": candidate.url})
    if not product_db:
        product_db = await prisma.product.create(
            data={
                "name": clean_product_name(candidate.name),
                "url": candidate.url,
                "brand": clean_product_name(candidate.name.split()[0]) if candidate.name.strip() else "Unknown",
            }
        )

    # 4. NLP PREDICTION & ASPECT TAGGING LOOP
    total_reviews = len(candidate.reviews)
    if total_reviews == 0: return None

    pos_count, neg_count = 0, 0
    reviews_data_to_save = []
    processed_texts_for_kwd = []

    for raw_text in candidate.reviews:
        # Preprocessing & Vectorizing
        clean_text = ml_core.preprocess_text(raw_text) 
        original_lower = raw_text.lower()      
        
        vec = ml_core.vectorizer.transform([clean_text])
        pred_idx = ml_core.model_optimized.predict(vec)[0]
        label = ml_core.label_encoder.inverse_transform([pred_idx])[0].lower()
        
        # Confidence Score dari XGBoost
        try:
            prob = ml_core.model_optimized.predict_proba(vec)[0]
            confidence_score = float(max(prob))
        except:
            confidence_score = 1.0

        is_positive = (label == "positif")
        if is_positive:
            pos_count += 1
            processed_texts_for_kwd.append(clean_text)
        else:
            neg_count += 1

        detected_keywords_from_review = [] 
        
        for aspect, keywords in config.ASPECT_KEYWORDS.items():
            matched_words = [k for k in keywords if k in original_lower or k in clean_text]
            
            if matched_words:
                detected_keywords_from_review.extend(matched_words)
                
                aspect_stats[aspect]["total"] += 1
                if is_positive:
                    aspect_stats[aspect]["positive"] += 1

        final_keywords = list(set(detected_keywords_from_review))

        reviews_data_to_save.append({
            "content": raw_text,
            "sentiment": Sentiment.POSITIVE if is_positive else Sentiment.NEGATIVE,
            "confidenceScore": confidence_score,
            "keywords": final_keywords,  
            "productId": product_db.id,
            "modelId": model_db.id,
            "userId": user_db.id
        })

    # 5. DATABASE SYNC (Batch Operations)
    if reviews_data_to_save:
        await prisma.review.delete_many(where={"productId": product_db.id})
        await prisma.review.create_many(data=reviews_data_to_save)

    # 6. CALCULATION & VERDICT GENERATION
    final_aspect_scores = {}
    for aspect, stat in aspect_stats.items():
        score = (stat["positive"] / stat["total"] * 100) if stat["total"] > 0 else 0
        final_aspect_scores[aspect] = round(score, 1)

    general_sentiment_pct = (pos_count / total_reviews) * 100

    valid_aspects = {k: v for k, v in final_aspect_scores.items() if aspect_stats[k]["total"] > 0}
    
    if valid_aspects:
        best_aspect = max(valid_aspects, key=valid_aspects.get)
        worst_aspect = min(valid_aspects, key=valid_aspects.get)
        
        verdict_summary = f"Produk ini sangat unggul pada aspek {best_aspect.upper()}."
        if valid_aspects[worst_aspect] < 60:
            verdict_summary += f" Namun, pengguna sering mengeluhkan {worst_aspect.upper()}."
    else:
        verdict_summary = "Ulasan umum tidak spesifik membahas aspek teknis tertentu."

    if general_sentiment_pct > 80:
        verdict_label = "Sangat Direkomendasikan"
    elif general_sentiment_pct > 60:
        verdict_label = "Layak Dipertimbangkan"
    else:
        verdict_label = "Kurang Disarankan"

    # 7. SAVE ANALYSIS TO DB
    await prisma.analysis.create(data={
        "targetProfession": "ASPECT_BASED", 
        "generalSentiment": round(general_sentiment_pct, 1),
        "compatibilityScore": round(general_sentiment_pct, 1), 
        "verdict": verdict_label,
        "topKeywords": [verdict_summary], 
        "userId": user_db.id,
        "productId": product_db.id,
        "modelId": model_db.id
    })

    return ProductAnalysisResult(
        name=candidate.name, url=candidate.url, general_score=round(general_sentiment_pct, 1),
        aspect_scores=final_aspect_scores, total_reviews=total_reviews, description=verdict_summary,
        positive_count=pos_count, negative_count=neg_count, verdict=verdict_label
    )