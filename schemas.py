from pydantic import BaseModel
from typing import List

class ProductCandidate(BaseModel):
    name: str
    url: str
    reviews: List[str] 

class RecommendationRequest(BaseModel):
    user_email: str
    candidates: List[ProductCandidate]

class ProductAnalysisResult(BaseModel):
    name: str
    url: str
    general_score: float
    aspect_scores: dict[str, float]
    total_reviews: int
    positive_count: int
    negative_count: int
    verdict: str
    description: str

class ComparisonResponse(BaseModel):
    user_email: str
    analysis_type: str = "ASPECT_BASED" 
    winning_product: str
    details: List[ProductAnalysisResult]