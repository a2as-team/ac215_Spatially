import "@/styles/globals.css";
import "@mantine/core/styles.css";
import "maplibre-gl/dist/maplibre-gl.css";
import type { AppProps } from "next/app";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider defaultColorScheme="light">
        <Component {...pageProps} />
      </MantineProvider>
    </QueryClientProvider>
  );
}
