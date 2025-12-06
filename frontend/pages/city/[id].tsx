import { useRouter } from "next/router";
import { GetStaticProps, GetStaticPaths } from "next";
import Image from "next/image";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import {
  AppShell,
  Burger,
  Group,
  Title,
  Text,
  ActionIcon,
  Badge,
  Box,
} from "@mantine/core";
import { useDisclosure, useHotkeys, useMediaQuery, useLocalStorage } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { IconMapPin, IconX } from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import { useStartChat, useContinueChat, useChat } from "@/hooks/useChat";
import { ZoningData, CityZoningResponse, getCityZoningServerSide, zoningApi } from "@/services/zoningApi";
import { getCitiesServerSide, citiesApi } from "@/services/citiesApi";
import { OrdinanceSource, DevelopmentPlanSource } from "@/services/chatApi";
import { getZoneSubtypeColor } from "@/utils/zoningColors";
import { MapLegend } from "@/components/MapLegend";
import { FloatingChat } from "@/components/FloatingChat";
import { Sidebar, SidebarTab, DocumentTab, QueryTab, DocumentContentTab } from "@/components/sidebar";

interface CityPageProps {
  cityZoningData: CityZoningResponse;
}

// Sidebar width constraints for ordinance viewer
const MIN_SIDEBAR_WIDTH = 300;
const MAX_SIDEBAR_WIDTH = 800;
const DEFAULT_SIDEBAR_WIDTH = 450;

