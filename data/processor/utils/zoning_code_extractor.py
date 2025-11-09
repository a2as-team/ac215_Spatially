import os
import pandas as pd
from utils.db_accessor import DBAccessor
import re

class ZoningCodeExtractor:
    def __init__(self, city: str):
        self._init_db()
        self.city = city
        self.zoning_codes = self._fetch_zoning_codes()
    
    def _init_db(self):
        self.db_name = os.environ.get("APP_DB_NAME") # We will store the census tracts in the app database
        self.db = DBAccessor(db_name=self.db_name)
    
    def _get_city_id(self, db: DBAccessor, city_name: str) -> int:
        """Get city_id from city name."""
        db.connect()
        with db.conn.cursor() as cur:
            cur.execute("SELECT id FROM cities WHERE name = %s", (city_name,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"City '{city_name}' not found in database")
            return result[0]
        
    def _fetch_zoning_codes(self):
        """We will fetch zoning codes from the database."""
        city_id = self._get_city_id(self.db, self.city)
        self.db.connect()
        with self.db.conn.cursor() as cur:
            # We will first fetch all the rows from the zoning_maps table for the given city
            cur.execute("SELECT code, article, usage FROM zoning_maps WHERE city_id = %s", (city_id,))
            zoning_maps = cur.fetchall()
            # We will then convert the zoning_maps to a GeoDataFrame
            df = pd.DataFrame(zoning_maps, columns=['code', 'article', 'usage'])
            zoning_codes = df["code"].unique().tolist()
            if len(zoning_codes) == 0:
                raise ValueError(f"No zoning codes found for {self.city}. Please collect the zoning maps first.")
            print(f"There are {len(zoning_codes)} unique zoning codes for {self.city}")

    def _fetch_zoning_codes(self):
        """We will fetch zoning codes from the database."""
        city_id = self._get_city_id(self.db, self.city)
        self.db.connect()
        with self.db.conn.cursor() as cur:
            # We will first fetch all the rows from the zoning_maps table for the given city
            cur.execute("SELECT code, article, usage FROM zoning_maps WHERE city_id = %s", (city_id,))
            zoning_maps = cur.fetchall()
            # We will then convert the zoning_maps to a GeoDataFrame
            df = pd.DataFrame(zoning_maps, columns=['code', 'article', 'usage'])
            zoning_codes = df["code"].unique().tolist()
            if len(zoning_codes) == 0:
                raise ValueError(f"No zoning codes found for {self.city}. Please collect the zoning maps first.")
            print(f"There are {len(zoning_codes)} unique zoning codes for {self.city}")
            return zoning_codes
    
    def extract_zoning_codes_from_text(self, text: str):
        if not text:
            return []
    
        matched_codes = set()
        for code in self.zoning_codes:
            escaped_code = re.escape(code)
            
            if len(code) == 1:
                neg_lookbehind = r'(?<!\d-)'
                pattern = neg_lookbehind + r'(?:district|zone|zoning|districts|zones)\s+' + escaped_code + r'\b'
                pattern += r'|' + neg_lookbehind + r'\b' + escaped_code + r'\s+(?:district|zone|zoning|districts|zones)'
                pattern += r'|' + neg_lookbehind + r'(?:,\s*|;\s*)' + escaped_code + r'(?:\s*,|\s*;|\s+)'
            else:
                pattern = r'\b' + escaped_code + r'\b'

            if re.search(pattern, text, re.IGNORECASE):
                matched_codes.add(code)

        return sorted(list(matched_codes))