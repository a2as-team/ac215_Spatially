"""
Utility module for downloading geospatial data from ArcGIS FeatureServer endpoints.

This module provides functions to:
- Query FeatureServer metadata to discover layers
- Download GeoJSON data from individual layers
- Handle pagination for large datasets
- Save data to local files
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path


class FeatureServerDownloader:
    """
    A utility class for downloading geospatial data from ArcGIS FeatureServer endpoints.
    """

    def __init__(self, logger: Optional[logging.Logger] = None, epsg_code: int = 4326):
        """
        Initialize the FeatureServer downloader.

        Args:
            logger: Logger instance for logging messages. If None, creates a new logger.
            epsg_code: The EPSG code for the output coordinate system. Default is 4326 (WGS84).
        """
        self.logger = logger or logging.getLogger(__name__)
        self.epsg_code = epsg_code

    def get_service_info(self, base_url: str) -> Dict[str, Any]:
        """
        Query the FeatureServer to get service metadata including available layers.

        Args:
            base_url: The base URL of the FeatureServer (without trailing slash)

        Returns:
            Dictionary containing service information

        Raises:
            requests.RequestException: If the request fails
        """
        response = requests.get(f"{base_url}?f=json")
        response.raise_for_status()
        return response.json()

    def get_layers(self, base_url: str) -> List[Dict[str, Any]]:
        """
        Get all available layers from a FeatureServer.

        Args:
            base_url: The base URL of the FeatureServer

        Returns:
            List of layer dictionaries containing id, name, and other metadata
        """
        service_info = self.get_service_info(base_url)
        layers = service_info.get('layers', [])
        self.logger.info(f"Found {len(layers)} layers in FeatureServer")
        return layers

    def download_layer_geojson(
        self,
        base_url: str,
        layer_id: int,
        where_clause: str = '1=1',
        out_fields: str = '*',
        include_geometry: bool = True
    ) -> Dict[str, Any]:
        """
        Download GeoJSON data from a specific layer.

        Args:
            base_url: The base URL of the FeatureServer
            layer_id: The ID of the layer to download
            where_clause: SQL-like where clause to filter features (default: '1=1' for all)
            out_fields: Comma-separated list of fields to include (default: '*' for all)
            include_geometry: Whether to include geometry in the response

        Returns:
            GeoJSON dictionary containing features and metadata

        Raises:
            requests.RequestException: If the request fails
        """
        query_url = f"{base_url}/{layer_id}/query"
        params = {
            'where': where_clause,
            'outFields': out_fields,
            'returnGeometry': str(include_geometry).lower(),
            'f': 'geojson',
            'outSR': self.epsg_code
        }

        self.logger.debug(f"Querying layer {layer_id} from {query_url}")
        response = requests.get(query_url, params=params)
        response.raise_for_status()

        return response.json()

    def download_layer_with_pagination(
        self,
        base_url: str,
        layer_id: int,
        where_clause: str = '1=1',
        out_fields: str = '*',
        include_geometry: bool = True,
        max_record_count: int = 1000
    ) -> Dict[str, Any]:
        """
        Download large datasets with pagination support.

        Some FeatureServers limit the number of records returned per request.
        This method handles pagination to download all features.

        Args:
            base_url: The base URL of the FeatureServer
            layer_id: The ID of the layer to download
            where_clause: SQL-like where clause to filter features
            out_fields: Comma-separated list of fields to include
            include_geometry: Whether to include geometry in the response
            max_record_count: Maximum number of records per request

        Returns:
            Combined GeoJSON dictionary with all features
        """
        query_url = f"{base_url}/{layer_id}/query"
        offset = 0
        all_features = []

        while True:
            params = {
                'where': where_clause,
                'outFields': out_fields,
                'returnGeometry': str(include_geometry).lower(),
                'f': 'geojson',
                'outSR': self.epsg_code,
                'resultOffset': offset,
                'resultRecordCount': max_record_count
            }

            self.logger.debug(f"Fetching records {offset} to {offset + max_record_count}")
            response = requests.get(query_url, params=params)
            response.raise_for_status()
            geojson_data = response.json()

            features = geojson_data.get('features', [])
            if not features:
                break

            all_features.extend(features)
            offset += len(features)

            # If we got fewer features than requested, we've reached the end
            if len(features) < max_record_count:
                break

        # Return combined GeoJSON
        return {
            'type': 'FeatureCollection',
            'features': all_features
        }

    def save_geojson(self, geojson_data: Dict[str, Any], filepath: str) -> int:
        """
        Save GeoJSON data to a file.

        Args:
            geojson_data: The GeoJSON dictionary to save
            filepath: Path where the file should be saved

        Returns:
            Number of features saved
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2)

        feature_count = len(geojson_data.get('features', []))
        self.logger.info(f"Saved {feature_count} features to {filepath}")
        return feature_count

    def download_all_layers(
        self,
        base_url: str,
        output_dir: str,
        filename_prefix: str = '',
        use_pagination: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Download all layers from a FeatureServer and save them as separate GeoJSON files.

        Args:
            base_url: The base URL of the FeatureServer
            output_dir: Directory where files should be saved
            filename_prefix: Optional prefix for filenames
            use_pagination: Whether to use pagination for large datasets

        Returns:
            List of dictionaries containing metadata about downloaded files
        """
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get all layers
        layers = self.get_layers(base_url)
        downloaded_files = []

        for layer in layers:
            layer_id = layer['id']
            layer_name = layer['name']

            self.logger.info(f"Downloading layer {layer_id}: {layer_name}")

            try:
                # Download the layer data
                if use_pagination:
                    geojson_data = self.download_layer_with_pagination(base_url, layer_id)
                else:
                    geojson_data = self.download_layer_geojson(base_url, layer_id)

                # Create filename
                clean_layer_name = layer_name.replace(' ', '_').replace('/', '-')
                prefix = f"{filename_prefix}_" if filename_prefix else ""
                filename = f"{prefix}{clean_layer_name}_{layer_id}.geojson"
                filepath = Path(output_dir) / filename

                # Save to file
                feature_count = self.save_geojson(geojson_data, str(filepath))

                # Store metadata
                downloaded_files.append({
                    'layer_id': layer_id,
                    'layer_name': layer_name,
                    'filename': filename,
                    'filepath': str(filepath),
                    'feature_count': feature_count,
                    'url': base_url
                })

            except Exception as e:
                self.logger.error(f"Error downloading layer {layer_id} ({layer_name}): {e}")
                continue

        return downloaded_files
