"""
Cloud Run NER Service Client

HTTP client for calling the NER service deployed on Cloud Run.
Handles Google Cloud authentication using ID tokens for service-to-service communication.
"""
import asyncio
import httpx
import logging
import os
from typing import List
from google.auth.transport.requests import Request
from google.oauth2 import id_token


logger = logging.getLogger(__name__)


class CloudRunNERClient:
    """
    HTTP client for NER service on Cloud Run.

    Handles authentication using Google Cloud ID tokens for
    authenticated service-to-service communication.
    """

    def __init__(self):
        """
        Initialize Cloud Run NER client.

        Raises:
            ValueError: If NER_SERVICE_URL environment variable is not set
        """
        self.service_url = os.environ.get("NER_SERVICE_URL")
        if not self.service_url:
            raise ValueError("NER_SERVICE_URL environment variable not set")

        # Remove trailing slash
        self.service_url = self.service_url.rstrip("/")

        # HTTP client with timeout and connection limits
        self.client = httpx.AsyncClient(
            timeout=60.0,  # 60 second timeout
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

        logger.info(f"CloudRunNERClient initialized with URL: {self.service_url}")

    def _get_id_token(self) -> str:
        """
        Get Google Cloud ID token for service authentication.

        Cloud Run services require ID tokens (not access tokens) for
        authenticated service-to-service calls. The backend compute
        service account credentials are used to generate the token.

        Returns:
            ID token string

        Raises:
            Exception: If token cannot be retrieved
        """
        try:
            # Get ID token for the target audience (Cloud Run service URL)
            # This uses the default credentials (backend compute service account)
            token = id_token.fetch_id_token(Request(), self.service_url)
            return token
        except Exception as e:
            logger.error(f"Failed to get ID token: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if NER service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.service_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def extract_article_references(
        self,
        text: str,
        retry_count: int = 3
    ) -> List[str]:
        """
        Extract article references from text via Cloud Run service.

        This method makes an authenticated HTTP request to the Cloud Run
        NER service to extract ARTICLE_REFERENCE entities.

        Args:
            text: Input text to extract article references from
            retry_count: Number of retries on failure (default: 3)

        Returns:
            List of unique article reference strings

        Raises:
            RuntimeError: If all retries fail
        """
        # Handle empty input
        if not text or not text.strip():
            return []

        # Get authentication token
        try:
            token = self._get_id_token()
        except Exception as e:
            logger.error(f"Failed to get authentication token: {e}")
            raise RuntimeError(f"Authentication failed: {e}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(retry_count):
            try:
                response = await self.client.post(
                    f"{self.service_url}/extract-article-references",
                    json={"text": text},
                    headers=headers,
                )
                response.raise_for_status()

                data = response.json()
                article_refs = data.get("article_references", [])

                logger.info(
                    f"Extracted {len(article_refs)} article references from Cloud Run service"
                )
                return article_refs

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"HTTP error (attempt {attempt + 1}/{retry_count}): "
                    f"Status {e.response.status_code}, Response: {e.response.text}"
                )
                if attempt < retry_count - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    await asyncio.sleep(2 ** attempt)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout error (attempt {attempt + 1}/{retry_count}): {e}"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Request failed (attempt {attempt + 1}/{retry_count}): {e}"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        error_msg = f"NER service unavailable after {retry_count} attempts: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.info("CloudRunNERClient closed")
