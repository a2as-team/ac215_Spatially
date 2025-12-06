import {
  Stack,
  Text,
  Title,
  ScrollArea,
  Group,
  Box,
  Divider,
  Badge,
  Paper,
  ThemeIcon,
  ActionIcon,
} from "@mantine/core";
import { IconQuote } from "@tabler/icons-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Plugin } from "unified";
import type { Root, Table, TableRow, TableCell } from "mdast";
import { visit } from "unist-util-visit";
import { IconMapPin } from "@tabler/icons-react";
import type { OrdinanceSource, DevelopmentPlanSource } from "@/services/chatApi";

/**
 * Remark plugin to clean up malformed tables by removing empty columns.
 */
const remarkCleanTables: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, "table", (node: Table) => {
      if (!node.children || node.children.length < 2) return;

      const rows = node.children as TableRow[];
      const maxCols = Math.max(...rows.map((row) => row.children?.length || 0));

      if (maxCols <= 5) return;

      const colHasContent = new Array(maxCols).fill(false);

      for (const row of rows) {
        const cells = row.children as TableCell[];
        for (let i = 0; i < cells.length; i++) {
          const cell = cells[i];
          const hasText = cell.children?.some((child) => {
            if ("value" in child && typeof child.value === "string") {
              const text = child.value.trim();
              return text.length > 0 && text !== "-" && text !== "---";
            }
            return true;
          });
          if (hasText) {
            colHasContent[i] = true;
          }
        }
      }

      const emptyColCount = colHasContent.filter((has) => !has).length;

      if (emptyColCount > maxCols * 0.4) {
        for (const row of rows) {
          const cells = row.children as TableCell[];
          row.children = cells.filter((_, idx) => colHasContent[idx]);
        }

        if (node.align) {
          node.align = node.align.filter((_, idx) => colHasContent[idx]);
        }
      }
    });
  };
};

interface QueryTabProps {
  ordinanceSources: OrdinanceSource[];
  developmentPlanSources: DevelopmentPlanSource[];
  onZoningCodeClick?: (code: string) => void;
  onPlanLocationClick?: (lat: number, lng: number) => void;
}

