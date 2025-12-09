import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import {
  AppShell,
  Group,
  Title,
  Text,
  Box,
  Paper,
  Stack,
  Button,
  Progress,
  Badge,
  Stepper,
  Card,
  ThemeIcon,
  Divider,
  Alert,
  rem,
  Table,
  ScrollArea,
  TextInput,
} from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE, PDF_MIME_TYPE } from "@mantine/dropzone";
import {
  IconUpload,
  IconPhoto,
  IconX,
  IconFileTypePdf,
  IconMap,
  IconDownload,
  IconCheck,
  IconInfoCircle,
  IconRefresh,
  IconFileText,
  IconCode,
  IconWorld,
  IconExternalLink,
  IconBuilding,
} from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import { getZoneSubtypeColor } from "@/utils/zoningColors";
import { zoningApi, ZoningData } from "@/services/zoningApi";

// Mock extracted zoning codes from ordinance (Phase 1 result)
const MOCK_EXTRACTED_CODES = [
  {
    code: "R-1",
    name: "Single Family Residential",
    description: "Low density residential district for single-family dwellings",
    maxHeight: "35 ft",
    minLotSize: "10,000 sq ft",
    setbacks: "Front: 25ft, Side: 10ft, Rear: 20ft",
  },
  {
    code: "R-2",
    name: "Multi-Family Residential",
    description: "Medium density residential district allowing multi-family dwellings",
    maxHeight: "45 ft",
    minLotSize: "5,000 sq ft",
    setbacks: "Front: 20ft, Side: 8ft, Rear: 15ft",
  },
  {
    code: "C-1",
    name: "General Commercial",
    description: "Commercial district for retail and service businesses",
    maxHeight: "60 ft",
    minLotSize: "2,500 sq ft",
    setbacks: "Front: 0ft, Side: 0ft, Rear: 10ft",
  },
  {
    code: "I-1",
    name: "Light Industrial",
    description: "Industrial district for manufacturing and warehousing",
    maxHeight: "50 ft",
    minLotSize: "20,000 sq ft",
    setbacks: "Front: 30ft, Side: 15ft, Rear: 25ft",
  },
  {
    code: "OS",
    name: "Open Space",
    description: "Protected areas for parks, recreation, and conservation",
    maxHeight: "25 ft",
    minLotSize: "N/A",
    setbacks: "Varies",
  },
  {
    code: "MU",
    name: "Mixed Use",
    description: "District allowing combination of residential and commercial uses",
    maxHeight: "75 ft",
    minLotSize: "3,000 sq ft",
    setbacks: "Front: 10ft, Side: 5ft, Rear: 10ft",
  },
];

// GeoJSON Feature type
interface ZoneFeature {
  type: "Feature";
  properties: {
    code: string;
    zone_subtype: string;
    color: string;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
}

interface ZoneFeatureCollection {
  type: "FeatureCollection";
  features: ZoneFeature[];
}

// Convert zoning data from API to GeoJSON FeatureCollection
const convertToGeoJSON = (zoningData: ZoningData[]): ZoneFeatureCollection => {
  const features: ZoneFeature[] = zoningData
    .filter((z) => z.geometry)
    .map((z) => {
      const color = getZoneSubtypeColor(z.zone_subtype);
      return {
        type: "Feature" as const,
        properties: {
          code: z.code || z.zoning_code || "Unknown",
          zone_subtype: z.zone_subtype || "Unknown",
          color: color,
        },
        geometry: z.geometry,
      };
    });

  return {
    type: "FeatureCollection" as const,
    features,
  };
};

// Fetch real zoning data from backend (uses Cambridge as sample)
const fetchSampleZoningData = async (): Promise<ZoneFeatureCollection> => {
  try {
    const response = await zoningApi.getAllZoningForCity("cambridge");
    return convertToGeoJSON(response.zoning_data);
  } catch (error) {
    console.error("Failed to fetch zoning data:", error);
    // Return empty collection on error
    return { type: "FeatureCollection", features: [] };
  }
};

interface UploadedFile {
  file: File;
  preview: string;
}

type ProcessingPhase = "upload" | "phase1" | "phase2" | "phase3" | "complete";

export default function ConvertPage() {
  const router = useRouter();

  // File uploads
  const [ordinanceFile, setOrdinanceFile] = useState<UploadedFile | null>(null);
  const [mapFile, setMapFile] = useState<UploadedFile | null>(null);

  // Processing state
  const [currentPhase, setCurrentPhase] = useState<ProcessingPhase>("upload");
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState("");

  // Results
  const [extractedCodes, setExtractedCodes] = useState<typeof MOCK_EXTRACTED_CODES | null>(null);
  const [convertedGeoJSON, setConvertedGeoJSON] = useState<ZoneFeatureCollection | null>(null);
  const [municipalityName, setMunicipalityName] = useState("");
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);

