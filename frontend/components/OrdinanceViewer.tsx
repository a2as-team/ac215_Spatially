import { useEffect, useRef } from "react";
import {
  Paper,
  Stack,
  Text,
  Title,
  ScrollArea,
  Group,
  ActionIcon,
  Box,
  Divider,
  Badge,
} from "@mantine/core";
import { IconX, IconFileText, IconGripVertical } from "@tabler/icons-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Plugin } from "unified";
import type { Root, Table, TableRow, TableCell } from "mdast";
import { visit } from "unist-util-visit";

/**
 * Remark plugin to clean up malformed tables by removing empty columns.
 */
const remarkCleanTables: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, "table", (node: Table) => {
      if (!node.children || node.children.length < 2) return;

      // Get all rows
      const rows = node.children as TableRow[];

      // Find the maximum number of columns
      const maxCols = Math.max(...rows.map((row) => row.children?.length || 0));

      // If table has very few columns, leave it alone
      if (maxCols <= 5) return;

      // Track which columns have content
      const colHasContent = new Array(maxCols).fill(false);

      for (const row of rows) {
        const cells = row.children as TableCell[];
        for (let i = 0; i < cells.length; i++) {
          const cell = cells[i];
          // Check if cell has any text content
          const hasText = cell.children?.some((child) => {
            if ("value" in child && typeof child.value === "string") {
              const text = child.value.trim();
              return text.length > 0 && text !== "-" && text !== "---";
            }
            return true; // Non-text nodes count as content
          });
          if (hasText) {
            colHasContent[i] = true;
          }
        }
      }

      // Count empty columns
      const emptyColCount = colHasContent.filter((has) => !has).length;

      // If more than 40% of columns are empty, filter them out
      if (emptyColCount > maxCols * 0.4) {
        for (const row of rows) {
          const cells = row.children as TableCell[];
          row.children = cells.filter((_, idx) => colHasContent[idx]);
        }

        // Also update alignment if present
        if (node.align) {
          node.align = node.align.filter((_, idx) => colHasContent[idx]);
        }
      }
    });
  };
};

interface OrdinanceSource {
  title: string;
  subtitle?: string;
  zoning_codes?: string[];
  content: string;
  similarity_score?: number;
}

interface OrdinanceViewerProps {
  sources: OrdinanceSource[];
  onClose: () => void;
  width: number;
  onWidthChange: (width: number) => void;
  isResizing: boolean;
  onResizeStart: (e: React.MouseEvent) => void;
  isMobile: boolean;
}

export function OrdinanceViewer({
  sources,
  onClose,
  width,
  isResizing,
  onResizeStart,
  isMobile,
}: OrdinanceViewerProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Scroll to top when sources change
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollElement) {
        scrollElement.scrollTop = 0;
      }
    }
  }, [sources]);

  if (sources.length === 0) {
    return null;
  }

  return (
    <Paper
      shadow="lg"
      style={{
        position: "fixed",
        top: 60,
        left: 0,
        width: isMobile ? "100%" : width,
        height: "calc(100vh - 60px)",
        backgroundColor: "white",
        zIndex: 100,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Resize handle - only show on desktop */}
      {!isMobile && (
        <Box
          onMouseDown={onResizeStart}
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 6,
            height: "100%",
            cursor: "col-resize",
            backgroundColor: isResizing ? "var(--mantine-color-blue-4)" : "transparent",
            transition: "background-color 0.2s",
            zIndex: 10,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "var(--mantine-color-gray-3)";
          }}
          onMouseLeave={(e) => {
            if (!isResizing) {
              e.currentTarget.style.backgroundColor = "transparent";
            }
          }}
        >
          <Box
            style={{
              position: "absolute",
              top: "50%",
              right: 0,
              transform: "translateY(-50%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 6,
              height: 40,
            }}
          >
            <IconGripVertical size={12} color="gray" />
          </Box>
        </Box>
      )}

      {/* Header */}
      <Group p="md" justify="space-between" style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
        <Group gap="sm">
          <IconFileText size={20} color="var(--mantine-color-blue-6)" />
          <div>
            <Title order={5}>Zoning Ordinance</Title>
            <Text size="xs" c="dimmed">
              {sources.length} relevant {sources.length === 1 ? "section" : "sections"} found
            </Text>
          </div>
        </Group>
        <ActionIcon variant="subtle" color="gray" onClick={onClose}>
          <IconX size={18} />
        </ActionIcon>
      </Group>

      {/* Content */}
      <ScrollArea style={{ flex: 1 }} offsetScrollbars ref={scrollAreaRef} p="md">
        <Stack gap="lg">
          {sources.map((source, index) => (
            <Paper key={index} withBorder p="md" radius="md">
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

              {/* Zoning codes */}
              {source.zoning_codes && source.zoning_codes.length > 0 && (
                <Group gap="xs" mb="sm">
                  {source.zoning_codes.map((code) => (
                    <Badge key={code} size="xs" variant="outline" color="gray">
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
                      <tr style={{ backgroundColor: "white" }}>
                        {children}
                      </tr>
                    ),
                    // Hide images - not needed for ordinance text
                    img: () => null,
                    // Style links
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
        </Stack>
      </ScrollArea>
    </Paper>
  );
}
