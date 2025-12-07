import { useRef, useState, useEffect } from "react";
import {
  Paper,
  Group,
  ActionIcon,
  Box,
  Title,
  ScrollArea,
  Text,
  UnstyledButton,
} from "@mantine/core";
import {
  IconChevronLeft,
  IconChevronRight,
  IconGripVertical,
  IconBook,
  IconArticle,
  IconFileText,
  IconX,
} from "@tabler/icons-react";

export interface SidebarTab {
  id: string;
  label: string;
  type: "browse" | "results" | "document";
  messageId?: string; // Link to chat message for reopening
}

interface SidebarProps {
  tabs: SidebarTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
  width: number;
  isResizing: boolean;
  onResizeStart: (e: React.MouseEvent) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobile: boolean;
  children: React.ReactNode;
}

export function Sidebar({
  tabs,
  activeTabId,
  onTabChange,
  onTabClose,
  width,
  isResizing,
  onResizeStart,
  isCollapsed,
  onToggleCollapse,
  isMobile,
  children,
}: SidebarProps) {
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Check if tabs overflow and update scroll button visibility
  const updateScrollButtons = () => {
    const viewport = scrollViewportRef.current;
    if (!viewport) return;

    setCanScrollLeft(viewport.scrollLeft > 0);
    setCanScrollRight(
      viewport.scrollLeft < viewport.scrollWidth - viewport.clientWidth - 1
    );
  };

  // Update scroll buttons on mount and when tabs change
  useEffect(() => {
    updateScrollButtons();
    // Add a small delay to ensure DOM is updated
    const timeout = setTimeout(updateScrollButtons, 100);
    return () => clearTimeout(timeout);
  }, [tabs]);

  // Scroll tabs left or right
  const scrollTabs = (direction: "left" | "right") => {
    const viewport = scrollViewportRef.current;
    if (!viewport) return;

    const scrollAmount = 150;
    viewport.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });

    // Update buttons after scroll
    setTimeout(updateScrollButtons, 300);
  };

  return (
    <>
      {/* Collapsed toggle button */}
      <Box
        style={{
          position: "fixed",
          top: 60,
          left: 0,
          height: "calc(100vh - 60px)",
          zIndex: 101,
          display: "flex",
          alignItems: "center",
          pointerEvents: isCollapsed ? "auto" : "none",
          opacity: isCollapsed ? 1 : 0,
          transition: "opacity 0.3s ease",
        }}
      >
        <ActionIcon
          variant="filled"
          color="blue"
          size="lg"
          onClick={onToggleCollapse}
          style={{
            borderTopLeftRadius: 0,
            borderBottomLeftRadius: 0,
          }}
        >
          <IconChevronRight size={18} />
        </ActionIcon>
      </Box>

      {/* Main sidebar panel */}
      <Paper
        shadow="lg"
        style={{
          position: "fixed",
          top: 60,
          left: isCollapsed ? -width : 0,
          width: isMobile ? "100%" : width,
          height: "calc(100vh - 60px)",
          backgroundColor: "white",
          zIndex: 100,
          display: "flex",
          flexDirection: "column",
          transition: "left 0.3s ease",
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

      {/* Header with collapse button */}
      <Group p="sm" justify="space-between" style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
        <Group gap="sm">
          <IconBook size={20} color="var(--mantine-color-blue-6)" />
          <Title order={5}>Documents</Title>
        </Group>
        <ActionIcon variant="subtle" color="gray" onClick={onToggleCollapse}>
          <IconChevronLeft size={18} />
        </ActionIcon>
      </Group>

      {/* Tabs */}
      <Box style={{ borderBottom: "1px solid var(--mantine-color-gray-2)", position: "relative" }}>
        <Group gap={0} wrap="nowrap" align="stretch">
          {/* Left scroll button */}
          {canScrollLeft && (
            <ActionIcon
              variant="subtle"
              color="gray"
              size="sm"
              onClick={() => scrollTabs("left")}
              style={{
                position: "absolute",
                left: 0,
                top: "50%",
                transform: "translateY(-50%)",
                zIndex: 2,
                backgroundColor: "white",
                boxShadow: "2px 0 4px rgba(0,0,0,0.1)",
              }}
            >
              <IconChevronLeft size={14} />
            </ActionIcon>
          )}

          {/* Tab scroll area */}
          <Box
            style={{ flex: 1, overflow: "hidden", paddingLeft: canScrollLeft ? 24 : 0, paddingRight: canScrollRight ? 24 : 0 }}
          >
            <ScrollArea
              type="never"
              style={{ whiteSpace: "nowrap" }}
              viewportRef={scrollViewportRef}
              onScrollPositionChange={updateScrollButtons}
            >
              <Group gap={4} wrap="nowrap" px="xs" pt="xs" pb={0} style={{ marginBottom: -1 }}>
                {tabs.map((tab) => {
                  const isActive = activeTabId === tab.id;
                  return (
                    <UnstyledButton
                      key={tab.id}
                      onClick={() => onTabChange(tab.id)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "6px 6px 0 0",
                        backgroundColor: isActive ? "white" : "var(--mantine-color-gray-0)",
                        border: "1px solid var(--mantine-color-gray-3)",
                        borderBottom: isActive ? "1px solid white" : "1px solid var(--mantine-color-gray-3)",
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        minWidth: 0,
                        flexShrink: 0,
                        position: "relative",
                        zIndex: isActive ? 1 : 0,
                        marginBottom: isActive ? -1 : 0,
                        transition: "all 0.15s ease",
                      }}
                    >
                      {tab.type === "browse" ? (
                        <IconBook size={14} color={isActive ? "var(--mantine-color-blue-6)" : "var(--mantine-color-gray-6)"} />
                      ) : tab.type === "document" ? (
                        <IconFileText size={14} color={isActive ? "var(--mantine-color-blue-6)" : "var(--mantine-color-gray-6)"} />
                      ) : (
                        <IconArticle size={14} color={isActive ? "var(--mantine-color-blue-6)" : "var(--mantine-color-gray-6)"} />
                      )}
                      <Text
                        size="xs"
                        fw={isActive ? 600 : 400}
                        c={isActive ? "blue.7" : "gray.7"}
                        style={{
                          maxWidth: 120,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {tab.label}
                      </Text>
                      {tab.type !== "browse" && (
                        <Box
                          component="span"
                          onClick={(e: React.MouseEvent) => {
                            e.stopPropagation();
                            onTabClose(tab.id);
                          }}
                          style={{
                            marginLeft: 4,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            width: 16,
                            height: 16,
                            borderRadius: 4,
                            cursor: "pointer",
                          }}
                          onMouseEnter={(e: React.MouseEvent<HTMLSpanElement>) => {
                            e.currentTarget.style.backgroundColor = "var(--mantine-color-gray-2)";
                          }}
                          onMouseLeave={(e: React.MouseEvent<HTMLSpanElement>) => {
                            e.currentTarget.style.backgroundColor = "transparent";
                          }}
                        >
                          <IconX size={10} color="gray" />
                        </Box>
                      )}
                    </UnstyledButton>
                  );
                })}
              </Group>
            </ScrollArea>
          </Box>

          {/* Right scroll button */}
          {canScrollRight && (
            <ActionIcon
              variant="subtle"
              color="gray"
              size="sm"
              onClick={() => scrollTabs("right")}
              style={{
                position: "absolute",
                right: 0,
                top: "50%",
                transform: "translateY(-50%)",
                zIndex: 2,
                backgroundColor: "white",
                boxShadow: "-2px 0 4px rgba(0,0,0,0.1)",
              }}
            >
              <IconChevronRight size={14} />
            </ActionIcon>
          )}
        </Group>
      </Box>

      {/* Content - rendered by children */}
      <Box style={{ flex: 1, overflow: "hidden" }}>
        {children}
      </Box>
    </Paper>
    </>
  );
}
