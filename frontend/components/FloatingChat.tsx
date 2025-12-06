import { useState, useRef, useEffect, useMemo } from "react";
import {
  Paper,
  Group,
  Stack,
  Text,
  Textarea,
  ActionIcon,
  Loader,
  Avatar,
  Box,
  ScrollArea,
  Collapse,
  Title,
  Badge,
} from "@mantine/core";
import {
  IconSend,
  IconRobot,
  IconUser,
  IconChevronDown,
  IconChevronUp,
  IconMapPin,
  IconFileText,
} from "@tabler/icons-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getZoneSubtypeColor } from "@/utils/zoningColors";

interface Message {
  message_id: string;
  role: "user" | "assistant";
  content: string;
}

interface SelectedZoning {
  code?: string;
  zoning_code?: string;
  zone_subtype?: string | null;
}

interface FloatingChatProps {
  messages: Message[];
  isPending: boolean;
  onSendMessage: (message: string) => void;
  selectedZoning?: SelectedZoning[] | null;
  messagesWithSources?: Set<string>;
  onMessageClick?: (messageId: string) => void;
}

export function FloatingChat({
  messages,
  isPending,
  onSendMessage,
  selectedZoning,
  messagesWithSources,
  onMessageClick,
}: FloatingChatProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [inputValue, setInputValue] = useState("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const hasZoningContext = selectedZoning && selectedZoning.length > 0;

  // Get the primary zone color for the animated border
  const zoneColor = useMemo(() => {
    if (!hasZoningContext || !selectedZoning[0]) return null;
    return getZoneSubtypeColor(selectedZoning[0].zone_subtype);
  }, [hasZoningContext, selectedZoning]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current && isExpanded) {
      const scrollElement = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages, isExpanded]);

  return (
    <Paper
      shadow="xl"
      radius="lg"
      style={{
        position: "absolute",
        bottom: 20,
        right: 20,
        width: 380,
        maxHeight: "60vh",
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        backdropFilter: "blur(10px)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        // Smooth transitions for color changes
        transition: "border-color 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease",
        // Colored border when zoning is selected
        border: hasZoningContext && zoneColor
          ? `2px solid ${zoneColor}`
          : "2px solid transparent",
        boxShadow: hasZoningContext && zoneColor
          ? `0 0 15px ${zoneColor}50, 0 4px 20px rgba(0,0,0,0.15)`
          : "0 4px 20px rgba(0,0,0,0.15)",
      }}
    >
      {/* Header */}
      <Box
        p="sm"
        style={{
          borderBottom: isExpanded ? "1px solid var(--mantine-color-gray-2)" : "none",
          cursor: "pointer",
          borderRadius: "var(--mantine-radius-lg) var(--mantine-radius-lg) 0 0",
          transition: "background 0.3s ease",
          background: hasZoningContext && zoneColor
            ? `linear-gradient(135deg, ${zoneColor}15 0%, ${zoneColor}08 100%)`
            : "transparent",
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Group justify="space-between">
          <Group gap="xs">
            <Avatar
              radius="xl"
              size="sm"
              style={{
                background: hasZoningContext && zoneColor ? zoneColor : "var(--mantine-color-grape-6)",
                transition: "background 0.3s ease",
              }}
            >
              <IconRobot size={16} color="white" />
            </Avatar>
            <div>
              <Text fw={500} size="sm">
                Zoning Assistant
              </Text>
              {hasZoningContext && (
                <Group gap={4} mt={2}>
                  <IconMapPin size={10} style={{ color: zoneColor || "var(--mantine-color-violet-6)" }} />
                  <Text size="xs" style={{ color: zoneColor || "var(--mantine-color-violet-6)" }}>
                    Location-specific mode
                  </Text>
                </Group>
              )}
            </div>
          </Group>
          <ActionIcon variant="subtle" color="gray" size="sm">
            {isExpanded ? <IconChevronDown size={16} /> : <IconChevronUp size={16} />}
          </ActionIcon>
        </Group>

        {/* Zoning Context Badge */}
        {hasZoningContext && isExpanded && (
          <Group gap="xs" mt="xs" wrap="wrap">
            {selectedZoning.slice(0, 3).map((zone, idx) => {
              const badgeColor = getZoneSubtypeColor(zone.zone_subtype);
              return (
                <Badge
                  key={idx}
                  size="xs"
                  style={{
                    backgroundColor: badgeColor,
                    color: "white",
                  }}
                >
                  {zone.code || zone.zoning_code}
                  {zone.zone_subtype && ` · ${zone.zone_subtype}`}
                </Badge>
              );
            })}
            {selectedZoning.length > 3 && (
              <Badge size="xs" variant="light" color="gray">
                +{selectedZoning.length - 3} more
              </Badge>
            )}
          </Group>
        )}
      </Box>

      <Collapse in={isExpanded} transitionDuration={300} transitionTimingFunction="ease">
        {/* Messages */}
        <ScrollArea
          h="calc(60vh - 160px)"
          offsetScrollbars
          ref={scrollAreaRef}
          p="sm"
          type="always"
          scrollbarSize={8}
        >
          <Stack gap="sm">
            {messages.length === 0 ? (
              <Box py="md" ta="center">
                <Text size="sm" c="dimmed">
                  {hasZoningContext
                    ? "Ask about this specific location's zoning"
                    : "Select a location or ask general questions"}
                </Text>
                {hasZoningContext && (
                  <Text size="xs" c="dimmed" mt="xs">
                    e.g., &quot;What can I build here?&quot; or &quot;What are the height limits?&quot;
                  </Text>
                )}
              </Box>
            ) : (
              messages.map((message) => {
                const hasDocuments = message.role === "assistant" && messagesWithSources?.has(message.message_id);
                return (
                <Group
                  key={message.message_id}
                  align="flex-start"
                  gap="xs"
                  wrap="nowrap"
                  style={{
                    flexDirection: message.role === "user" ? "row-reverse" : "row",
                  }}
                >
                  <Avatar
                    color={message.role === "user" ? "blue" : "grape"}
                    radius="xl"
                    size="sm"
                  >
                    {message.role === "user" ? (
                      <IconUser size={14} />
                    ) : (
                      <IconRobot size={14} />
                    )}
                  </Avatar>
                  <Paper
                    p="xs"
                    radius="md"
                    onClick={hasDocuments ? () => onMessageClick?.(message.message_id) : undefined}
                    style={{
                      maxWidth: "80%",
                      backgroundColor:
                        message.role === "user"
                          ? "var(--mantine-color-blue-1)"
                          : "var(--mantine-color-gray-0)",
                      cursor: hasDocuments ? "pointer" : "default",
                      border: hasDocuments ? "1px solid var(--mantine-color-blue-3)" : "none",
                    }}
                  >
                    {/* Document indicator for messages with sources */}
                    {hasDocuments && (
                      <Group gap={4} mb={4}>
                        <IconFileText size={12} color="var(--mantine-color-blue-6)" />
                        <Text size="xs" c="blue" fw={500}>
                          View sources
                        </Text>
                      </Group>
                    )}
                    <Box>
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => (
                            <Text size="xs" mb={4} c="dark">
                              {children}
                            </Text>
                          ),
                          h1: ({ children }) => (
                            <Title order={5} mb={4} c="dark">
                              {children}
                            </Title>
                          ),
                          h2: ({ children }) => (
                            <Title order={6} mb={4} c="dark">
                              {children}
                            </Title>
                          ),
                          h3: ({ children }) => (
                            <Text fw={600} size="sm" mb={4} c="dark">
                              {children}
                            </Text>
                          ),
                          code: ({ children, className }) => {
                            const isInline = !className;
                            return isInline ? (
                              <Text
                                component="code"
                                size="xs"
                                c="blue"
                                style={{
                                  backgroundColor: "var(--mantine-color-gray-1)",
                                  padding: "1px 4px",
                                  borderRadius: "3px",
                                  fontFamily: "monospace",
                                }}
                              >
                                {children}
                              </Text>
                            ) : (
                              <Text
                                component="pre"
                                size="xs"
                                c="dark"
                                style={{
                                  backgroundColor: "var(--mantine-color-gray-1)",
                                  padding: "8px",
                                  borderRadius: "6px",
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
                              size="xs"
                              c="dark"
                              style={{ paddingLeft: "16px", margin: "4px 0" }}
                            >
                              {children}
                            </Text>
                          ),
                          ol: ({ children }) => (
                            <Text
                              component="ol"
                              size="xs"
                              c="dark"
                              style={{ paddingLeft: "16px", margin: "4px 0" }}
                            >
                              {children}
                            </Text>
                          ),
                          li: ({ children }) => (
                            <Text component="li" size="xs" mb={2} c="dark">
                              {children}
                            </Text>
                          ),
                          img: () => null,
                          a: ({ href, children }) => (
                            <Text
                              component="a"
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              size="xs"
                              c="blue"
                              style={{ textDecoration: "underline" }}
                            >
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
              );})
            )}
            {isPending && (
              <Group align="flex-start" gap="xs" wrap="nowrap">
                <Avatar color="grape" radius="xl" size="sm">
                  <IconRobot size={14} />
                </Avatar>
                <Paper
                  p="xs"
                  radius="md"
                  style={{
                    backgroundColor: "var(--mantine-color-gray-0)",
                  }}
                >
                  <Group gap="xs">
                    <Loader size="xs" />
                    <Text size="xs" c="dark">
                      Thinking...
                    </Text>
                  </Group>
                </Paper>
              </Group>
            )}
          </Stack>
        </ScrollArea>

        {/* Input */}
        <Group gap="xs" p="sm" style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}>
          <Textarea
            placeholder={
              hasZoningContext
                ? "Ask about this zone..."
                : "Ask about zoning..."
            }
            value={inputValue}
            onChange={(e) => setInputValue(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (inputValue.trim()) {
                  onSendMessage(inputValue);
                  setInputValue("");
                }
              }
            }}
            minRows={1}
            maxRows={3}
            autosize
            style={{ flex: 1 }}
            disabled={isPending}
            size="xs"
          />
          <ActionIcon
            size="md"
            variant="filled"
            onClick={() => {
              if (inputValue.trim()) {
                onSendMessage(inputValue);
                setInputValue("");
              }
            }}
            disabled={!inputValue.trim() || isPending}
            style={{
              backgroundColor: hasZoningContext && zoneColor ? zoneColor : "var(--mantine-color-blue-6)",
              transition: "background-color 0.3s ease",
            }}
          >
            <IconSend size={14} />
          </ActionIcon>
        </Group>
      </Collapse>
    </Paper>
  );
}
