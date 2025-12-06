from typing import Any, Dict, List, Optional
from app.utils.db_accessor import DBConnector
import json
import logging
import re


class ZoningMapSpatialQuery:
    def __init__(self, db_name):
        self.logger = logging.getLogger(__name__)
        self.db = DBConnector(db_name)

    def query(self, query):
        return self.db.execute(query)

    def _normalize_zone_code(self, code: str) -> str:
        """
        Normalize a zone code by extracting the base code.

        Handles patterns like:
        - R-1/PUD -> R-1
        - R-1(10) -> R-1
        - CH(O) -> CH
        - MF-L/SMHAO -> MF-L
        - R-1(WYCO) -> R-1
        - C-6-OVERLAY -> C-6
        """
        if not code:
            return code

        # Remove overlay suffixes
        code = re.sub(r'-OVERLAY$', '', code, flags=re.IGNORECASE)

        # Take first part before slash (e.g., R-1/PUD -> R-1)
        code = code.split('/')[0]

        # Remove parenthetical suffixes (e.g., R-1(10) -> R-1, but keep R-1-3-C)
        code = re.sub(r'\([^)]*\)$', '', code)

        return code.strip()

    def _get_zone_code_match_query(self) -> str:
        """
        Returns a SQL fragment for smart zone code matching.

        Matching priority:
        1. Exact match (zm.code = zc.zone_code)
        2. Article prefix stripped from zc.zone_code (Art42A_B-1-55 -> B-1-55)
           Boston zoning_codes have Article prefix, but zoning_maps don't
        3. First part before '/' (R-1/PUD -> R-1) - for combined zone codes
        4. Case-insensitive match for descriptive zone names

        Note: We intentionally do NOT do:
        - M-1 ≠ M1 matching (these may be different zones in different cities)
        - Parenthetical stripping R-1(10) -> R-1 (these are distinct zones)
        """
        return """
            LEFT JOIN LATERAL (
                SELECT zc.zone_subtype, zc.description, zc.zone_code as matched_code
                FROM zoning_codes zc
                WHERE zc.city_id = zm.city_id
                AND (
                    -- Priority 1: Exact match
                    zc.zone_code = zm.code
                    OR
                    -- Priority 2: Strip Article prefix from zc.zone_code
                    -- Boston zoning_codes have Art##_ prefix, zoning_maps don't
                    zm.code = REGEXP_REPLACE(zc.zone_code, '^Art[0-9A-Za-z]+_', '')
                    OR
                    -- Priority 3: First part before '/' (e.g., R-1/PUD -> R-1)
                    -- Only when map code contains '/' and DB code doesn't
                    -- Note: %% is escaped for psycopg2
                    (zm.code LIKE '%%/%%' AND zc.zone_code = SPLIT_PART(zm.code, '/', 1))
                    OR
                    -- Priority 4: Case-insensitive match for descriptive names
                    UPPER(zc.zone_code) = UPPER(zm.code)
                    OR
                    UPPER(zm.code) = UPPER(REGEXP_REPLACE(zc.zone_code, '^Art[0-9A-Za-z]+_', ''))
                )
                ORDER BY
                    CASE
                        WHEN zc.zone_code = zm.code THEN 1
                        WHEN zm.code = REGEXP_REPLACE(zc.zone_code, '^Art[0-9A-Za-z]+_', '') THEN 2
                        WHEN zc.zone_code = SPLIT_PART(zm.code, '/', 1) THEN 3
                        WHEN UPPER(zc.zone_code) = UPPER(zm.code) THEN 4
                        ELSE 5
                    END,
                    LENGTH(zc.zone_code) DESC  -- Prefer longer (more specific) matches
                LIMIT 1
            ) zc ON true
        """

    def get_zoning_by_location(
        self, latitude: float, longitude: float, city: str
    ) -> List[Dict[str, Any]]:
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            query = f"""
                SELECT
                    zm.id,
                    zm.code,
                    zm.article,
                    zm.usage,
                    ST_AsGeoJSON(zm.geom) as geometry,
                    zm.created_at,
                    zc.zone_subtype,
                    zc.description as zone_description,
                    zc.matched_code
                FROM zoning_maps zm
                {self._get_zone_code_match_query()}
                WHERE zm.city_id = %s
                  AND ST_Contains(
                        zm.geom,
                        ST_SetSRID(
                            ST_MakePoint(%s, %s),
                            4326
                        )
                    )
                ORDER BY zm.code;
            """
            results = self.db.execute(query, (city_id, longitude, latitude))

            if not results:
                raise ValueError(
                    f"No zoning data found for location ({latitude}, {longitude}) in {city}"
                )

            zoning_data = []
            for row in results:
                data = dict(row)
                data["geometry"] = (
                    json.loads(data["geometry"]) if data["geometry"] else None
                )
                # Convert datetime to ISO format string for JSON serialization
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                zoning_data.append(data)
            self.logger.info(
                f"Found {len(zoning_data)} zoning areas at ({latitude}, {longitude}) in {city}"
            )
            return zoning_data
        except Exception as e:
            self.logger.error(f"Error querying zoning geodata by location: {e}")
            raise
        finally:
            self.db.close()

    def get_all_zoning_for_city(self, city: str) -> List[Dict[str, Any]]:
        """Get all zoning data for a city"""
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            query = f"""
                SELECT
                    zm.id,
                    zm.code,
                    zm.article,
                    zm.usage,
                    ST_AsGeoJSON(zm.geom) as geometry,
                    zm.created_at,
                    zc.zone_subtype,
                    zc.description as zone_description,
                    zc.matched_code
                FROM zoning_maps zm
                {self._get_zone_code_match_query()}
                WHERE zm.city_id = %s
                ORDER BY zm.code;
            """
            results = self.db.execute(query, (city_id,))

            if not results:
                self.logger.warning(f"No zoning data found for city: {city}")
                return []

            zoning_data = []
            for row in results:
                data = dict(row)
                data["geometry"] = (
                    json.loads(data["geometry"]) if data["geometry"] else None
                )
                # Convert datetime to ISO format string for JSON serialization
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                zoning_data.append(data)

            self.logger.info(f"Found {len(zoning_data)} zoning areas in {city}")
            return zoning_data
        except Exception as e:
            self.logger.error(f"Error querying all zoning data for city: {e}")
            raise
        finally:
            self.db.close()

    def get_city_id(self, city_name: str) -> Optional[int]:
        try:
            query = "SELECT id FROM cities WHERE name = %s"
            cursor = self.db.execute(query, (city_name.lower(),))
            result = cursor.fetchone()
            if result:
                return result["id"]
            return None
        except Exception as e:
            self.logger.error(f"Error getting city ID: {e}")
            raise
