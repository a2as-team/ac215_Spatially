import { useState, useMemo } from "react";
import {
  Stack,
  Text,
  ScrollArea,
  Group,
  Box,
  Loader,
  TextInput,
  UnstyledButton,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconSearch, IconFileText } from "@tabler/icons-react";

export interface DocumentItem {
  title: string;
  subtitle: string;
}

interface DocumentTabProps {
  documents: DocumentItem[];
  isLoading: boolean;
  onDocumentSelect: (title: string, subtitle: string) => void;
}

export function DocumentTab({
  documents,
  isLoading,
  onDocumentSelect,
}: DocumentTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch] = useDebouncedValue(searchQuery, 300);

  // Filter documents by debounced search query
  const filteredDocuments = useMemo(() => {
    if (!debouncedSearch) return documents;
    const query = debouncedSearch.toLowerCase();
    return documents.filter((doc) =>
      doc.title.toLowerCase().includes(query) ||
      doc.subtitle.toLowerCase().includes(query)
    );
  }, [documents, debouncedSearch]);

  return (
    <ScrollArea style={{ height: "100%" }} offsetScrollbars p="md">
      <Stack gap="sm">
        <TextInput
          placeholder="Search documents..."
          leftSection={<IconSearch size={14} />}
          size="xs"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.currentTarget.value)}
        />

        {isLoading ? (
          <Box py="xl" ta="center">
            <Loader size="sm" />
            <Text size="xs" c="dimmed" mt="xs">
              Loading documents...
            </Text>
          </Box>
        ) : filteredDocuments.length === 0 ? (
          <Box py="md" ta="center">
            <Text size="sm" c="dimmed">
              {debouncedSearch ? "No documents match your search" : "No documents available"}
            </Text>
          </Box>
        ) : (
          <Stack gap="xs">
            {filteredDocuments.map((doc, index) => (
              <UnstyledButton
                key={index}
                onClick={() => onDocumentSelect(doc.title, doc.subtitle)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--mantine-color-gray-2)",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "var(--mantine-color-gray-0)";
                  e.currentTarget.style.borderColor = "var(--mantine-color-blue-4)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.borderColor = "var(--mantine-color-gray-2)";
                }}
              >
                <Group gap="xs" wrap="nowrap">
                  <IconFileText size={16} color="var(--mantine-color-blue-6)" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text size="sm" fw={500} lineClamp={1}>
                      {doc.title}
                    </Text>
                    {doc.subtitle && (
                      <Text size="xs" c="dimmed" lineClamp={1}>
                        {doc.subtitle}
                      </Text>
                    )}
                  </div>
                </Group>
              </UnstyledButton>
            ))}
          </Stack>
        )}
      </Stack>
    </ScrollArea>
  );
}