export default function CityPage({ cityZoningData }: CityPageProps) {
  const router = useRouter();
  const { id } = router.query;
  const [opened, { toggle }] = useDisclosure();
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [selectedZoning, setSelectedZoning] = useState<ZoningData[] | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  // Track development plan markers on the map
  const devPlanMarkersRef = useRef<maplibregl.Marker[]>([]);

  // Sidebar state - start collapsed by default
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [sidebarTabs, setSidebarTabs] = useState<SidebarTab[]>([
    { id: "browse", label: "Browse", type: "browse" },
  ]);
  const [activeTabId, setActiveTabId] = useState("browse");

  // Track sources per tab (keyed by tab id)
  // Now supports both ordinance and development plan sources
  const [tabSources, setTabSources] = useState<Record<string, {
    ordinances: OrdinanceSource[];
    developmentPlans: DevelopmentPlanSource[];
  }>>({});

  // Track full document content per tab (keyed by tab id)
  const [tabDocuments, setTabDocuments] = useState<Record<string, { title: string; subtitle: string; content: string }>>({});
  const [loadingDocumentTabId, setLoadingDocumentTabId] = useState<string | null>(null);

  // Track which messages have tabs (for reopening closed tabs)
  // Using ref to avoid re-renders when updating the map
  // Also stores location for highlighting the correct polygon
  const messageTabMapRef = useRef<Record<string, {
    tabId: string;
    ordinances: OrdinanceSource[];
    developmentPlans: DevelopmentPlanSource[];
    label: string;
    location?: { latitude: number; longitude: number };
  }>>({});
  // Simple set of message IDs that have sources (for UI display only)
  const [messagesWithSources, setMessagesWithSources] = useState<Set<string>>(new Set());

  // Resizable ordinance viewer
  const [sidebarWidth, setSidebarWidth] = useLocalStorage({
    key: "spatially-sidebar-width",
    defaultValue: DEFAULT_SIDEBAR_WIDTH,
  });
  const [isResizing, setIsResizing] = useState(false);
  const isMobile = useMediaQuery("(max-width: 768px)") ?? false;

  // Handle sidebar resize
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = e.clientX;
      if (newWidth >= MIN_SIDEBAR_WIDTH && newWidth <= MAX_SIDEBAR_WIDTH) {
        setSidebarWidth(newWidth);
        if (map.current) {
          map.current.resize();
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, setSidebarWidth]);

  const { data: currentChatData } = useChat(currentChatId);
  const { mutate: startChat, isPending: isStarting } = useStartChat();
  const { mutate: continueChat, isPending: isContinuing } = useContinueChat();

  // Track pending user message for optimistic UI
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);

  const isPending = isStarting || isContinuing;

  // Combine actual messages with pending user message for optimistic display
  const messages = useMemo(() => {
    const actualMessages = currentChatData?.messages || [];
    if (pendingUserMessage && isPending) {
      return [
        ...actualMessages,
        {
          message_id: "pending-user-message",
          role: "user" as const,
          content: pendingUserMessage,
        },
      ];
    }
    return actualMessages;
  }, [currentChatData?.messages, pendingUserMessage, isPending]);

  // Fetch documents for the city
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ["documents", id],
    queryFn: () => citiesApi.getDocuments(id as string),
    enabled: !!id && typeof id === "string",
  });

  // Add zoning polygons to map
  const addZoningLayer = useCallback((zoningData: ZoningData[], fitBounds = true) => {
    if (!map.current || !map.current.isStyleLoaded()) {
      return;
    }

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

    if (features.length === 0) {
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
        "fill-color": ["get", "color"],
        "fill-opacity": 0.5,
      },
    });

    // Add outline layer
    map.current.addLayer({
      id: "zoning-outline",
      type: "line",
      source: "zoning",
      paint: {
        "line-color": ["get", "color"],
        "line-width": 1.5,
      },
    });

    // Fit bounds
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
      map.current.resize();
      setTimeout(() => {
        map.current?.fitBounds(bounds, {
          padding: { top: 50, right: 50, bottom: 50, left: 50 },
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
      0.7,
      0.15,
    ]);

    map.current.setPaintProperty("zoning-outline", "line-opacity", [
      "case",
      ["in", ["get", "code"], ["literal", selectedCodes]],
      1,
      0.3,
    ]);

    map.current.setPaintProperty("zoning-outline", "line-width", [
      "case",
      ["in", ["get", "code"], ["literal", selectedCodes]],
      3,
      1,
    ]);
  }, []);

  // Reset zone highlighting
  const resetZoneHighlight = useCallback(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;
    map.current.setPaintProperty("zoning-fill", "fill-opacity", 0.5);
    map.current.setPaintProperty("zoning-outline", "line-opacity", 1);
    map.current.setPaintProperty("zoning-outline", "line-width", 1.5);
  }, []);

  // Clear all development plan markers from the map
  const clearDevPlanMarkers = useCallback(() => {
    devPlanMarkersRef.current.forEach((marker) => marker.remove());
    devPlanMarkersRef.current = [];
  }, []);

  // Show development plan locations on the map
  const showDevPlanMarkers = useCallback((plans: DevelopmentPlanSource[]) => {
    if (!map.current) return;

    // Clear existing markers first
    clearDevPlanMarkers();

    // Create markers for each plan with location
    const bounds = new maplibregl.LngLatBounds();
    let hasValidLocations = false;

    plans.forEach((plan, index) => {
      if (plan.latitude && plan.longitude) {
        hasValidLocations = true;

        // Create a custom marker element
        const el = document.createElement("div");
        el.className = "dev-plan-marker";
        el.style.cssText = `
          width: 24px;
          height: 24px;
          background-color: #40c057;
          border: 2px solid white;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
          color: white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        `;
        el.textContent = String(index + 1);
        el.title = plan.title;

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([plan.longitude, plan.latitude])
          .setPopup(
            new maplibregl.Popup({ offset: 25 }).setHTML(
              `<strong>${plan.title}</strong>${plan.subtitle ? `<br/><small>${plan.subtitle}</small>` : ""}${plan.distance_km != null ? `<br/><small>${plan.distance_km.toFixed(2)}km away</small>` : ""}`
            )
          )
          .addTo(map.current!);

        devPlanMarkersRef.current.push(marker);
        bounds.extend([plan.longitude, plan.latitude]);
      }
    });

    // Fit map to show all markers if we have valid locations
    if (hasValidLocations && !bounds.isEmpty()) {
      map.current.fitBounds(bounds, {
        padding: 100,
        maxZoom: 15,
      });
    }
  }, [clearDevPlanMarkers]);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    try {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [-71.0589, 42.3601],
        zoom: 12,
      });

      map.current.on("load", () => {
        setTimeout(() => {
          map.current?.resize();
          setTimeout(() => {
            map.current?.resize();
            setMapLoaded(true);
          }, 100);
        }, 100);
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");

      // Add click handler
      map.current.on("click", (e) => {
        const { lng, lat } = e.lngLat;

        const features = map.current!.queryRenderedFeatures(e.point, {
          layers: ["zoning-fill"],
        });

        if (features.length === 0) {
          setSelectedZoning(null);
          setSelectedLocation(null);
          if (markerRef.current) {
            markerRef.current.remove();
            markerRef.current = null;
          }
          resetZoneHighlight();
          return;
        }

        if (markerRef.current) {
          markerRef.current.remove();
        }
        markerRef.current = new maplibregl.Marker({ color: "#FF0000" })
          .setLngLat([lng, lat])
          .addTo(map.current!);

        setSelectedLocation({ latitude: lat, longitude: lng });

        const zoningData: ZoningData[] = features.map((f) => ({
          id: f.id as number,
          code: f.properties?.code,
          article: f.properties?.article,
          usage: f.properties?.usage,
          zone_subtype: f.properties?.zone_subtype,
          geometry: f.geometry,
        }));

        setSelectedZoning(zoningData);

        const selectedCodes = zoningData
          .map((z) => z.code)
          .filter(Boolean) as string[];
        highlightSelectedZones(selectedCodes);

        // Zoom to fit the selected zone(s)
        const bounds = new maplibregl.LngLatBounds();
        zoningData.forEach((zone) => {
          if (zone.geometry) {
            if (zone.geometry.type === "Polygon") {
              (zone.geometry.coordinates as number[][][])[0].forEach((coord) => {
                bounds.extend(coord as [number, number]);
              });
            } else if (zone.geometry.type === "MultiPolygon") {
              (zone.geometry.coordinates as number[][][][]).forEach((polygon) => {
                polygon[0].forEach((coord) => {
                  bounds.extend(coord as [number, number]);
                });
              });
            }
          }
        });

        if (!bounds.isEmpty()) {
          map.current!.fitBounds(bounds, {
            padding: { top: 100, right: 100, bottom: 100, left: 100 },
            maxZoom: 16,
            duration: 500,
          });
        }
      });
    } catch (error) {
      console.error("Failed to initialize map:", error);
    }

    return () => {
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

  // Tab management functions
  const handleTabChange = useCallback((tabId: string) => {
    setActiveTabId(tabId);

    // If switching to a results tab, handle zoning/location display
    if (tabId.startsWith("results-")) {
      const messageId = tabId.replace("results-", "");
      const tabData = messageTabMapRef.current[messageId];

      // Check if this tab has ordinance sources (zoning data)
      const hasOrdinances = tabData?.ordinances && tabData.ordinances.length > 0;
      const hasDevPlans = tabData?.developmentPlans && tabData.developmentPlans.length > 0;

      // If tab only has development plans (no ordinances), clear zoning selection
      if (!hasOrdinances && hasDevPlans) {
        setSelectedZoning(null);
        setSelectedLocation(null);
        resetZoneHighlight();
        if (markerRef.current) {
          markerRef.current.remove();
          markerRef.current = null;
        }
        // Development plan markers will be shown by the useEffect that watches activeTabSources
        return;
      }

      // If tab has ordinances and a stored location, zoom to it
      if (hasOrdinances && tabData?.location && map.current && cityZoningData?.zoning_data) {
        const { latitude, longitude } = tabData.location;

        // Fly to the location
        map.current.flyTo({
          center: [longitude, latitude],
          zoom: 15,
          duration: 500,
        });

        // Query the map for features at this point after the fly animation
        setTimeout(() => {
          if (!map.current) return;
          const point = map.current.project([longitude, latitude]);
          const features = map.current.queryRenderedFeatures(point, {
            layers: ["zoning-fill"],
          });

          if (features.length > 0) {
            const zoningData: ZoningData[] = features.map((f) => ({
              id: f.id as number,
              code: f.properties?.code,
              article: f.properties?.article,
              usage: f.properties?.usage,
              zone_subtype: f.properties?.zone_subtype,
              geometry: f.geometry,
            }));

            const selectedCodes = zoningData
              .map((z) => z.code)
              .filter(Boolean) as string[];

            highlightSelectedZones(selectedCodes);
            setSelectedZoning(zoningData);
            setSelectedLocation({ latitude, longitude });

            // Update marker
            if (markerRef.current) {
              markerRef.current.remove();
            }
            markerRef.current = new maplibregl.Marker({ color: "#FF0000" })
              .setLngLat([longitude, latitude])
              .addTo(map.current!);
          }
        }, 600); // Wait for fly animation to complete
      }
    }
  }, [cityZoningData, highlightSelectedZones, resetZoneHighlight]);

  const handleTabClose = useCallback((tabId: string) => {
    setSidebarTabs((prev) => prev.filter((t) => t.id !== tabId));
    setTabSources((prev) => {
      const next = { ...prev };
      delete next[tabId];
      return next;
    });
    setTabDocuments((prev) => {
      const next = { ...prev };
      delete next[tabId];
      return next;
    });
    // Switch to browse tab if closing active tab
    if (activeTabId === tabId) {
      setActiveTabId("browse");
    }
  }, [activeTabId]);

  const createResultsTab = useCallback((
    ordinances: OrdinanceSource[],
    developmentPlans: DevelopmentPlanSource[],
    messageId: string,
    label: string,
    location?: { latitude: number; longitude: number }
  ) => {
    const tabId = `results-${messageId}`;

    // Store in ref for reopening later (doesn't cause re-render)
    messageTabMapRef.current[messageId] = { tabId, ordinances, developmentPlans, label, location };

    // Update the set of messages with sources (for UI)
    setMessagesWithSources((prev) => new Set(prev).add(messageId));

    // Check if tab already exists
    setSidebarTabs((prev) => {
      const exists = prev.find((t) => t.id === tabId);
      if (exists) {
        return prev;
      }
      return [...prev, { id: tabId, label, type: "results", messageId }];
    });

    // Store sources for this tab
    setTabSources((prev) => ({
      ...prev,
      [tabId]: { ordinances, developmentPlans },
    }));

    // Switch to the new tab and expand sidebar
    setActiveTabId(tabId);
    setSidebarCollapsed(false);
  }, []);

  // Handle clicking on a chat message to reopen its tab and highlight zones
  const handleMessageClick = useCallback((messageId: string) => {
    const tabData = messageTabMapRef.current[messageId];
    if (!tabData) return;

    // If we have a stored location, use it to find the specific polygon
    if (tabData.location && map.current && cityZoningData?.zoning_data) {
      const { latitude, longitude } = tabData.location;
      const point = map.current.project([longitude, latitude]);

      // Query the map for features at this point
      const features = map.current.queryRenderedFeatures(point, {
        layers: ["zoning-fill"],
      });

      if (features.length > 0) {
        const zoningData: ZoningData[] = features.map((f) => ({
          id: f.id as number,
          code: f.properties?.code,
          article: f.properties?.article,
          usage: f.properties?.usage,
          zone_subtype: f.properties?.zone_subtype,
          geometry: f.geometry,
        }));

        const selectedCodes = zoningData
          .map((z) => z.code)
          .filter(Boolean) as string[];

        // Highlight the zone(s) on the map
        highlightSelectedZones(selectedCodes);

        // Set selected zoning for UI display
        setSelectedZoning(zoningData);

        // Update marker position
        if (markerRef.current) {
          markerRef.current.remove();
        }
        markerRef.current = new maplibregl.Marker({ color: "#FF0000" })
          .setLngLat([longitude, latitude])
          .addTo(map.current);

        // Set selected location
        setSelectedLocation({ latitude, longitude });

        // Calculate bounds and zoom to fit
        const bounds = new maplibregl.LngLatBounds();
        zoningData.forEach((zone) => {
          if (zone.geometry) {
            if (zone.geometry.type === "Polygon") {
              (zone.geometry.coordinates as number[][][])[0].forEach((coord) => {
                bounds.extend(coord as [number, number]);
              });
            } else if (zone.geometry.type === "MultiPolygon") {
              (zone.geometry.coordinates as number[][][][]).forEach((polygon) => {
                polygon[0].forEach((coord) => {
                  bounds.extend(coord as [number, number]);
                });
              });
            }
          }
        });

        if (!bounds.isEmpty()) {
          map.current.fitBounds(bounds, {
            padding: { top: 100, right: 100, bottom: 100, left: 100 },
            maxZoom: 16,
            duration: 500,
          });
        }
      }
    }

    // Check if tab still exists by looking at current tabs
    setSidebarTabs((currentTabs) => {
      const existingTab = currentTabs.find((t) => t.id === tabData.tabId);
      if (existingTab) {
        // Tab exists, just switch to it
        setActiveTabId(tabData.tabId);
        setSidebarCollapsed(false);
        return currentTabs;
      } else {
        // Reopen the tab
        setTabSources((prev) => ({
          ...prev,
          [tabData.tabId]: {
            ordinances: tabData.ordinances,
            developmentPlans: tabData.developmentPlans,
          },
        }));
        setActiveTabId(tabData.tabId);
        setSidebarCollapsed(false);
        return [...currentTabs, { id: tabData.tabId, label: tabData.label, type: "results", messageId }];
      }
    });
  }, [cityZoningData, highlightSelectedZones]);

  const handleDocumentSelect = useCallback(async (title: string, subtitle: string) => {
    if (!id || typeof id !== "string") return;

    // Create a unique tab ID for this document
    const tabId = `doc-${title}-${subtitle}`.replace(/\s+/g, "-").toLowerCase();

    // Check if tab already exists
    const existingTab = sidebarTabs.find((t) => t.id === tabId);
    if (existingTab) {
      setActiveTabId(tabId);
      setSidebarCollapsed(false);
      return;
    }

    // Create new tab
    const label = subtitle ? `${title} - ${subtitle}` : title;
    const truncatedLabel = label.length > 25 ? label.slice(0, 25) + "..." : label;

    setSidebarTabs((prev) => [
      ...prev,
      { id: tabId, label: truncatedLabel, type: "document" },
    ]);
    setActiveTabId(tabId);
    setSidebarCollapsed(false);
    setLoadingDocumentTabId(tabId);

    try {
      const response = await zoningApi.getFullDocument(id, title, subtitle);
      setTabDocuments((prev) => ({
        ...prev,
        [tabId]: {
          title: response.title,
          subtitle: response.subtitle,
          content: response.content,
        },
      }));
    } catch (error) {
      console.error("Failed to fetch document:", error);
      // Remove the tab on error
      setSidebarTabs((prev) => prev.filter((t) => t.id !== tabId));
      setActiveTabId("browse");
    } finally {
      setLoadingDocumentTabId(null);
    }
  }, [id, sidebarTabs]);

  const handleSendMessage = useCallback((content: string) => {
    if (!content.trim() || !id || typeof id !== "string") return;

    // Show user message immediately (optimistic update)
    setPendingUserMessage(content);

    // Capture location at time of sending for use in callback
    const messageLocation = selectedLocation ? { ...selectedLocation } : undefined;

    if (!currentChatId) {
      startChat(
        {
          content,
          city: id,
          latitude: selectedLocation?.latitude,
          longitude: selectedLocation?.longitude,
        },
        {
          onSuccess: (data) => {
            setPendingUserMessage(null); // Clear pending message
            setCurrentChatId(data.chat_id);
            // Create new tab with sources if any exist
            const hasOrdinances = data.ordinance_sources && data.ordinance_sources.length > 0;
            const hasDevPlans = data.development_plan_sources && data.development_plan_sources.length > 0;
            if (hasOrdinances || hasDevPlans) {
              const lastMessage = data.messages[data.messages.length - 1];
              const label = content.slice(0, 20) + (content.length > 20 ? "..." : "");
              createResultsTab(
                data.ordinance_sources || [],
                data.development_plan_sources || [],
                lastMessage.message_id,
                label,
                messageLocation
              );
            }
          },
          onError: () => {
            setPendingUserMessage(null); // Clear pending message on error
          },
        }
      );
    } else {
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
          onSuccess: (data) => {
            setPendingUserMessage(null); // Clear pending message
            // Create new tab with sources if any exist
            const hasOrdinances = data.ordinance_sources && data.ordinance_sources.length > 0;
            const hasDevPlans = data.development_plan_sources && data.development_plan_sources.length > 0;
            if (hasOrdinances || hasDevPlans) {
              const lastMessage = data.messages[data.messages.length - 1];
              const label = content.slice(0, 20) + (content.length > 20 ? "..." : "");
              createResultsTab(
                data.ordinance_sources || [],
                data.development_plan_sources || [],
                lastMessage.message_id,
                label,
                messageLocation
              );
            }
          },
          onError: () => {
            setPendingUserMessage(null); // Clear pending message on error
          },
        }
      );
    }
  }, [id, currentChatId, selectedLocation, startChat, continueChat, createResultsTab]);

  const handleClearSelection = useCallback(() => {
    setSelectedZoning(null);
    setSelectedLocation(null);

    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    resetZoneHighlight();
  }, [resetZoneHighlight]);

  // Handle clicking on a development plan location to fly to it
  const handlePlanLocationClick = useCallback((lat: number, lng: number) => {
    if (!map.current) return;

    map.current.flyTo({
      center: [lng, lat],
      zoom: 16,
      duration: 1000,
    });

    // Find the marker at this location and open its popup
    devPlanMarkersRef.current.forEach((marker) => {
      const markerLngLat = marker.getLngLat();
      if (Math.abs(markerLngLat.lat - lat) < 0.0001 && Math.abs(markerLngLat.lng - lng) < 0.0001) {
        marker.togglePopup();
      }
    });
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  // Handle clicking on a zoning code in the QueryTab to highlight on map
  const handleZoningCodeClick = useCallback((code: string) => {
    if (!cityZoningData?.zoning_data) return;

    // Find the zoning data for this code
    const zoningData = cityZoningData.zoning_data.filter(
      (z) => z.code === code || z.zoning_code === code
    );

    if (zoningData.length === 0) return;

    // Highlight the zone(s) on the map
    highlightSelectedZones([code]);

    // Set selected zoning for UI display
    setSelectedZoning(zoningData);

    // Calculate bounds and zoom to fit
    if (map.current) {
      const bounds = new maplibregl.LngLatBounds();
      zoningData.forEach((zone) => {
        if (zone.geometry) {
          if (zone.geometry.type === "Polygon") {
            (zone.geometry.coordinates as number[][][])[0].forEach((coord) => {
              bounds.extend(coord as [number, number]);
            });
          } else if (zone.geometry.type === "MultiPolygon") {
            (zone.geometry.coordinates as number[][][][]).forEach((polygon) => {
              polygon[0].forEach((coord) => {
                bounds.extend(coord as [number, number]);
              });
            });
          }
        }
      });

      if (!bounds.isEmpty()) {
        map.current.fitBounds(bounds, {
          padding: { top: 100, right: 100, bottom: 100, left: 100 },
          maxZoom: 16,
          duration: 500,
        });
      }
    }
  }, [cityZoningData, highlightSelectedZones]);

  // Get sources for active tab
  const activeTabSources = tabSources[activeTabId] || { ordinances: [], developmentPlans: [] };

  // Show development plan markers when viewing a results tab with dev plans
  useEffect(() => {
    if (!mapLoaded) return;

    const activeTab = sidebarTabs.find((t) => t.id === activeTabId);
    const isResultsTab = activeTab?.type === "results";

    if (isResultsTab && activeTabSources.developmentPlans.length > 0 && !sidebarCollapsed) {
      showDevPlanMarkers(activeTabSources.developmentPlans);
    } else {
      clearDevPlanMarkers();
    }
  }, [activeTabId, activeTabSources.developmentPlans, sidebarTabs, mapLoaded, sidebarCollapsed, showDevPlanMarkers, clearDevPlanMarkers]);

  // Load city zoning data when available and map is ready
  useEffect(() => {
    if (mapLoaded && cityZoningData?.zoning_data && cityZoningData.zoning_data.length > 0) {
      addZoningLayer(cityZoningData.zoning_data);
    }
  }, [mapLoaded, cityZoningData, addZoningLayer]);

  // Handle escape key to deselect
  useHotkeys([["Escape", handleClearSelection]]);

  // Calculate map offset based on sidebar
  const mapLeftOffset = !sidebarCollapsed && !isMobile ? sidebarWidth : 0;

  return (
    <AppShell
      header={{ height: 60 }}
      padding={0}
      styles={{
        root: { height: "100vh", overflow: "hidden" },
        main: { height: "100%", overflow: "hidden" },
      }}
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

      <AppShell.Main>
        {/* Sidebar with tabs */}
        <Sidebar
          tabs={sidebarTabs}
          activeTabId={activeTabId}
          onTabChange={handleTabChange}
          onTabClose={handleTabClose}
          width={sidebarWidth}
          isResizing={isResizing}
          onResizeStart={handleMouseDown}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
          isMobile={isMobile}
        >
          {activeTabId === "browse" ? (
            <DocumentTab
              documents={documentsData?.documents || []}
              isLoading={documentsLoading}
              onDocumentSelect={handleDocumentSelect}
            />
          ) : activeTabId.startsWith("doc-") ? (
            <DocumentContentTab
              title={tabDocuments[activeTabId]?.title || ""}
              subtitle={tabDocuments[activeTabId]?.subtitle}
              content={tabDocuments[activeTabId]?.content || ""}
              isLoading={loadingDocumentTabId === activeTabId}
            />
          ) : (
            <QueryTab
              ordinanceSources={activeTabSources.ordinances}
              developmentPlanSources={activeTabSources.developmentPlans}
              onZoningCodeClick={handleZoningCodeClick}
              onPlanLocationClick={handlePlanLocationClick}
            />
          )}
        </Sidebar>

        {/* Map Container */}
        <Box
          style={{
            position: "fixed",
            top: 60,
            left: mapLeftOffset,
            right: 0,
            bottom: 0,
            transition: !sidebarCollapsed ? "left 0.3s ease" : "none",
          }}
        >
          <div
            ref={mapContainer}
            style={{
              width: "100%",
              height: "100%",
            }}
          />
          <MapLegend zoningData={selectedZoning || cityZoningData?.zoning_data} />

          {/* Floating Chat */}
          <FloatingChat
            messages={messages}
            isPending={isPending}
            onSendMessage={handleSendMessage}
            selectedZoning={selectedZoning}
            messagesWithSources={messagesWithSources}
            onMessageClick={handleMessageClick}
          />
        </Box>
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
    revalidate: 3600,
  };
};
