import { useMemo } from "react";
import { Paper, Text, Stack, Group, Box } from "@mantine/core";
import { getZoneSubtypeColor, COLOR_TO_CATEGORY } from "@/utils/zoningColors";

interface ZoningData {
  zone_subtype?: string | null;
}

interface MapLegendProps {
  zoningData?: ZoningData[];
}

export function MapLegend({ zoningData }: MapLegendProps) {
  // Generate legend items grouped by color (category)
  const legendItems = useMemo(() => {
    if (!zoningData || zoningData.length === 0) return [];

    // Collect unique colors present in the data
    const colorsInUse = new Set<string>();
    zoningData.forEach((zone) => {
      const color = getZoneSubtypeColor(zone.zone_subtype);
      colorsInUse.add(color);
    });

    // Convert to legend items with category labels
    return Array.from(colorsInUse)
      .map((color) => ({
        color,
        label: COLOR_TO_CATEGORY[color] || "Unknown",
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [zoningData]);

  if (legendItems.length === 0) return null;

  return (
    <Paper
      shadow="md"
      p="xs"
      radius="sm"
      style={{
        position: "absolute",
        top: 10,
        left: 10,
        maxHeight: 300,
        overflow: "auto",
        zIndex: 1000,
        backgroundColor: "rgba(255, 255, 255, 0.95)",
      }}
    >
      <Text size="xs" fw={600} mb="xs">
        Zoning Legend
      </Text>
      <Stack gap={4}>
        {legendItems.map((item) => (
          <Group key={item.label} gap="xs" wrap="nowrap">
            <Box
              style={{
                width: 14,
                height: 14,
                backgroundColor: item.color,
                borderRadius: 2,
                border: "1px solid rgba(0,0,0,0.2)",
                flexShrink: 0,
              }}
            />
            <Text size="xs" c="dark" lineClamp={1}>
              {item.label}
            </Text>
          </Group>
        ))}
      </Stack>
    </Paper>
  );
}
