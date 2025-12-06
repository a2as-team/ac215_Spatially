"""
Unit tests for DevelopmentPlansVectorQuery class.

Tests cover:
- Basic query functionality
- Article reference filtering
- Project/file name filtering
- Similarity threshold filtering
- City not found errors
- get_projects_by_city method
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery


@pytest.fixture
def mock_db_connector():
    """Mock DBConnector for testing."""
    with patch("app.utils.vector_query.development_plans.DBConnector") as mock_db:
        db_instance = Mock()
        mock_db.return_value = db_instance
        yield db_instance


@pytest.fixture
def mock_embedding_client():
    """Mock GoogleLLMClient for testing."""
    with patch("app.utils.vector_query.development_plans.GoogleLLMClient") as mock_client:
        client_instance = Mock()
        client_instance.generate_text_embeddings.return_value = [
            [0.1] * 768  # Mock 768-dimensional embedding
        ]
        mock_client.return_value = client_instance
        yield client_instance


@pytest.fixture
def query_instance(mock_db_connector, mock_embedding_client):
    """Create DevelopmentPlansVectorQuery instance with mocked dependencies."""
    with patch.dict("os.environ", {"GCP_PROJECT": "test-project", "GCP_REGION": "us-central1"}):
        instance = DevelopmentPlansVectorQuery(db_name="test_db")
        return instance


class TestDevelopmentPlansVectorQuery:
    """Test suite for DevelopmentPlansVectorQuery."""

    def test_initialization(self, query_instance, mock_db_connector, mock_embedding_client):
        """Test that the query instance initializes correctly."""
        assert query_instance.db is not None
        assert query_instance.embedding_client is not None
        assert query_instance.gcp_project == "test-project"
        assert query_instance.gcp_region == "us-central1"

    def test_initialization_missing_env_vars(self):
        """Test that initialization fails if GCP env vars are missing."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("app.utils.vector_query.development_plans.DBConnector"):
                with pytest.raises(ValueError, match="GCP_PROJECT and GCP_REGION must be set"):
                    DevelopmentPlansVectorQuery(db_name="test_db")

    def test_basic_query(self, query_instance, mock_db_connector, mock_embedding_client):
        """Test basic query without filters."""
        # Setup mock responses
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = [
            {
                "text_chunk": "Test development plan text",
                "project_name": "Test Project",
                "file_name": "test_file",
                "zoning_codes": ["R1"],
                "article_reference": ["Article 50"],
                "location_context": "Downtown Boston",
                "metadata": {},
                "similarity_score": 0.85,
            }
        ]

        # Execute query
        results = query_instance.query(
            query_text="test query",
            city="boston",
            top_k=5,
        )

        # Verify results
        assert len(results) == 1
        assert results[0]["project_name"] == "Test Project"
        assert results[0]["similarity_score"] == 0.85
        assert isinstance(results[0], dict)

        # Verify method calls
        mock_db_connector.get_city_id.assert_called_once_with("boston")
        mock_embedding_client.generate_text_embeddings.assert_called_once_with("test query")
        mock_db_connector.execute.assert_called_once()
        mock_db_connector.close.assert_called_once()

    def test_query_with_article_reference_filter(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with article_reference filter."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        results = query_instance.query(
            query_text="test query",
            city="boston",
            article_reference=["Article 50", "Section 32"],
        )

        # Check that article_reference was passed in query parameters
        call_args = mock_db_connector.execute.call_args
        assert call_args is not None
        query_str = call_args[0][0]
        params = call_args[0][1]

        # Verify article_reference filter is in query
        assert "article_reference && %s" in query_str
        assert ["Article 50", "Section 32"] in params

    def test_query_with_project_name_filter(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with project_name_contains filter."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        results = query_instance.query(
            query_text="test query",
            city="boston",
            project_name_contains="Hood Park",
        )

        # Check that project_name filter was applied
        call_args = mock_db_connector.execute.call_args
        query_str = call_args[0][0]
        params = call_args[0][1]

        assert "project_name ILIKE %s" in query_str
        assert "%Hood Park%" in params

    def test_query_with_file_name_filter(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with file_name_contains filter."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        results = query_instance.query(
            query_text="test query",
            city="boston",
            file_name_contains="LOI",
        )

        # Check that file_name filter was applied
        call_args = mock_db_connector.execute.call_args
        query_str = call_args[0][0]
        params = call_args[0][1]

        assert "file_name ILIKE %s" in query_str
        assert "%LOI%" in params

    def test_query_with_similarity_threshold(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with similarity_threshold."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        results = query_instance.query(
            query_text="test query",
            city="boston",
            similarity_threshold=0.7,
        )

        # Verify threshold is in parameters
        call_args = mock_db_connector.execute.call_args
        params = call_args[0][1]
        assert 0.7 in params

    def test_query_city_not_found(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query raises ValueError when city not found."""
        mock_db_connector.get_city_id.return_value = None

        with pytest.raises(ValueError, match="City 'nonexistent' not found"):
            query_instance.query(
                query_text="test query",
                city="nonexistent",
            )

        mock_db_connector.close.assert_called_once()

    def test_query_database_error(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query handles database errors."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            query_instance.query(
                query_text="test query",
                city="boston",
            )

        mock_db_connector.close.assert_called_once()

    def test_get_projects_by_city(
        self, query_instance, mock_db_connector
    ):
        """Test get_projects_by_city method."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.execute.return_value = [
            {
                "project_name": "100 Hood Park Drive",
                "file_count": 3,
                "article_references": ["Article 50", "Section 32"],
            },
            {
                "project_name": "Downtown Tower",
                "file_count": 2,
                "article_references": ["Article 10"],
            },
        ]

        results = query_instance.get_projects_by_city(city="boston")

        assert len(results) == 2
        assert results[0]["project_name"] == "100 Hood Park Drive"
        assert results[0]["file_count"] == 3
        assert "Article 50" in results[0]["article_references"]

        mock_db_connector.get_city_id.assert_called_once_with("boston")
        mock_db_connector.close.assert_called_once()

    def test_get_projects_city_not_found(
        self, query_instance, mock_db_connector
    ):
        """Test get_projects_by_city raises ValueError when city not found."""
        mock_db_connector.get_city_id.return_value = None

        with pytest.raises(ValueError, match="City 'nonexistent' not found"):
            query_instance.get_projects_by_city(city="nonexistent")

        mock_db_connector.close.assert_called_once()

    def test_query_with_multiple_filters(
        self, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with multiple filters applied simultaneously."""
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        results = query_instance.query(
            query_text="test query",
            city="boston",
            top_k=10,
            similarity_threshold=0.8,
            article_reference=["Article 50"],
            project_name_contains="Hood",
            file_name_contains="LOI",
        )

        # Verify all filters are in query
        call_args = mock_db_connector.execute.call_args
        query_str = call_args[0][0]
        params = call_args[0][1]

        assert "article_reference && %s" in query_str
        assert "project_name ILIKE %s" in query_str
        assert "file_name ILIKE %s" in query_str
        assert 0.8 in params
        assert ["Article 50"] in params
        assert "%Hood%" in params
        assert "%LOI%" in params
        assert 10 in params  # top_k