  // Map state
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    try {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [-71.0589, 42.3601],
        zoom: 13,
      });

      map.current.on("load", () => {
        setTimeout(() => {
          map.current?.resize();
          setMapLoaded(true);
        }, 100);
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    } catch (error) {
      console.error("Failed to initialize map:", error);
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // Add converted zones to map
  const addConvertedZonesToMap = useCallback(
    (geoJSON: ZoneFeatureCollection) => {
      if (!map.current || !mapLoaded) return;

      // Remove existing layers
      if (map.current.getLayer("converted-fill")) {
        map.current.removeLayer("converted-fill");
      }
      if (map.current.getLayer("converted-outline")) {
        map.current.removeLayer("converted-outline");
      }
      if (map.current.getSource("converted")) {
        map.current.removeSource("converted");
      }

      // Add source and layers
      map.current.addSource("converted", {
        type: "geojson",
        data: geoJSON as GeoJSON.FeatureCollection,
      });

      map.current.addLayer({
        id: "converted-fill",
        type: "fill",
        source: "converted",
        paint: {
          "fill-color": ["get", "color"],
          "fill-opacity": 0.6,
        },
      });

      map.current.addLayer({
        id: "converted-outline",
        type: "line",
        source: "converted",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 2,
        },
      });

      // Fit bounds to show all features
      const bounds = new maplibregl.LngLatBounds();
      geoJSON.features.forEach((feature) => {
        if (feature.geometry.type === "Polygon") {
          (feature.geometry.coordinates as number[][][])[0].forEach((coord) => {
            bounds.extend(coord as [number, number]);
          });
        } else if (feature.geometry.type === "MultiPolygon") {
          (feature.geometry.coordinates as number[][][][]).forEach((polygon) => {
            polygon[0].forEach((coord) => {
              bounds.extend(coord as [number, number]);
            });
          });
        }
      });
      if (!bounds.isEmpty()) {
        map.current.fitBounds(bounds, { padding: 50 });
      }
    },
    [mapLoaded]
  );

  // Show converted zones when available
  useEffect(() => {
    if (convertedGeoJSON && mapLoaded) {
      addConvertedZonesToMap(convertedGeoJSON);
    }
  }, [convertedGeoJSON, mapLoaded, addConvertedZonesToMap]);

  const handleOrdinanceDrop = useCallback((files: File[]) => {
    const file = files[0];
    if (!file) return;
    const preview = URL.createObjectURL(file);
    setOrdinanceFile({ file, preview });
  }, []);

  const handleMapDrop = useCallback((files: File[]) => {
    const file = files[0];
    if (!file) return;
    const preview = URL.createObjectURL(file);
    setMapFile({ file, preview });
  }, []);

  // Phase 2: Convert map to GeoJSON
  const runPhase2 = useCallback(async () => {
    setCurrentPhase("phase2");
    setProcessingProgress(0);

    const steps = [
      { progress: 10, status: "Analyzing map image..." },
      { progress: 25, status: "Detecting zone boundaries..." },
      { progress: 40, status: "Extracting zone labels and colors..." },
      { progress: 55, status: "Converting to vector format..." },
      { progress: 70, status: "Georeferencing zones..." },
      { progress: 85, status: "Validating topology..." },
      { progress: 95, status: "Generating GeoJSON..." },
    ];

    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      setProcessingProgress(step.progress);
      setProcessingStatus(step.status);
    }

    // Fetch real zoning data from the database as demo
    const geoJSON = await fetchSampleZoningData();
    setConvertedGeoJSON(geoJSON);

    setProcessingProgress(100);
    setProcessingStatus("Map conversion complete!");

    await new Promise((resolve) => setTimeout(resolve, 500));
    setCurrentPhase("phase3");
    setProcessingProgress(0);
  }, []);

  // Phase 1: Extract zoning codes from ordinance
  const runPhase1 = useCallback(async () => {
    setCurrentPhase("phase1");
    setProcessingProgress(0);

    const steps = [
      { progress: 15, status: "Parsing PDF document..." },
      { progress: 30, status: "Identifying zoning sections..." },
      { progress: 50, status: "Extracting zoning codes and regulations..." },
      { progress: 70, status: "Analyzing dimensional requirements..." },
      { progress: 85, status: "Building zoning code database..." },
      { progress: 100, status: "Extraction complete!" },
    ];

    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      setProcessingProgress(step.progress);
      setProcessingStatus(step.status);
    }

    setExtractedCodes(MOCK_EXTRACTED_CODES);
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Always proceed to phase 2 (map conversion)
    runPhase2();
  }, [runPhase2]);

  // Phase 3: Publish interactive website
  const runPhase3 = useCallback(async () => {
    if (!municipalityName.trim()) {
      return;
    }

    setCurrentPhase("phase3");
    setProcessingProgress(0);

    const steps = [
      { progress: 20, status: "Generating interactive map viewer..." },
      { progress: 40, status: "Linking zoning codes to map layers..." },
      { progress: 60, status: "Creating search functionality..." },
      { progress: 80, status: "Setting up public hosting..." },
      { progress: 100, status: "Website published!" },
    ];

    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setProcessingProgress(step.progress);
      setProcessingStatus(step.status);
    }

    const slug = municipalityName.toLowerCase().replace(/\s+/g, "-");
    setPublishedUrl(`https://spatially.zone/${slug}`);

    await new Promise((resolve) => setTimeout(resolve, 500));
    setCurrentPhase("complete");
  }, [municipalityName]);

  const handleStartProcessing = useCallback(() => {
    // Always run both phases - phase 1 extracts codes, phase 2 converts map
    // Both are mocked but show real polygon data at the end
    runPhase1();
  }, [runPhase1]);

  const handleReset = useCallback(() => {
    if (ordinanceFile) URL.revokeObjectURL(ordinanceFile.preview);
    if (mapFile) URL.revokeObjectURL(mapFile.preview);

    setOrdinanceFile(null);
    setMapFile(null);
    setCurrentPhase("upload");
    setProcessingProgress(0);
    setProcessingStatus("");
    setExtractedCodes(null);
    setConvertedGeoJSON(null);
    setMunicipalityName("");
    setPublishedUrl(null);

    // Clear map layers
    if (map.current) {
      if (map.current.getLayer("converted-fill")) {
        map.current.removeLayer("converted-fill");
      }
      if (map.current.getLayer("converted-outline")) {
        map.current.removeLayer("converted-outline");
      }
      if (map.current.getSource("converted")) {
        map.current.removeSource("converted");
      }
    }
  }, [ordinanceFile, mapFile]);

  const handleExportGeoJSON = useCallback(() => {
    if (!convertedGeoJSON) return;

    const blob = new Blob([JSON.stringify(convertedGeoJSON, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${municipalityName || "zoning"}_map.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  }, [convertedGeoJSON, municipalityName]);

  const handleExportCodes = useCallback(() => {
    if (!extractedCodes) return;

    const blob = new Blob([JSON.stringify(extractedCodes, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${municipalityName || "zoning"}_codes.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [extractedCodes, municipalityName]);

  const getStepperActive = () => {
    switch (currentPhase) {
      case "upload": return 0;
      case "phase1": return 1;
      case "phase2": return 2;
      case "phase3": return 3;
      case "complete": return 4;
      default: return 0;
    }
  };

  const isProcessing = currentPhase === "phase1" || currentPhase === "phase2" || (currentPhase === "phase3" && processingProgress > 0 && processingProgress < 100);

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
            <Group
              style={{ cursor: "pointer" }}
              onClick={() => router.push("/")}
            >
              <Image src="/icon.png" alt="Spatially" width={40} height={40} />
              <Title order={3}>Spatially Zoning</Title>
            </Group>
            <Badge color="violet" variant="light" size="lg">
              GIS Converter
            </Badge>
          </Group>
          <Text size="sm" c="dimmed">
            Free for municipalities
          </Text>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        {/* Left Panel - Upload & Controls */}
        <Paper
          shadow="md"
          style={{
            position: "fixed",
            top: 60,
            left: 0,
            width: 480,
            height: "calc(100vh - 60px)",
            zIndex: 100,
            overflow: "auto",
            borderRight: "1px solid var(--mantine-color-gray-3)",
          }}
        >
          <ScrollArea h="calc(100vh - 60px)">
            <Stack p="md" gap="md">
              {/* Header */}
              <Box>
                <Group gap="xs" mb="xs">
                  <ThemeIcon size="lg" color="violet" variant="light">
                    <IconMap size={20} />
                  </ThemeIcon>
                  <Title order={4}>Zoning Map Generator</Title>
                </Group>
                <Text size="sm" c="dimmed">
                  Transform your zoning ordinances and maps into an interactive digital platform
                </Text>
              </Box>

              <Divider />

              {/* Stepper */}
              <Stepper
                active={getStepperActive()}
                size="sm"
                orientation="horizontal"
              >
                <Stepper.Step label="Upload" icon={<IconUpload size={16} />} />
                <Stepper.Step
                  label="Extract Codes"
                  icon={<IconFileText size={16} />}
                  loading={currentPhase === "phase1" && isProcessing}
                />
                <Stepper.Step
                  label="Convert Map"
                  icon={<IconMap size={16} />}
                  loading={currentPhase === "phase2" && isProcessing}
                />
                <Stepper.Step
                  label="Publish"
                  icon={<IconWorld size={16} />}
                  loading={currentPhase === "phase3" && isProcessing}
                />
              </Stepper>

              <Divider />

              {/* Upload Section */}
              {currentPhase === "upload" && (
                <Stack gap="md">
                  <Alert
                    icon={<IconInfoCircle size={16} />}
                    color="blue"
                    variant="light"
                  >
                    <Text size="sm">
                      Upload your zoning ordinance document and/or zoning map to get started.
                      Our AI will extract zoning codes and convert maps to GIS format.
                    </Text>
                  </Alert>

                  {/* Ordinance Upload */}
                  <Box>
                    <Group gap="xs" mb="xs">
                      <IconFileText size={18} />
                      <Text fw={500} size="sm">Zoning Ordinance (PDF)</Text>
                    </Group>
                    <Dropzone
                      onDrop={handleOrdinanceDrop}
                      accept={PDF_MIME_TYPE}
                      maxSize={50 * 1024 ** 2}
                      multiple={false}
                      style={{
                        border: ordinanceFile
                          ? "2px solid var(--mantine-color-green-5)"
                          : undefined,
                      }}
                    >
                      <Group
                        justify="center"
                        gap="md"
                        mih={100}
                        style={{ pointerEvents: "none" }}
                      >
                        <Dropzone.Accept>
                          <IconUpload
                            style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-blue-6)" }}
                            stroke={1.5}
                          />
                        </Dropzone.Accept>
                        <Dropzone.Reject>
                          <IconX
                            style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-red-6)" }}
                            stroke={1.5}
                          />
                        </Dropzone.Reject>
                        <Dropzone.Idle>
                          {ordinanceFile ? (
                            <IconCheck
                              style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-green-6)" }}
                              stroke={1.5}
                            />
                          ) : (
                            <IconFileTypePdf
                              style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-dimmed)" }}
                              stroke={1.5}
                            />
                          )}
                        </Dropzone.Idle>
                        <div>
                          <Text size="sm" inline ta="center">
                            {ordinanceFile ? ordinanceFile.file.name : "Drop zoning ordinance PDF"}
                          </Text>
                          <Text size="xs" c="dimmed" inline mt={4}>
                            {ordinanceFile ? "Click to replace" : "Extract zoning codes automatically"}
                          </Text>
                        </div>
                      </Group>
                    </Dropzone>
                    {ordinanceFile && (
                      <Group justify="flex-end" mt="xs">
                        <Button
                          size="xs"
                          variant="subtle"
                          color="red"
                          leftSection={<IconX size={14} />}
                          onClick={() => {
                            URL.revokeObjectURL(ordinanceFile.preview);
                            setOrdinanceFile(null);
                          }}
                        >
                          Remove
                        </Button>
                      </Group>
                    )}
                  </Box>

                  {/* Map Upload */}
                  <Box>
                    <Group gap="xs" mb="xs">
                      <IconMap size={18} />
                      <Text fw={500} size="sm">Zoning Map (PDF/Image)</Text>
                    </Group>
                    <Dropzone
                      onDrop={handleMapDrop}
                      accept={[...IMAGE_MIME_TYPE, ...PDF_MIME_TYPE]}
                      maxSize={50 * 1024 ** 2}
                      multiple={false}
                      style={{
                        border: mapFile
                          ? "2px solid var(--mantine-color-green-5)"
                          : undefined,
                      }}
                    >
                      <Group
                        justify="center"
                        gap="md"
                        mih={100}
                        style={{ pointerEvents: "none" }}
                      >
                        <Dropzone.Accept>
                          <IconUpload
                            style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-blue-6)" }}
                            stroke={1.5}
                          />
                        </Dropzone.Accept>
                        <Dropzone.Reject>
                          <IconX
                            style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-red-6)" }}
                            stroke={1.5}
                          />
                        </Dropzone.Reject>
                        <Dropzone.Idle>
                          {mapFile ? (
                            <IconCheck
                              style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-green-6)" }}
                              stroke={1.5}
                            />
                          ) : (
                            <IconPhoto
                              style={{ width: rem(40), height: rem(40), color: "var(--mantine-color-dimmed)" }}
                              stroke={1.5}
                            />
                          )}
                        </Dropzone.Idle>
                        <div>
                          <Text size="sm" inline ta="center">
                            {mapFile ? mapFile.file.name : "Drop zoning map here"}
                          </Text>
                          <Text size="xs" c="dimmed" inline mt={4}>
                            {mapFile ? "Click to replace" : "PDF, PNG, JPG supported"}
                          </Text>
                        </div>
                      </Group>
                    </Dropzone>
                    {mapFile && (
                      <Group justify="flex-end" mt="xs">
                        <Button
                          size="xs"
                          variant="subtle"
                          color="red"
                          leftSection={<IconX size={14} />}
                          onClick={() => {
                            URL.revokeObjectURL(mapFile.preview);
                            setMapFile(null);
                          }}
                        >
                          Remove
                        </Button>
                      </Group>
                    )}
                  </Box>

                  {/* Preview uploaded image */}
                  {mapFile && mapFile.file.type !== "application/pdf" && (
                    <Card withBorder padding="xs">
                      <Text size="xs" fw={500} mb="xs">Map Preview</Text>
                      <Box style={{ maxHeight: 150, overflow: "hidden", borderRadius: 8 }}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={mapFile.preview}
                          alt="Map Preview"
                          style={{ width: "100%", height: "auto", objectFit: "contain" }}
                        />
                      </Box>
                    </Card>
                  )}

                  <Button
                    size="lg"
                    leftSection={<IconCode size={20} />}
                    disabled={!ordinanceFile && !mapFile}
                    onClick={handleStartProcessing}
                    color="violet"
                  >
                    Start Processing
                  </Button>
                </Stack>
              )}

              {/* Processing Section */}
              {isProcessing && (
                <Stack gap="md">
                  <Card withBorder padding="lg">
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text fw={500}>
                          {currentPhase === "phase1" && "Extracting Zoning Codes..."}
                          {currentPhase === "phase2" && "Converting Map to GeoJSON..."}
                          {currentPhase === "phase3" && "Publishing Website..."}
                        </Text>
                        <Badge color="violet">{processingProgress}%</Badge>
                      </Group>
                      <Progress
                        value={processingProgress}
                        size="lg"
                        radius="xl"
                        color="violet"
                        animated
                      />
                      <Text size="sm" c="dimmed" ta="center">
                        {processingStatus}
                      </Text>
                    </Stack>
                  </Card>
                </Stack>
              )}

              {/* Phase 1 Results - Extracted Codes */}
              {extractedCodes && currentPhase !== "upload" && !isProcessing && (
                <Card withBorder>
                  <Group justify="space-between" mb="sm">
                    <Group gap="xs">
                      <IconFileText size={18} />
                      <Text fw={500} size="sm">Extracted Zoning Codes</Text>
                    </Group>
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<IconDownload size={14} />}
                      onClick={handleExportCodes}
                    >
                      Export
                    </Button>
                  </Group>
                  <ScrollArea h={200}>
                    <Table striped highlightOnHover withTableBorder>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Code</Table.Th>
                          <Table.Th>Name</Table.Th>
                          <Table.Th>Max Height</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {extractedCodes.map((code) => (
                          <Table.Tr key={code.code}>
                            <Table.Td>
                              <Badge size="xs" variant="light">{code.code}</Badge>
                            </Table.Td>
                            <Table.Td>{code.name}</Table.Td>
                            <Table.Td>{code.maxHeight}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </ScrollArea>
                </Card>
              )}

              {/* Phase 2 Results & Phase 3 Setup */}
              {convertedGeoJSON && (currentPhase === "phase3" || currentPhase === "complete") && !isProcessing && (
                <Stack gap="md">
                  {/* Zone Summary */}
                  <Card withBorder>
                    <Group justify="space-between" mb="sm">
                      <Group gap="xs">
                        <IconMap size={18} />
                        <Text fw={500} size="sm">Converted Zones</Text>
                      </Group>
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconDownload size={14} />}
                        onClick={handleExportGeoJSON}
                      >
                        GeoJSON
                      </Button>
                    </Group>
                    <Stack gap="xs">
                      {/* Group features by zone_subtype and show counts */}
                      {Object.entries(
                        convertedGeoJSON.features.reduce((acc, f) => {
                          const key = f.properties.zone_subtype;
                          if (!acc[key]) {
                            acc[key] = { count: 0, color: f.properties.color, code: f.properties.code };
                          }
                          acc[key].count++;
                          return acc;
                        }, {} as Record<string, { count: number; color: string; code: string }>)
                      )
                        .sort((a, b) => b[1].count - a[1].count)
                        .slice(0, 10)
                        .map(([name, { count, color }]) => (
                          <Group key={name} justify="space-between">
                            <Group gap="xs">
                              <Box
                                style={{
                                  width: 14,
                                  height: 14,
                                  backgroundColor: color,
                                  borderRadius: 3,
                                  border: "1px solid #ccc",
                                }}
                              />
                              <Text size="xs" lineClamp={1} style={{ maxWidth: 180 }}>
                                {name}
                              </Text>
                            </Group>
                            <Badge size="xs" variant="light">
                              {count}
                            </Badge>
                          </Group>
                        ))}
                    </Stack>
                  </Card>

                  {/* Publish Section */}
                  {currentPhase === "phase3" && !publishedUrl && (
                    <Card withBorder>
                      <Group gap="xs" mb="sm">
                        <IconWorld size={18} />
                        <Text fw={500} size="sm">Publish Interactive Website</Text>
                      </Group>
                      <Stack gap="sm">
                        <TextInput
                          label="Municipality Name"
                          placeholder="e.g., Town of Springfield"
                          leftSection={<IconBuilding size={16} />}
                          value={municipalityName}
                          onChange={(e) => setMunicipalityName(e.target.value)}
                        />
                        <Button
                          leftSection={<IconWorld size={16} />}
                          onClick={runPhase3}
                          disabled={!municipalityName.trim()}
                          color="violet"
                        >
                          Publish Zoning Website
                        </Button>
                      </Stack>
                    </Card>
                  )}

                  {/* Published Result */}
                  {publishedUrl && (
                    <Alert
                      icon={<IconCheck size={18} />}
                      color="green"
                      variant="light"
                      title="Website Published!"
                    >
                      <Stack gap="xs">
                        <Text size="sm">
                          Your interactive zoning map is now live at:
                        </Text>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<IconExternalLink size={14} />}
                            onClick={() => window.open(publishedUrl, "_blank")}
                          >
                            {publishedUrl}
                          </Button>
                        </Group>
                        <Text size="xs" c="dimmed">
                          Share this link with residents, developers, and staff.
                        </Text>
                      </Stack>
                    </Alert>
                  )}
                </Stack>
              )}

              {/* Complete State */}
              {currentPhase === "complete" && (
                <Stack gap="md">
                  <Divider />
                  <Button
                    variant="subtle"
                    leftSection={<IconRefresh size={16} />}
                    onClick={handleReset}
                  >
                    Process Another Municipality
                  </Button>
                </Stack>
              )}

              {/* Info Footer */}
              <Divider mt="auto" />
              <Box>
                <Text size="xs" c="dimmed" ta="center">
                  Spatially helps municipalities digitize and share zoning information.
                  This tool is free for local governments.
                </Text>
              </Box>
            </Stack>
          </ScrollArea>
        </Paper>

        {/* Map Container */}
        <Box
          style={{
            position: "fixed",
            top: 60,
            left: 480,
            right: 0,
            bottom: 0,
          }}
        >
          <div
            ref={mapContainer}
            style={{
              width: "100%",
              height: "100%",
            }}
          />

          {/* Map Overlay - Shows when no conversion yet */}
          {!convertedGeoJSON && (
            <Box
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(255, 255, 255, 0.8)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Paper shadow="lg" p="xl" radius="lg" withBorder>
                <Stack align="center" gap="md">
                  <ThemeIcon size={60} color="violet" variant="light">
                    <IconMap size={36} />
                  </ThemeIcon>
                  <Title order={3} ta="center">
                    Map Preview
                  </Title>
                  <Text c="dimmed" ta="center" maw={300}>
                    Upload your zoning map to see the converted GIS data displayed here as an interactive map.
                  </Text>
                </Stack>
              </Paper>
            </Box>
          )}

          {/* Legend - Shows after conversion */}
          {convertedGeoJSON && (
            <Paper
              shadow="md"
              p="md"
              radius="md"
              style={{
                position: "absolute",
                top: 16,
                left: 16,
                maxWidth: 220,
              }}
            >
              <Text fw={500} size="sm" mb="xs">
                Zoning Districts
              </Text>
              <ScrollArea h={200}>
                <Stack gap={4}>
                  {Object.entries(
                    convertedGeoJSON.features.reduce((acc, f) => {
                      const key = f.properties.zone_subtype;
                      if (!acc[key]) {
                        acc[key] = { color: f.properties.color, code: f.properties.code };
                      }
                      return acc;
                    }, {} as Record<string, { color: string; code: string }>)
                  )
                    .slice(0, 15)
                    .map(([name, { color, code }]) => (
                      <Group key={name} gap="xs" wrap="nowrap">
                        <Box
                          style={{
                            width: 14,
                            height: 14,
                            backgroundColor: color,
                            borderRadius: 3,
                            border: "1px solid #666",
                            flexShrink: 0,
                          }}
                        />
                        <Text size="xs" fw={500} style={{ flexShrink: 0 }}>{code}</Text>
                        <Text size="xs" c="dimmed" lineClamp={1}>
                          {name}
                        </Text>
                      </Group>
                    ))}
                </Stack>
              </ScrollArea>
            </Paper>
          )}
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
