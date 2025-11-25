import { useMutation, useQuery } from '@tanstack/react-query';
import {
  zoningApi,
  SearchZoningParams,
  ZoningSearchResponse,
  ZoningLocationResponse,
  CityZoningResponse
} from '@/services/zoningApi';

export const useZoningSearch = () => {
  return useMutation<ZoningSearchResponse, Error, SearchZoningParams>({
    mutationFn: (params) => zoningApi.searchZoningOrdinance(params),
  });
};

export const useZoningAtLocation = () => {
  return useMutation<
    ZoningLocationResponse,
    Error,
    { city: string; latitude: number; longitude: number }
  >({
    mutationFn: ({ city, latitude, longitude }) =>
      zoningApi.getZoningAtLocation(city, latitude, longitude),
  });
};

export const useCityZoning = (city: string | undefined) => {
  return useQuery<CityZoningResponse, Error>({
    queryKey: ['cityZoning', city],
    queryFn: () => zoningApi.getAllZoningForCity(city!),
    enabled: !!city,
  });
};