export function QueryTab({
  ordinanceSources,
  developmentPlanSources,
  onZoningCodeClick,
  onPlanLocationClick,
}: QueryTabProps) {
  const hasOrdinances = ordinanceSources.length > 0;
  const hasDevPlans = developmentPlanSources.length > 0;
  const hasAny = hasOrdinances || hasDevPlans;

  return (
    <ScrollArea style={{ height: "100%" }} offsetScrollbars p="md">
      <Stack gap="lg">
        {/* Development Plan Sources */}
        {hasDevPlans && (
          <>
            <Title order={5} c="dark">Development Plans</Title>
            {developmentPlanSources.map((source, index) => (
              <Paper key={`dev-${index}`} withBorder p="md" radius="md" style={{ borderColor: "var(--mantine-color-green-4)" }}>
                {/* Source header */}
                <Group justify="space-between" mb="sm">
                  <div>
                    <Group gap="xs">
                      <Text fw={600} size="sm" c="dark">
                        {source.title}
                      </Text>
                      {source.latitude && source.longitude && (
                        <ActionIcon
                          size="xs"
                          variant="light"
                          color="green"
                          onClick={() => onPlanLocationClick?.(source.latitude!, source.longitude!)}
                          title="Show on map"
                        >
                          <IconMapPin size={12} />
                        </ActionIcon>
                      )}
                    </Group>
                    {source.subtitle && (
                      <Text size="xs" c="dimmed">
                        {source.subtitle}
                      </Text>
                    )}
                  </div>
                  <Group gap="xs">
                    {source.distance_km != null && (
                      <Badge size="xs" color="green" variant="light">
                        {source.distance_km.toFixed(2)}km away
                      </Badge>
                    )}
                    {source.similarity_score && (
                      <Badge size="xs" color="blue" variant="light">
                        {Math.round(source.similarity_score * 100)}% match
                      </Badge>
                    )}
                  </Group>
                </Group>

                {/* Agent's highlight - key excerpt */}
                {source.highlight && (
                  <Box
                    mb="sm"
                    p="sm"
                    style={{
                      backgroundColor: "var(--mantine-color-green-0)",
                      borderLeft: "3px solid var(--mantine-color-green-6)",
                      borderRadius: "4px",
                    }}
                  >
                    <Group gap="xs" mb={4}>
                      <ThemeIcon size="xs" color="green" variant="light">
                        <IconQuote size={12} />
                      </ThemeIcon>
                      <Text size="xs" fw={600} c="green.8">
                        Key excerpt
                      </Text>
                    </Group>
                    <Text size="sm" c="dark" style={{ fontStyle: "italic" }}>
                      &quot;{source.highlight}&quot;
                    </Text>
                    {source.reason && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {source.reason}
                      </Text>
                    )}
                  </Box>
                )}

                {/* Article references and zoning codes */}
                <Group gap="xs" mb="sm" wrap="wrap">
                  {source.article_reference?.map((ref) => (
                    <Badge key={ref} size="xs" variant="outline" color="orange">
                      {ref}
                    </Badge>
                  ))}
                  {source.zoning_codes?.map((code) => (
                    <Badge
                      key={code}
                      size="xs"
                      variant="outline"
                      color="blue"
                      style={{
                        cursor: onZoningCodeClick ? "pointer" : "default",
                        transition: "all 0.2s ease",
                      }}
                      onClick={() => onZoningCodeClick?.(code)}
                    >
                      {code}
                    </Badge>
                  ))}
                </Group>

                <Divider mb="sm" />

                {/* Content */}
                <Text size="sm" c="dark" style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                  {source.content}
                </Text>
              </Paper>
            ))}
          </>
        )}

        {/* Ordinance Sources */}
        {hasOrdinances && (
          <>
            {hasDevPlans && <Divider my="md" />}
            <Title order={5} c="dark">Zoning Ordinances</Title>
            {ordinanceSources.map((source, index) => (
          <Paper key={`ord-${index}`} withBorder p="md" radius="md">
            {/* Source header */}
            <Group justify="space-between" mb="sm">
              <div>
                <Text fw={600} size="sm" c="dark">
                  {source.title}
                </Text>
                {source.subtitle && (
                  <Text size="xs" c="dimmed">
                    {source.subtitle}
                  </Text>
                )}
              </div>
              {source.similarity_score && (
                <Badge size="xs" color="blue" variant="light">
                  {Math.round(source.similarity_score * 100)}% match
                </Badge>
              )}
            </Group>

            {/* Agent's highlight - key excerpt */}
            {source.highlight && (
              <Box
                mb="sm"
                p="sm"
                style={{
                  backgroundColor: "var(--mantine-color-yellow-0)",
                  borderLeft: "3px solid var(--mantine-color-yellow-6)",
                  borderRadius: "4px",
                }}
              >
                <Group gap="xs" mb={4}>
                  <ThemeIcon size="xs" color="yellow" variant="light">
                    <IconQuote size={12} />
                  </ThemeIcon>
                  <Text size="xs" fw={600} c="yellow.8">
                    Key excerpt
                  </Text>
                </Group>
                <Text size="sm" c="dark" style={{ fontStyle: "italic" }}>
                  "{source.highlight}"
                </Text>
                {source.reason && (
                  <Text size="xs" c="dimmed" mt={4}>
                    {source.reason}
                  </Text>
                )}
              </Box>
            )}

            {/* Zoning codes */}
            {source.zoning_codes && source.zoning_codes.length > 0 && (
              <Group gap="xs" mb="sm">
                {source.zoning_codes.map((code) => (
                  <Badge
                    key={code}
                    size="xs"
                    variant="outline"
                    color="blue"
                    style={{
                      cursor: onZoningCodeClick ? "pointer" : "default",
                      transition: "all 0.2s ease",
                    }}
                    onClick={() => onZoningCodeClick?.(code)}
                    onMouseEnter={(e) => {
                      if (onZoningCodeClick) {
                        e.currentTarget.style.backgroundColor = "var(--mantine-color-blue-1)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = "";
                    }}
                  >
                    {code}
                  </Badge>
                ))}
              </Group>
            )}

            <Divider mb="sm" />

            {/* Markdown content */}
            <Box>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkCleanTables]}
                components={{
                  p: ({ children }) => (
                    <Text size="sm" mb="xs" c="dark" style={{ lineHeight: 1.6 }}>
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
                      style={{ paddingLeft: "20px", marginBottom: "8px" }}
                    >
                      {children}
                    </Text>
                  ),
                  ol: ({ children }) => (
                    <Text
                      component="ol"
                      size="sm"
                      c="dark"
                      style={{ paddingLeft: "20px", marginBottom: "8px" }}
                    >
                      {children}
                    </Text>
                  ),
                  li: ({ children }) => (
                    <Text component="li" size="sm" mb={4} c="dark" style={{ lineHeight: 1.5 }}>
                      {children}
                    </Text>
                  ),
                  table: ({ children }) => (
                    <Box
                      style={{
                        overflowX: "auto",
                        marginBottom: "12px",
                        border: "1px solid var(--mantine-color-gray-3)",
                        borderRadius: "4px",
                        maxHeight: "400px",
                        overflowY: "auto",
                      }}
                    >
                      <table
                        style={{
                          borderCollapse: "collapse",
                          width: "100%",
                          fontSize: "0.7rem",
                          lineHeight: 1.3,
                        }}
                      >
                        {children}
                      </table>
                    </Box>
                  ),
                  thead: ({ children }) => (
                    <thead
                      style={{
                        backgroundColor: "var(--mantine-color-blue-0)",
                        position: "sticky",
                        top: 0,
                        zIndex: 1,
                      }}
                    >
                      {children}
                    </thead>
                  ),
                  th: ({ children }) => (
                    <th
                      style={{
                        border: "1px solid var(--mantine-color-gray-4)",
                        padding: "4px 6px",
                        backgroundColor: "var(--mantine-color-blue-1)",
                        textAlign: "center",
                        fontWeight: 600,
                        fontSize: "0.65rem",
                        minWidth: "40px",
                      }}
                    >
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td
                      style={{
                        border: "1px solid var(--mantine-color-gray-3)",
                        padding: "3px 5px",
                        fontSize: "0.65rem",
                        textAlign: "center",
                        verticalAlign: "middle",
                      }}
                    >
                      {children}
                    </td>
                  ),
                  tr: ({ children }) => (
                    <tr style={{ backgroundColor: "white" }}>{children}</tr>
                  ),
                  img: () => null,
                  a: ({ href, children }) => (
                    <Text
                      component="a"
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="sm"
                      c="blue"
                      style={{ textDecoration: "underline" }}
                    >
                      {children}
                    </Text>
                  ),
                }}
              >
                {source.content}
              </ReactMarkdown>
            </Box>
          </Paper>
            ))}
          </>
        )}

        {/* Empty state */}
        {!hasAny && (
          <Box py="xl" ta="center">
            <Text size="sm" c="dimmed">
              No sources to display
            </Text>
          </Box>
        )}
      </Stack>
    </ScrollArea>
  );
}
