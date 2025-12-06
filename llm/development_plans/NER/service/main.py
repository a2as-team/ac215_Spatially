"""
NER Cloud Run Service - Main Application

FastAPI service for extracting article references from development plan text.
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from service.config import config
from service.models import (
    HealthResponse,
    ReadyResponse,
    ArticleReferenceRequest,
    ArticleReferenceResponse,
)
from service.health import health_checker

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NER Service",
    description="Named Entity Recognition service for extracting article references from development plans",
    version=config.version,
)

# Add CORS middleware for backend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global NER predictor (lazy loading)
_ner_predictor: Optional[object] = None


def get_ner_predictor():
    """
    Get or initialize the NER predictor (singleton pattern with lazy loading).

    This function loads the NER model from GCS on first use and caches it
    for subsequent requests.

    Returns:
        NERPredictor instance

    Raises:
        RuntimeError: If model cannot be loaded
    """
    global _ner_predictor

    if _ner_predictor is not None:
        return _ner_predictor

    try:
        logger.info("Initializing NER predictor (first request)...")

        # Add package to Python path
        package_path = Path(__file__).parent.parent / "package"
        if str(package_path) not in sys.path:
            sys.path.insert(0, str(package_path))

        logger.info(f"Added package path to sys.path: {package_path}")

        # Import NER dependencies
        from predictor.predict import NERPredictor
        from utils.gcp_storage import GCPStorage

        # Validate configuration
        if not config.gcp_project:
            raise RuntimeError("GCP_PROJECT environment variable must be set")

        # Initialize GCS client
        logger.info(f"Initializing GCS client with bucket: {config.finetune_gcs_bucket}")
        storage = GCPStorage(
            gcp_project=config.gcp_project,
            bucket_name=config.finetune_gcs_bucket,
        )

        # Initialize NER predictor (downloads model from GCS if needed)
        logger.info("Loading NER model from GCS...")
        _ner_predictor = NERPredictor(
            gcp_storage=storage,
            gcp_project=config.gcp_project,
            model_gcs_path=config.model_gcs_path,
            tokenizer_gcs_path=config.tokenizer_gcs_path,
            model_bucket=config.finetune_gcs_bucket,
            device="cpu",  # Cloud Run uses CPU
        )

        logger.info("✓ NER model loaded successfully")
        health_checker.mark_model_loaded()

        return _ner_predictor

    except ImportError as e:
        error_msg = f"Failed to import NER dependencies: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    except Exception as e:
        error_msg = f"Failed to load NER model: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for Cloud Run liveness probe.

    Returns HTTP 200 as long as the container is running.
    Cloud Run uses this to determine if the container should be restarted.
    """
    return HealthResponse(status="healthy")


@app.get("/ready", response_model=ReadyResponse, status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness check endpoint for Cloud Run startup probe.

    Returns HTTP 200 only when the NER model is loaded and ready.
    Cloud Run uses this to determine when to start routing traffic.
    """
    is_ready = health_checker.is_ready()
    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        model_loaded=is_ready
    )


@app.post(
    "/extract-article-references",
    response_model=ArticleReferenceResponse,
    status_code=status.HTTP_200_OK
)
async def extract_article_references(request: ArticleReferenceRequest):
    """
    Extract article references from development plan text.

    This endpoint uses the fine-tuned NER model to identify and extract
    article references like "Article 50", "Section 32", etc.

    Args:
        request: ArticleReferenceRequest with text to analyze

    Returns:
        ArticleReferenceResponse with list of unique article references

    Raises:
        HTTPException: 500 if model cannot be loaded or inference fails
    """
    try:
        # Get NER predictor (lazy load on first request)
        predictor = get_ner_predictor()

        # Handle empty input
        if not request.text or not request.text.strip():
            return ArticleReferenceResponse(article_references=[])

        logger.info(f"Processing text of length {len(request.text)}")

        # Extract all entities
        entities = predictor.predict_entities(request.text)

        # Filter for ARTICLE_REFERENCE only
        article_refs = [
            entity["text"]
            for entity in entities
            if entity.get("label") == "ARTICLE_REFERENCE"
        ]

        # Remove duplicates while preserving order
        unique_refs = []
        seen = set()
        for ref in article_refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        logger.info(f"Extracted {len(unique_refs)} unique article references")

        return ArticleReferenceResponse(article_references=unique_refs)

    except Exception as e:
        error_msg = f"Error extracting article references: {e}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.service_name,
        "version": config.version,
        "status": "running",
        "model_loaded": health_checker.is_ready(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.port,
        log_level=config.log_level.lower(),
    )
