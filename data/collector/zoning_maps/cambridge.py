from .base import ZoningMapsBaseCollector
from utils.selenium import SeleniumUtil
import requests
import time
from pathlib import Path
import geopandas as gpd


class CambridgeZoningMapsCollector(ZoningMapsBaseCollector):
    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())

    def city(self) -> str:
        return "cambridge"

    def zoning_static_resource_url(self) -> str:
        """Base page URL containing zoning map PDFs."""
        return "https://www.cambridgema.gov/CDD/zoninganddevelopment/Zoning/Maps"

    def zoning_geospatial_resource_url(self) -> str:
        return "https://services1.arcgis.com/WnzC35krSYGuYov4/arcgis/rest/services/Zoning_Districts/FeatureServer"

    # Column mappings
    def zoning_article_column(self) -> str:
        return None

    def zoning_usage_column(self) -> str:
        return None

    def zoning_code_column(self) -> str:
        return "ZONE_TYPE"

    def download_zoning_static_files(self):
        """
        Download the two main zoning maps: Base and Overlay District maps.
        """
        import os
        from selenium.webdriver.common.by import By

        url = self.zoning_static_resource_url()
        self.logger.info(f"Scraping zoning maps from: {url}")

        os.makedirs(self.download_directory(), exist_ok=True)

        # Navigate to the page
        self.selenium_util.driver.get(url)
        time.sleep(3)  # Wait for page to fully load

        # Maps we're looking for
        target_maps = {
            "base_zoning_district": ["Base Zoning District", "base zoning", "zoning base"],
            "overlay_zoning_district": ["Overlay Zoning District", "overlay zoning", "zoning overlay"]
        }

        downloaded_files = []

        for map_name, search_terms in target_maps.items():
            try:
                self.logger.info(f"Looking for {map_name}...")

                # Find the section containing this map
                link = None
                for term in search_terms:
                    # Try to find link near text containing the search term
                    try:
                        # Look for the term in the page
                        elements = self.selenium_util.driver.find_elements(
                            By.XPATH,
                            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term.lower()}')]"
                        )

                        # For each matching element, look for nearby PDF links
                        for element in elements:
                            # Try to find "View Map" link or PDF link nearby
                            try:
                                # Look for PDF link in same parent or nearby
                                parent = element.find_element(By.XPATH, '..')
                                pdf_link = parent.find_element(By.XPATH, ".//a[contains(@href, '.pdf') or contains(translate(text(), 'VIEW MAP', 'view map'), 'view map')]")
                                link = pdf_link
                                break
                            except:
                                continue

                        if link:
                            break
                    except:
                        continue

                if not link:
                    self.logger.warning(f"Could not find link for {map_name}")
                    continue

                # Get the PDF URL
                href = link.get_attribute("href")
                self.logger.info(f"Found {map_name} at: {href}")

                # Download the PDF
                response = requests.get(href, timeout=60)
                response.raise_for_status()

                # Create filename
                filename = f"cambridge_{map_name}.pdf"
                filepath = Path(self.download_directory()) / filename

                # Save to file
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                file_size = len(response.content)
                self.logger.info(f"Downloaded {filename} ({file_size:,} bytes)")

                downloaded_files.append({
                    "title": map_name.replace('_', ' ').title(),
                    "url": href,
                    "filename": filename,
                    "filepath": str(filepath)
                })

            except Exception as e:
                self.logger.error(f"Error downloading {map_name}: {e}")
                continue

        self.logger.info(f"Successfully downloaded {len(downloaded_files)}/2 zoning map PDFs")
        return downloaded_files

    def download_zoning_geospatial_files(self):
        """Download geospatial data from ArcGIS FeatureServer."""
        from utils.featureserver_downloader import FeatureServerDownloader
        import os

        url = self.zoning_geospatial_resource_url()
        os.makedirs(self.download_directory(), exist_ok=True)

        downloader = FeatureServerDownloader(logger=self.logger, epsg_code=self.EPSG_CODE)
        file_info = downloader.download_as_single_geojson(
            base_url=url,
            output_dir=self.download_directory(),
            merged_filename="cambridge_zoning.geojson",
            layer_name="Cambridge Zoning (Combined)"
        )

        file_info["title"] = "Cambridge Zoning (Combined)"
        return file_info

    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the files to the database."""
        self._create_zoning_maps_table()

        gdf = self._ensure_crs(gdf)

        self.logger.info(f"Available columns in GeoDataFrame: {gdf.columns.tolist()}")

        code_col = self.zoning_code_column()
        city = self.city()

        success_count = 0
        error_count = 0

        for idx, row in gdf.iterrows():
            try:
                # Cambridge doesn't have article or usage columns, use None
                article = None
                usage = None
                code = row[code_col]

                geometry_wkt = row['geometry'].wkt
                self._insert_zoning_map(self.db, city, code, article, usage, geometry_wkt)
                success_count += 1
            except Exception as e:
                self.logger.error(f"Error uploading row {idx} (code: {row.get(code_col, 'unknown')}): {e}")
                error_count += 1
                continue

        self.logger.info(f"Successfully uploaded {success_count}/{len(gdf)} zoning maps to database ({error_count} errors)")

    def upload_to_gcs(self, file_path: str, gcs_filename: str):
        """Upload the files to GCS."""
        self.gcp_storage.upload_file(
            file_path=file_path,
            destination_path=f"{self.gcp_storage_parent_directory()}/{gcs_filename}"
        )

    def collect(self):
        """
        Collect zoning maps data for Cambridge.
        """
        # Download static PDF files
        static_files = self.download_zoning_static_files()

        for file_info in static_files:
            self.upload_to_gcs(
                file_path=file_info['filepath'],
                gcs_filename=f"static/{file_info['filename']}"
            )

        # Download geospatial data
        geospatial_file = self.download_zoning_geospatial_files()
        self.upload_to_gcs(
            file_path=geospatial_file['filepath'],
            gcs_filename=f"geojson/{geospatial_file['filename']}"
        )

        # Upload to database
        gdf = gpd.read_file(geospatial_file['filepath'])
        self.upload_to_db(gdf)

        self.logger.info(f"Collection complete for {self.city()}")
