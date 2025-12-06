import { ScrollArea, Text, Loader, Center, Box } from "@mantine/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface DocumentContentTabProps {
  title: string;
  subtitle?: string;
  content: string;
  isLoading?: boolean;
}

export function DocumentContentTab({
  title,
  subtitle,
  content,
  isLoading,
}: DocumentContentTabProps) {
  if (isLoading) {
    return (
      <Center h="100%">
        <Loader size="lg" />
      </Center>
    );
  }

  return (
    <ScrollArea h="100%" p="md">
      <Box mb="md">
        <Text size="lg" fw={700}>
          {title}
        </Text>
        {subtitle && (
          <Text size="sm" c="dimmed">
            {subtitle}
          </Text>
        )}
      </Box>
      <Box
        style={{
          fontSize: "14px",
          lineHeight: 1.6,
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            table: ({ children }) => (
              <Box style={{ overflowX: "auto", marginBottom: "1rem" }}>
                <table
                  style={{
                    borderCollapse: "collapse",
                    width: "100%",
                    minWidth: "400px",
                  }}
                >
                  {children}
                </table>
              </Box>
            ),
            thead: ({ children }) => (
              <thead style={{ backgroundColor: "var(--mantine-color-gray-1)" }}>
                {children}
              </thead>
            ),
            th: ({ children }) => (
              <th
                style={{
                  border: "1px solid var(--mantine-color-gray-3)",
                  padding: "8px 12px",
                  textAlign: "left",
                  fontWeight: 600,
                }}
              >
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td
                style={{
                  border: "1px solid var(--mantine-color-gray-3)",
                  padding: "8px 12px",
                }}
              >
                {children}
              </td>
            ),
            h1: ({ children }) => (
              <Text size="xl" fw={700} mt="lg" mb="sm">
                {children}
              </Text>
            ),
            h2: ({ children }) => (
              <Text size="lg" fw={600} mt="md" mb="xs">
                {children}
              </Text>
            ),
            h3: ({ children }) => (
              <Text size="md" fw={600} mt="sm" mb="xs">
                {children}
              </Text>
            ),
            p: ({ children }) => (
              <Text size="sm" mb="xs">
                {children}
              </Text>
            ),
            ul: ({ children }) => (
              <Box component="ul" style={{ paddingLeft: "1.5rem", marginBottom: "0.5rem" }}>
                {children}
              </Box>
            ),
            ol: ({ children }) => (
              <Box component="ol" style={{ paddingLeft: "1.5rem", marginBottom: "0.5rem" }}>
                {children}
              </Box>
            ),
            li: ({ children }) => (
              <li style={{ marginBottom: "0.25rem" }}>{children}</li>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </Box>
    </ScrollArea>
  );
}
