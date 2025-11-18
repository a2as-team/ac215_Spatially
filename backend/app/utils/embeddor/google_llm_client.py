from google import genai
from google.genai import types, errors
import time
import logging

logger = logging.getLogger(__name__)


class GoogleLLMClient:
    def __init__(
        self,
        gcp_project: str,
        gcp_region: str,
    ):
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region
        if not self.gcp_project:
            raise ValueError("GCP_PROJECT environment variable not set")
        if not self.gcp_region:
            raise ValueError("GCP_REGION environment variable not set")
        self._init_llm_client()

    def _init_llm_client(self):
        self.embedding_model = "text-embedding-004"
        self.embedding_dimension = 768
        self.llm_client = genai.Client(
            vertexai=True, project=self.gcp_project, location=self.gcp_region
        )

    def generate_text_embeddings(
        self,
        text: str | list[str],
        batch_size: int = 250,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> list[list[float]]:
        """
        Generate embeddings using Vertex AI text-embedding-004.

        Args:
            text: Single text string or list of text strings to embed
            batch_size: Number of texts to process in each batch (default: 250)
            max_retries: Maximum number of retry attempts on API errors (default: 5)
            retry_delay: Initial delay in seconds between retries, doubles on each retry (default: 5)

        Returns:
            List of embeddings. For single text input, returns list with one embedding.
            For list input, returns list of embeddings in same order as input.
            Each embedding is a list of floats with length = embedding_dimension (768).

        Raises:
            ValueError: If API fails after all retries
        """
        # Normalize input to list
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            retry_count = 0
            while retry_count <= max_retries:
                try:
                    response = self.llm_client.models.embed_content(
                        model=self.embedding_model,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            output_dimensionality=self.embedding_dimension
                        ),
                    )
                    # Extract embedding values from response
                    all_embeddings.extend(
                        [embedding.values for embedding in response.embeddings]
                    )
                    break

                except errors.APIError as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        error_msg = f"Failed to generate embeddings after {max_retries} attempts. Last error: {str(e)}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                    # Exponential backoff
                    wait_time = retry_delay * (2 ** (retry_count - 1))
                    logger.warning(
                        f"API error (code: {e.code}): {e.message}. "
                        f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})..."
                    )
                    time.sleep(wait_time)

        return all_embeddings
