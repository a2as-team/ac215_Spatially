"""
Pydantic Models for NER Service API

Request and response models for type safety and validation.
"""
from typing import List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Health status of the service")


class ReadyResponse(BaseModel):
    """Readiness check response"""
    status: str = Field(..., description="Readiness status")
    model_loaded: bool = Field(..., description="Whether NER model is loaded")


class ArticleReferenceRequest(BaseModel):
    """Request model for article reference extraction"""
    text: str = Field(..., description="Input text to extract article references from", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "According to Article 50, Section 32 of the zoning code, this development requires special permits."
            }
        }


class ArticleReferenceResponse(BaseModel):
    """Response model for article reference extraction"""
    article_references: List[str] = Field(
        ...,
        description="List of unique article references found in the text"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "article_references": ["Article 50", "Section 32"]
            }
        }
