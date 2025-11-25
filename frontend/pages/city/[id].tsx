import { useRouter } from "next/router";
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
import { useDisclosure } from "@mantine/hooks";
import {
  IconSend,
  IconMap,
  IconPlus,
  IconMapPin,
  IconUser,
  IconRobot,
  IconX,
} from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStartChat, useContinueChat, useChats } from "@/hooks/useChat";
import { useZoningAtLocation, useCityZoning } from "@/hooks/useZoningSearch";
import { ZoningData } from "@/services/zoningApi";

export default function CityPage() {
  const router = useRouter();
  const { id } = router.query;
  const [opened, { toggle }] = useDisclosure();
  const [inputValue, setInputValue] = useState("");
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [selectedZoning, setSelectedZoning] = useState<ZoningData[] | null>(
    null
  );
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  const { data: chats } = useChats(10);
  const { mutate: startChat, isPending: isStarting } = useStartChat();
  const { mutate: continueChat, isPending: isContinuing } = useContinueChat();
  const { mutate: fetchZoning, isPending: isLoadingZoning } =
    useZoningAtLocation();
  const { data: cityZoningData, isLoading: isCityZoningLoading } = useCityZoning(
    typeof id === "string" ? id : undefined
  );

  const isPending = isStarting || isContinuing;

  // Get current chat messages
  const currentChat = chats?.find((chat) => chat.chat_id === currentChatId);
  const messages = currentChat?.messages || [];

  // Add zoning polygons to map
  const addZoningLayer = useCallback((zoningData: ZoningData[]) => {
    if (!map.current) {
      console.log("Map not ready for adding zoning layer");
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

    // Create GeoJSON features from zoning data
    const features = zoningData
      .filter((z) => z.geometry)
      .map((z) => ({
        type: "Feature" as const,
        properties: {
          code: z.code || z.zoning_code,
          article: z.article,
          usage: z.usage,
        },
        geometry: z.geometry,
      }));

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

    // Add fill layer
    map.current.addLayer({
      id: "zoning-fill",
      type: "fill",
      source: "zoning",
      paint: {
        "fill-color": "#0080ff",
        "fill-opacity": 0.3,
      },
    });

    // Add outline layer
    map.current.addLayer({
      id: "zoning-outline",
      type: "line",
      source: "zoning",
      paint: {
        "line-color": "#0080ff",
        "line-width": 2,
      },
    });

    // Fit bounds to show all zoning areas
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
    map.current.fitBounds(bounds, { padding: 50 });
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
        setMapLoaded(true);
      });

      map.current.on("error", (e) => {
        console.error("Map error:", e);
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");

      // Add click handler to query zoning
      map.current.on("click", (e) => {
        const { lng, lat } = e.lngLat;

        // Add or update marker
        if (markerRef.current) {
          markerRef.current.remove();
        }
        markerRef.current = new maplibregl.Marker({ color: "#FF0000" })
          .setLngLat([lng, lat])
          .addTo(map.current!);

        // Fetch zoning data
        if (id && typeof id === "string") {
          fetchZoning(
            { city: id, latitude: lat, longitude: lng },
            {
              onSuccess: (data) => {
                setSelectedZoning(data.zoning_data);
                // Add zoning polygons to map
                addZoningLayer(data.zoning_data);
              },
              onError: (error) => {
                console.error("Error fetching zoning:", error);
                setSelectedZoning(null);
              },
            }
          );
        }
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
  }, [id, fetchZoning, addZoningLayer]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const content = inputValue;
    setInputValue("");

    if (!currentChatId) {
      // Start a new chat
      startChat(
        { content },
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
      // Continue existing chat
      continueChat(
        { chatId: currentChatId, request: { content } },
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

  const handleClearSelection = () => {
    // Clear selected zoning
    setSelectedZoning(null);

    // Remove marker from map
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    // Reload all city zoning data
    if (cityZoningData?.zoning_data && mapLoaded) {
      addZoningLayer(cityZoningData.zoning_data);
    }
  };

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
  }, [mapLoaded, cityZoningData, addZoningLayer]);

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

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 400,
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
            <Group>
              <IconMap size={28} />
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
                </Badge>
              ))}
              {isLoadingZoning && <Loader size="xs" />}
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
          {isLoadingZoning && !selectedZoning && (
            <Group gap="xs">
              <Loader size="xs" />
              <Text size="sm" c="dimmed">
                Loading zoning data...
              </Text>
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

      <AppShell.Main p={0} style={{ position: "relative", overflow: "hidden" }}>
        <div
          ref={mapContainer}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            width: "100%",
            height: "100%",
          }}
        />
      </AppShell.Main>
    </AppShell>
  );
}
