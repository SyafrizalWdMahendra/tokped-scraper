from pydantic import BaseModel
from typing import List

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