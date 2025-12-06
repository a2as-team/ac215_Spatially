import { useRouter } from "next/router";
import { GetStaticProps, GetStaticPaths } from "next";
import Image from "next/image";
import { useEffect, useRef, useState, useCallback } from "react";
import {
  AppShell,
  Burger,
  Group,
  Title,
  Text,
  Textarea,
  ScrollArea,
  Stack,
  Paper,
  Loader,
  ActionIcon,
  Divider,
  Badge,
  Box,
  Avatar,
} from "@mantine/core";
import { useDisclosure, useHotkeys } from "@mantine/hooks";
import {
  IconSend,
  IconPlus,
  IconMapPin,
  IconUser,
  IconRobot,
  IconX,
} from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStartChat, useContinueChat, useChats, useChat } from "@/hooks/useChat";
import { ZoningData, CityZoningResponse, getCityZoningServerSide } from "@/services/zoningApi";
import { getCitiesServerSide } from "@/services/citiesApi";
import { getZoneSubtypeColor } from "@/utils/zoningColors";
import { MapLegend } from "@/components/MapLegend";

interface CityPageProps {
  cityZoningData: CityZoningResponse;
}

export default function CityPage({ cityZoningData }: CityPageProps) {
  const router = useRouter();
  const { id } = router.query;
  const [opened, { toggle }] = useDisclosure();
  const [inputValue, setInputValue] = useState("");
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [selectedZoning, setSelectedZoning] = useState<ZoningData[] | null>(
    null
  );
  const [selectedLocation, setSelectedLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  const { data: chats } = useChats(10);
  const { data: currentChatData } = useChat(currentChatId);
  const { mutate: startChat, isPending: isStarting } = useStartChat();
  const { mutate: continueChat, isPending: isContinuing } = useContinueChat();

  const isPending = isStarting || isContinuing;

  // Get current chat messages from the dedicated query (updates immediately on mutation)
  const messages = currentChatData?.messages || [];

  // Add zoning polygons to map
  const addZoningLayer = useCallback((zoningData: ZoningData[], fitBounds = true) => {
    // Check map style is fully loaded before adding layers
    if (!map.current || !map.current.isStyleLoaded()) {
      console.log("Map style not ready for adding zoning layer");
      return;
    }

    console.log(`Adding zoning layer with ${zoningData.length} zones`);

    // Remove existing zoning layer if it exists
    if (map.current.getLayer("zoning-fill")) {
      map.current.removeLayer("zoning-fill");
    }
    if (map.current.getLayer("zoning-outline")) {
      map.current.removeLayer("zoning-outline");
    }
    if (map.current.getSource("zoning")) {
      map.current.removeSource("zoning");
    }

    // Log sample of incoming data to debug zone_subtype
    console.log("Sample zoning data:", zoningData.slice(0, 3).map(z => ({
      code: z.code,
      zone_subtype: z.zone_subtype,
    })));

    // Create GeoJSON features from zoning data with color based on zone_subtype
    const features = zoningData
      .filter((z) => z.geometry)
      .map((z) => {
        const color = getZoneSubtypeColor(z.zone_subtype);
        return {
          type: "Feature" as const,
          properties: {
            code: z.code || z.zoning_code,
            article: z.article,
            usage: z.usage,
            zone_subtype: z.zone_subtype || "Unknown",
            color: color,
          },
          geometry: z.geometry,
        };
      });

    // Log color assignments
    const uniqueColors = [...new Set(features.map(f => `${f.properties.zone_subtype}: ${f.properties.color}`))];
    console.log("Zone subtype to color mappings:", uniqueColors);
    console.log(`Created ${features.length} GeoJSON features`);
    if (features.length === 0) {
      console.warn("No features with geometry to display");
      return;
    }

    // Add source
    map.current.addSource("zoning", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: features,
      },
    });

    // Add fill layer with data-driven color based on zone_subtype
    map.current.addLayer({
      id: "zoning-fill",
      type: "fill",
      source: "zoning",
      paint: {
        "fill-color": ["get", "color"],
        "fill-opacity": 0.5,
      },
    });

    // Add outline layer with matching color
    map.current.addLayer({
      id: "zoning-outline",
      type: "line",
      source: "zoning",
      paint: {
        "line-color": ["get", "color"],
        "line-width": 1.5,
      },
    });

    // Fit bounds to show all zoning areas (only on initial load)
    if (fitBounds) {
      const bounds = new maplibregl.LngLatBounds();
      features.forEach((feature) => {
        if (feature.geometry.type === "Polygon") {
          feature.geometry.coordinates[0].forEach((coord: number[]) => {
            bounds.extend(coord as [number, number]);
          });
        } else if (feature.geometry.type === "MultiPolygon") {
          feature.geometry.coordinates.forEach((polygon: number[][][]) => {
            polygon[0].forEach((coord: number[]) => {
              bounds.extend(coord as [number, number]);
            });
          });
        }
      });
      // Resize map to ensure proper dimensions, then fit bounds
      map.current.resize();
      // Small delay to ensure resize is applied before fitBounds
      setTimeout(() => {
        map.current?.fitBounds(bounds, {
          padding: { top: 50, right: 50, bottom: 50, left: 50 }
        });
      }, 50);
    }
  }, []);

  // Highlight selected zones by dimming others
  const highlightSelectedZones = useCallback((selectedCodes: string[]) => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    map.current.setPaintProperty("zoning-fill", "fill-opacity", [
      "case",
      ["in", ["get", "code"], ["literal", selectedCodes]],
      0.7, // Selected zones: higher opacity
      0.15, // Other zones: dimmed
    ]);

    map.current.setPaintProperty("zoning-outline", "line-opacity", [
      "case",
      ["in", ["get", "code"], ["literal", selectedCodes]],
      1, // Selected zones: full opacity
      0.3, // Other zones: dimmed
    ]);

    map.current.setPaintProperty("zoning-outline", "line-width", [
      "case",
      ["in", ["get", "code"], ["literal", selectedCodes]],
      3, // Selected zones: thicker line
      1, // Other zones: thin line
    ]);
  }, []);

  // Reset zone highlighting (restore all to normal opacity)
  const resetZoneHighlight = useCallback(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    map.current.setPaintProperty("zoning-fill", "fill-opacity", 0.5);
    map.current.setPaintProperty("zoning-outline", "line-opacity", 1);
    map.current.setPaintProperty("zoning-outline", "line-width", 1.5);
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) {
      console.log("Map container not ready");
      return;
    }

    if (map.current) {
      console.log("Map already initialized");
      return;
    }

    console.log("Initializing map...");

    try {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [-71.0589, 42.3601], // Boston
        zoom: 12,
      });

      map.current.on("load", () => {
        console.log("Map loaded successfully!");
        // Trigger resize to account for sidebar layout
        // Use multiple resize calls to ensure proper dimensions after CSS settles
        setTimeout(() => {
          map.current?.resize();
          setTimeout(() => {
            map.current?.resize();
            setMapLoaded(true);
          }, 100);
        }, 100);
      });

      map.current.on("error", (e) => {
        console.error("Map error:", e);
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");

      // Add click handler to query zoning
      map.current.on("click", (e) => {
        const { lng, lat } = e.lngLat;

        // Query features at click point from the zoning layer
        const features = map.current!.queryRenderedFeatures(e.point, {
          layers: ["zoning-fill"],
        });

        if (features.length === 0) {
          // Clicked outside any zone - clear selection
          setSelectedZoning(null);
          setSelectedLocation(null);
          if (markerRef.current) {
            markerRef.current.remove();
            markerRef.current = null;
          }
          resetZoneHighlight();
          return;
        }

        // Add or update marker
        if (markerRef.current) {
          markerRef.current.remove();
        }
        markerRef.current = new maplibregl.Marker({ color: "#FF0000" })
          .setLngLat([lng, lat])
          .addTo(map.current!);

        // Save selected location for chat context
        setSelectedLocation({ latitude: lat, longitude: lng });

        // Convert MapLibre features to ZoningData format
        const zoningData: ZoningData[] = features.map((f) => ({
          id: f.id as number,
          code: f.properties?.code,
          article: f.properties?.article,
          usage: f.properties?.usage,
          zone_subtype: f.properties?.zone_subtype,
          geometry: f.geometry,
        }));

        setSelectedZoning(zoningData);

        // Highlight selected zones (dim others)
        const selectedCodes = zoningData
          .map((z) => z.code)
          .filter(Boolean) as string[];
        highlightSelectedZones(selectedCodes);
      });
    } catch (error) {
      console.error("Failed to initialize map:", error);
    }

    return () => {
      console.log("Cleaning up map...");
      setMapLoaded(false);
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [id, addZoningLayer, highlightSelectedZones, resetZoneHighlight]);

  const handleSendMessage = () => {
    if (!inputValue.trim() || !id || typeof id !== "string") return;

    const content = inputValue;
    setInputValue("");

    if (!currentChatId) {
      // Start a new chat with city and optional location
      startChat(
        {
          content,
          city: id,
          latitude: selectedLocation?.latitude,
          longitude: selectedLocation?.longitude,
        },
        {
          onSuccess: (data) => {
            setCurrentChatId(data.chat_id);
          },
          onError: (error) => {
            console.error("Error starting chat:", error);
          },
        }
      );
    } else {
      // Continue existing chat with optional new location
      continueChat(
        {
          chatId: currentChatId,
          request: {
            content,
            latitude: selectedLocation?.latitude,
            longitude: selectedLocation?.longitude,
          },
        },
        {
          onError: (error) => {
            console.error("Error continuing chat:", error);
          },
        }
      );
    }
  };

  const handleNewChat = () => {
    setCurrentChatId(null);
    setInputValue("");
  };

  const handleClearSelection = useCallback(() => {
    // Clear selected zoning and location
    setSelectedZoning(null);
    setSelectedLocation(null);

    // Remove marker from map
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    // Reset zone highlighting (restore all to normal opacity)
    resetZoneHighlight();
  }, [resetZoneHighlight]);

  // Load city zoning data when available and map is ready
  useEffect(() => {
    console.log("City zoning effect triggered:", {
      mapLoaded,
      hasCityZoningData: !!cityZoningData,
      zoningDataLength: cityZoningData?.zoning_data?.length,
    });

    if (mapLoaded && cityZoningData?.zoning_data && cityZoningData.zoning_data.length > 0) {
      console.log(`Loading ${cityZoningData.zoning_data.length} zoning areas for city:`, cityZoningData.city);
      addZoningLayer(cityZoningData.zoning_data);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapLoaded, cityZoningData]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages]);

  // Handle escape key to deselect
  useHotkeys([["Escape", handleClearSelection]]);

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 500,
        breakpoint: "sm",
        collapsed: { mobile: !opened },
      }}
      padding={0}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger
              opened={opened}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
            />
            <Group
              style={{ cursor: "pointer" }}
              onClick={() => router.push("/")}
            >
              <Image src="/icon.png" alt="Spatially" width={40} height={40} />
              <Title order={3}>Spatially Zoning</Title>
            </Group>
            <Text size="sm" c="dimmed" tt="capitalize">
              {id || "Loading..."}
            </Text>
          </Group>

          {/* Zoning Information Display */}
          {selectedZoning && selectedZoning.length > 0 && (
            <Group gap="xs">
              <IconMapPin size={20} />
              <Text size="sm" fw={500}>
                Selected Zoning:
              </Text>
              {selectedZoning.map((zone, index) => (
                <Badge key={index} color="blue" variant="light">
                  {zone.code || zone.zoning_code}
                  {zone.zone_subtype && ` (${zone.zone_subtype})`}
                </Badge>
              ))}
              <ActionIcon
                size="sm"
                variant="subtle"
                color="gray"
                onClick={handleClearSelection}
                title="Clear selection"
              >
                <IconX size={16} />
              </ActionIcon>
            </Group>
          )}
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" style={{ backgroundColor: "white" }}>
        <Stack h="100%" gap="md">
          <Group justify="space-between">
            <div>
              <Title order={4}>Zoning Chat</Title>
              <Text size="sm" c="dimmed">
                Ask questions about zoning
              </Text>
            </div>
            <ActionIcon
              size="lg"
              variant="filled"
              onClick={handleNewChat}
              title="New Chat"
            >
              <IconPlus size={18} />
            </ActionIcon>
          </Group>

          <Divider />

          {/* Chat History */}
          {chats && chats.length > 0 && (
            <div>
              <Text size="xs" fw={500} c="dimmed" mb="xs">
                RECENT CHATS
              </Text>
              <Stack gap="xs">
                {chats.map((chat) => (
                  <Paper
                    key={chat.chat_id}
                    p="xs"
                    withBorder
                    style={{
                      cursor: "pointer",
                      backgroundColor:
                        currentChatId === chat.chat_id
                          ? "var(--mantine-color-blue-1)"
                          : "white",
                    }}
                    onClick={() => setCurrentChatId(chat.chat_id)}
                  >
                    <Text size="sm" lineClamp={1}>
                      {chat.title}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {new Date(chat.dts * 1000).toLocaleDateString()}
                    </Text>
                  </Paper>
                ))}
              </Stack>
            </div>
          )}

          <Divider />

          {/* Messages */}
          <ScrollArea style={{ flex: 1 }} offsetScrollbars ref={scrollAreaRef}>
            <Stack gap="md">
              {messages.length === 0 ? (
                <Paper p="md" withBorder style={{ backgroundColor: "white" }}>
                  <Text size="sm" c="dimmed" ta="center">
                    {currentChatId
                      ? "Loading messages..."
                      : "Start a new conversation!"}
                  </Text>
                </Paper>
              ) : (
                messages.map((message) => (
                  <Group
                    key={message.message_id}
                    align="flex-start"
                    gap="sm"
                    wrap="nowrap"
                    style={{
                      flexDirection:
                        message.role === "user" ? "row-reverse" : "row",
                    }}
                  >
                    <Avatar
                      color={message.role === "user" ? "blue" : "grape"}
                      radius="xl"
                      size="md"
                    >
                      {message.role === "user" ? (
                        <IconUser size={20} />
                      ) : (
                        <IconRobot size={20} />
                      )}
                    </Avatar>
                    <Paper
                      p="md"
                      radius="lg"
                      shadow="sm"
                      withBorder
                      style={{
                        maxWidth: "75%",
                        backgroundColor:
                          message.role === "user"
                            ? "var(--mantine-color-blue-1)"
                            : "var(--mantine-color-gray-0)",
                      }}
                    >
                      <Box>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => (
                              <Text size="sm" mb="xs" c="dark">
                                {children}
                              </Text>
                            ),
                            h1: ({ children }) => (
                              <Title order={4} mb="xs" c="dark">
                                {children}
                              </Title>
                            ),
                            h2: ({ children }) => (
                              <Title order={5} mb="xs" c="dark">
                                {children}
                              </Title>
                            ),
                            h3: ({ children }) => (
                              <Title order={6} mb="xs" c="dark">
                                {children}
                              </Title>
                            ),
                            code: ({ children, className }) => {
                              const isInline = !className;
                              return isInline ? (
                                <Text
                                  component="code"
                                  size="sm"
                                  c="blue"
                                  style={{
                                    backgroundColor: "var(--mantine-color-gray-1)",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    fontFamily: "monospace",
                                  }}
                                >
                                  {children}
                                </Text>
                              ) : (
                                <Text
                                  component="pre"
                                  size="sm"
                                  c="dark"
                                  style={{
                                    backgroundColor: "var(--mantine-color-gray-1)",
                                    padding: "12px",
                                    borderRadius: "8px",
                                    overflowX: "auto",
                                    fontFamily: "monospace",
                                  }}
                                >
                                  <code>{children}</code>
                                </Text>
                              );
                            },
                            ul: ({ children }) => (
                              <Text
                                component="ul"
                                size="sm"
                                c="dark"
                                style={{ paddingLeft: "20px" }}
                              >
                                {children}
                              </Text>
                            ),
                            ol: ({ children }) => (
                              <Text
                                component="ol"
                                size="sm"
                                c="dark"
                                style={{ paddingLeft: "20px" }}
                              >
                                {children}
                              </Text>
                            ),
                            li: ({ children }) => (
                              <Text component="li" size="sm" mb={4} c="dark">
                                {children}
                              </Text>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </Box>
                    </Paper>
                  </Group>
                ))
              )}
              {isPending && (
                <Group align="flex-start" gap="sm" wrap="nowrap">
                  <Avatar color="grape" radius="xl" size="md">
                    <IconRobot size={20} />
                  </Avatar>
                  <Paper
                    p="md"
                    radius="lg"
                    shadow="sm"
                    withBorder
                    style={{
                      backgroundColor: "var(--mantine-color-gray-0)",
                    }}
                  >
                    <Group gap="xs">
                      <Loader size="xs" />
                      <Text size="sm" c="dark">
                        Thinking...
                      </Text>
                    </Group>
                  </Paper>
                </Group>
              )}
            </Stack>
          </ScrollArea>

          {/* Input */}
          <Group gap="xs" align="flex-end">
            <Textarea
              placeholder="Ask about zoning... (Enter to send, Shift+Enter for new line)"
              value={inputValue}
              onChange={(e) => setInputValue(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              minRows={1}
              maxRows={4}
              autosize
              style={{ flex: 1 }}
              disabled={isPending}
            />
            <ActionIcon
              size="lg"
              variant="filled"
              color="blue"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isPending}
            >
              <IconSend size={18} />
            </ActionIcon>
          </Group>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main style={{ height: "100vh", overflow: "hidden" }}>
        <div style={{ position: "relative", width: "100%", height: "100%" }}>
          <div
            ref={mapContainer}
            style={{
              width: "100%",
              height: "100%",
            }}
          />
          <MapLegend zoningData={selectedZoning || cityZoningData?.zoning_data} />
        </div>
      </AppShell.Main>
    </AppShell>
  );
}

// Generate paths for all cities at build time
export const getStaticPaths: GetStaticPaths = async () => {
  const { cities } = await getCitiesServerSide();

  const paths = cities.map((city) => ({
    params: { id: city.name },
  }));

  return {
    paths,
    // fallback: 'blocking' allows new cities to be rendered on-demand
    fallback: "blocking",
  };
};

// Pre-fetch GeoJSON data at build time (or on-demand with ISR)
export const getStaticProps: GetStaticProps<CityPageProps> = async ({
  params,
}) => {
  const cityId = params?.id as string;

  if (!cityId) {
    return { notFound: true };
  }

  const cityZoningData = await getCityZoningServerSide(cityId);

  return {
    props: {
      cityZoningData,
    },
    // Revalidate every hour - GeoJSON data doesn't change often
    revalidate: 3600,
  };
};
