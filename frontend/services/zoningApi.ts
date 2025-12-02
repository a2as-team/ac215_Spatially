import { apiClient } from './api';

export interface ZoningSearchResult {
  chunk_text: string;
  similarity_score: number;
  metadata: {
    city: string;
    document_id?: string;
    document_title?: string;
    zoning_code?: string;
    chunk_index?: number;
  };
}

export interface ZoningSearchResponse {
  query: string;
  city: string;
  location?: {
    latitude: number;
    longitude: number;
  };
  filters?: {
    zoning_codes?: string[];
    document_title_contains?: string;
  };
  results: ZoningSearchResult[];
  count: number;
}

export interface ZoningData {
  id?: number;
  code: string;
  zoning_code?: string; // Alternative field name for compatibility
  article?: string;
  usage?: string;
  geometry?: any;
  created_at?: string;
}

export interface ZoningLocationResponse {
  location: {
    latitude: number;
    longitude: number;
  };
  city: string;
  zoning_data: ZoningData[];
  count: number;
}

export interface SearchZoningParams {
  city: string;
  question: string;
  top_k?: number;
  similarity_threshold?: number;
  latitude?: number;
  longitude?: number;
  zoning_codes?: string[];
  document_title_contains?: string;
}

export interface CityZoningResponse {
  city: string;
  zoning_data: ZoningData[];
  count: number;
}

// Server-side only function for getStaticProps (similar to citiesApi pattern)
export const getCityZoningServerSide = async (city: string): Promise<CityZoningResponse> => {
  const isServer = typeof window === 'undefined';
  const API_BASE_URL = isServer
    ? (process.env.SERVER_API_BASE_URL || 'http://backend:8000')
    : (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000');

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/zoning_ordinance/${city}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch zoning for ${city}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching zoning for ${city}:`, error);
    return { city, zoning_data: [], count: 0 };
  }
};

export const zoningApi = {
  searchZoningOrdinance: async (params: SearchZoningParams): Promise<ZoningSearchResponse> => {
    const { data } = await apiClient.get<ZoningSearchResponse>(
      '/api/v1/zoning_ordinance/search',
      { params }
    );
    return data;
  },

  getZoningAtLocation: async (
    city: string,
    latitude: number,
    longitude: number
  ): Promise<ZoningLocationResponse> => {
    const { data } = await apiClient.get<ZoningLocationResponse>(
      '/api/v1/zoning_ordinance/zoning',
      {
        params: { city, latitude, longitude },
      }
    );
    return data;
  },

  getAllZoningForCity: async (city: string): Promise<CityZoningResponse> => {
    const { data } = await apiClient.get<CityZoningResponse>(
      `/api/v1/zoning_ordinance/${city}`
    );
    return data;
  },
};
