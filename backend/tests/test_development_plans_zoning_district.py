"""
Integration tests for new query_by_zoning_district method.

Tests cover:
- Query by zoning district functionality
- Spatial containment filtering
- Integration with ZoningMapSpatialQuery
"""
import pytest
from unittest.mock import Mock, patch
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery


@pytest.fixture
def mock_db_connector():
    """Mock DBConnector for testing."""
    with patch("app.utils.vector_query.development_plans.DBConnector") as mock_db:
        db_instance = Mock()
        db_instance.db_name = "test_db"
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


class TestQueryByZoningDistrict:
    """Test suite for query_by_zoning_district method."""

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_success(
        self, mock_zoning_query_class, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test successful query by zoning district."""
        # Setup mock zoning query
        mock_zoning_instance = Mock()
        mock_zoning_instance.get_zoning_by_location.return_value = [
            {
                "code": "H-3-65",
                "article": "Article 50",
                "usage": "Residential",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-71.06, 42.36], [-71.05, 42.36], [-71.05, 42.37], [-71.06, 42.37], [-71.06, 42.36]]]
                },
            }
        ]
        mock_zoning_query_class.return_value = mock_zoning_instance

        # Setup mock db responses
        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = [
            {
                "text_chunk": "Test development plan in H-3-65 zone",
                "project_name": "Test Project",
                "file_name": "test_file",
                "zoning_codes": ["H-3-65"],
                "article_reference": ["Article 50"],
                "location_context": "Downtown Boston",
                "metadata": {"latitude": 42.365, "longitude": -71.058},
                "similarity_score": 0.85,
            }
        ]

        # Execute query
        results = query_instance.query_by_zoning_district(
            query_text="What developments are in this zone?",
            latitude=42.3601,
            longitude=-71.0589,
            city="boston",
            top_k=10,
        )

        # Verify results
        assert len(results) == 1
        assert results[0]["project_name"] == "Test Project"
        assert results[0]["similarity_score"] == 0.85
        assert results[0]["_zoning_code"] == "H-3-65"  # Added by method

        # Verify method calls
        mock_db_connector.get_city_id.assert_called_once_with("boston")
        mock_embedding_client.generate_text_embeddings.assert_called_once()
        mock_zoning_instance.get_zoning_by_location.assert_called_once_with(
            latitude=42.3601,
            longitude=-71.0589,
            city="boston",
        )
        mock_db_connector.execute.assert_called_once()
        mock_db_connector.close.assert_called_once()

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_no_zoning_found(
        self, mock_zoning_query_class, query_instance, mock_db_connector
    ):
        """Test query when no zoning district found at location."""
        mock_zoning_instance = Mock()
        mock_zoning_instance.get_zoning_by_location.return_value = []
        mock_zoning_query_class.return_value = mock_zoning_instance

        mock_db_connector.get_city_id.return_value = 1

        with pytest.raises(ValueError, match="No zoning district found at location"):
            query_instance.query_by_zoning_district(
                query_text="test",
                latitude=42.3601,
                longitude=-71.0589,
                city="boston",
            )

        mock_db_connector.close.assert_called_once()

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_city_not_found(
        self, mock_zoning_query_class, query_instance, mock_db_connector
    ):
        """Test query when city not found."""
        mock_db_connector.get_city_id.return_value = None

        with pytest.raises(ValueError, match="City 'nonexistent' not found"):
            query_instance.query_by_zoning_district(
                query_text="test",
                latitude=42.3601,
                longitude=-71.0589,
                city="nonexistent",
            )

        mock_db_connector.close.assert_called_once()

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_no_geometry(
        self, mock_zoning_query_class, query_instance, mock_db_connector
    ):
        """Test query when zoning has no geometry data."""
        mock_zoning_instance = Mock()
        mock_zoning_instance.get_zoning_by_location.return_value = [
            {"code": "H-3-65", "geometry": None}  # No geometry
        ]
        mock_zoning_query_class.return_value = mock_zoning_instance

        mock_db_connector.get_city_id.return_value = 1

        with pytest.raises(ValueError, match="No geometry available"):
            query_instance.query_by_zoning_district(
                query_text="test",
                latitude=42.3601,
                longitude=-71.0589,
                city="boston",
            )

        mock_db_connector.close.assert_called_once()

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_sql_contains_spatial_query(
        self, mock_zoning_query_class, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Verify SQL query uses ST_Contains for spatial filtering."""
        mock_zoning_instance = Mock()
        mock_zoning_instance.get_zoning_by_location.return_value = [
            {
                "code": "H-3-65",
                "geometry": {"type": "Polygon", "coordinates": [[[-71.06, 42.36]]]},
            }
        ]
        mock_zoning_query_class.return_value = mock_zoning_instance

        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        query_instance.query_by_zoning_district(
            query_text="test",
            latitude=42.3601,
            longitude=-71.0589,
            city="boston",
        )

        # Verify SQL query contains spatial operations
        call_args = mock_db_connector.execute.call_args
        query_str = call_args[0][0]

        assert "ST_GeomFromGeoJSON" in query_str
        assert "ST_Contains" in query_str
        assert "ST_MakePoint" in query_str
        assert "zoning_boundary" in query_str

    @patch("app.utils.vector_query.development_plans.ZoningMapSpatialQuery")
    def test_query_by_zoning_district_with_similarity_threshold(
        self, mock_zoning_query_class, query_instance, mock_db_connector, mock_embedding_client
    ):
        """Test query with custom similarity threshold."""
        mock_zoning_instance = Mock()
        mock_zoning_instance.get_zoning_by_location.return_value = [
            {
                "code": "H-3-65",
                "geometry": {"type": "Polygon", "coordinates": [[[-71.06, 42.36]]]},
            }
        ]
        mock_zoning_query_class.return_value = mock_zoning_instance

        mock_db_connector.get_city_id.return_value = 1
        mock_db_connector.embedding_to_pgvector.return_value = "[0.1,0.2,...]"
        mock_db_connector.execute.return_value = []

        query_instance.query_by_zoning_district(
            query_text="test",
            latitude=42.3601,
            longitude=-71.0589,
            city="boston",
            similarity_threshold=0.7,
        )

        # Verify threshold is in parameters
        call_args = mock_db_connector.execute.call_args
        params = call_args[0][1]
        assert 0.7 in params

