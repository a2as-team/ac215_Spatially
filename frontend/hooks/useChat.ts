import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  chatApi,
  Chat,
  StartChatRequest,
  ContinueChatRequest,
} from '@/services/chatApi';

// Query keys
export const chatKeys = {
  all: ['chats'] as const,
  lists: () => [...chatKeys.all, 'list'] as const,
  list: (limit?: number) => [...chatKeys.lists(), { limit }] as const,
  details: () => [...chatKeys.all, 'detail'] as const,
  detail: (id: string) => [...chatKeys.details(), id] as const,
};

// Get all chats
export const useChats = (limit?: number) => {
  return useQuery({
    queryKey: chatKeys.list(limit),
    queryFn: () => chatApi.getChats(limit),
  });
};

// Get a specific chat
export const useChat = (chatId: string | null) => {
  return useQuery({
    queryKey: chatKeys.detail(chatId || ''),
    queryFn: () => chatApi.getChat(chatId!),
    enabled: !!chatId,
  });
};

// Start a new chat
export const useStartChat = () => {
  const queryClient = useQueryClient();

  return useMutation<Chat, Error, StartChatRequest>({
    mutationFn: (request) => chatApi.startChat(request),
    onSuccess: (data) => {
      // Invalidate and refetch chats list
      queryClient.invalidateQueries({ queryKey: chatKeys.lists() });
      // Add the new chat to cache
      queryClient.setQueryData(chatKeys.detail(data.chat_id), data);
    },
  });
};

// Continue an existing chat
export const useContinueChat = () => {
  const queryClient = useQueryClient();

  return useMutation<
    Chat,
    Error,
    { chatId: string; request: ContinueChatRequest }
  >({
    mutationFn: ({ chatId, request }) => chatApi.continueChat(chatId, request),
    onSuccess: (data, variables) => {
      // Update the chat in cache
      queryClient.setQueryData(chatKeys.detail(variables.chatId), data);
      // Invalidate chats list to update timestamps
      queryClient.invalidateQueries({ queryKey: chatKeys.lists() });
    },
  });
};
