import re
from connection import prisma
from prisma.enums import Sentiment
from schemas import ProductCandidate, ProductAnalysisResult
import config
import ml_core

def clean_product_name(name: str) -> str:
    name = re.sub(r'【.*?】', '', name)
    return name.strip()

async def process_product_reviews(candidate: ProductCandidate, profession: str, user_email: str):
    keywords_target = config.PROFESSION_KEYWORDS.get(profession.lower(), [])
    print(f"🔍 Analisis untuk {candidate.name[:20]}... | Profesi: {profession}")

    model_db = await prisma.model.find_first(where={"modelName": "Model XGBoost (Baseline)"})
    if not model_db:
        print("❌ ERROR: Model tidak ditemukan di DB!")
        return None
    
    product_db = await prisma.product.find_first(where={"url": candidate.url})
    if not product_db:
        cleaned_name = clean_product_name(candidate.name) if candidate.name else "Unknown"
        guessed_brand = clean_product_name(candidate.name.split()[0]) if candidate.name else "Unknown"

        product_db = await prisma.product.create(
            data={
                "name": cleaned_name,
                "url": candidate.url,
                "brand": guessed_brand,
            }
        )

    total_reviews = len(candidate.reviews)
    if total_reviews == 0: return None

    pos_count, neg_count = 0, 0
    profession_relevant_count, profession_pos_score = 0, 0      
    positive_reviews_text = [] 
    reviews_data_to_save = [] 

    user_db = await prisma.user.find_unique(where={"email": user_email})
    if not user_db:
        print(f"⚠️ User {user_email} tidak ditemukan!")
        return None
    
    # 2. NLP PREDICTION LOOP
    for raw_text in candidate.reviews:
        clean_text = ml_core.preprocess_text(raw_text) 
        original_lower = raw_text.lower()      
        
        vec = ml_core.vectorizer.transform([clean_text])
        pred_idx = ml_core.model_optimized.predict(vec)[0]
        label = ml_core.label_encoder.inverse_transform([pred_idx])[0].lower()
        
        try:
            confidence_score = float(max(ml_core.model_optimized.predict_proba(vec)[0]))
        except:
            confidence_score = 1.0

        is_positive = (label == "positif")
        if is_positive:
            pos_count += 1
            positive_reviews_text.append(clean_text)
        elif label == "negatif":
            neg_count += 1
            
        # Keyword Matching Logic
        matched_keywords = [k for k in keywords_target if k in clean_text or k in original_lower]
        
        if matched_keywords:
            profession_relevant_count += 1
            if is_positive:
                profession_pos_score += 1.2 if len(matched_keywords) > 1 else 1

        # Siapkan data untuk DB Batch Insert
        sentiment_enum_map = {"positif": Sentiment.POSITIVE, "negatif": Sentiment.NEGATIVE}
        prisma_sentiment = sentiment_enum_map.get(label, Sentiment.NEUTRAL)

        reviews_data_to_save.append({
            "content": raw_text,
            "sentiment": prisma_sentiment,
            "confidenceScore": confidence_score,
            "keywords": matched_keywords,
            "productId": product_db.id,
            "modelId": model_db.id,
            "userId": user_db.id
        })

    # 3. DATABASE BATCH INSERT
    if reviews_data_to_save:
        try:
            await prisma.review.delete_many(where={"productId": product_db.id})
            await prisma.review.create_many(data=reviews_data_to_save)
        except Exception as e:
            print(f"❌ Gagal menyimpan review: {e}")

    # 4. SCORING & VERDICT
    general_score = (pos_count / total_reviews) * 100
    
    if profession_relevant_count > 0:
        comp_score = min((profession_pos_score / profession_relevant_count) * 100, 100.0)
    else:
        comp_score = general_score * 0.85 

    if comp_score > 85: verdict = "Sangat Cocok"
    elif comp_score > 65: verdict = "Cocok"
    elif comp_score > 40: verdict = "Cukup"
    else: verdict = "Kurang Disarankan"

    top_kwd = ml_core.extract_keywords_batch(positive_reviews_text, top_n=5)

    if user_db:
        try:
            await prisma.analysis.create(data={
                "targetProfession": profession, "generalSentiment": round(general_score, 1),
                "compatibilityScore": round(comp_score, 1), "verdict": verdict,
                "topKeywords": top_kwd, "userId": user_db.id,
                "productId": product_db.id, "modelId": model_db.id
            })
        except Exception as e:
            print(f"❌ Gagal menyimpan data Analysis: {e}")

    return ProductAnalysisResult(
        name=candidate.name, url=candidate.url, general_sentiment_score=round(general_score, 1),
        profession_compatibility_score=round(comp_score, 1), total_reviews=total_reviews,
        positive_count=pos_count, negative_count=neg_count, top_keywords=top_kwd, verdict=verdict
    )