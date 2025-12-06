import { apiClient } from './api';

export interface City {
  id: number;
  name: string;
  created_at: string;
}

export interface CitiesResponse {
  cities: City[];
  count: number;
}

export interface ZoningCode {
  id: number;
  zone_code: string;
  zone_subtype: string | null;
  area_acres: number | null;
  description: string | null;
  created_at: string;
}

export interface ZoningCodesResponse {
  zoning_codes: ZoningCode[];
  count: number;
}

export const citiesApi = {
  // Get all cities
  getCities: async (): Promise<CitiesResponse> => {
    const { data } = await apiClient.get<CitiesResponse>('/api/v1/cities/');
    return data;
  },

  // Get a specific city by name
  getCity: async (cityName: string): Promise<City> => {
    const { data } = await apiClient.get<City>(`/api/v1/cities/${cityName}`);
    return data;
  },

  // Get zoning codes for a city
  getZoningCodes: async (cityName: string): Promise<ZoningCodesResponse> => {
    const { data } = await apiClient.get<ZoningCodesResponse>(`/api/v1/cities/${cityName}/zoning-codes`);
    return data;
  },
};

// Server-side only function for getStaticProps
export const getCitiesServerSide = async (): Promise<CitiesResponse> => {
  // On server-side (inside Docker), use internal service name
  // On client-side (browser), use localhost
  const isServer = typeof window === 'undefined';
  const API_BASE_URL = isServer
    ? (process.env.SERVER_API_BASE_URL || 'http://backend:8000')
    : (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000');

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/cities/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch cities: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching cities:', error);
    return { cities: [], count: 0 };
  }
};

// Server-side only function to get zoning codes for a city
export const getZoningCodesServerSide = async (cityName: string): Promise<ZoningCodesResponse> => {
  const isServer = typeof window === 'undefined';
  const API_BASE_URL = isServer
    ? (process.env.SERVER_API_BASE_URL || 'http://backend:8000')
    : (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000');

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/cities/${cityName}/zoning-codes`);
    if (!response.ok) {
      throw new Error(`Failed to fetch zoning codes: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching zoning codes:', error);
    return { zoning_codes: [], count: 0 };
  }
};
