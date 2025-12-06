import { apiClient } from './api';

export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string;
  image_path?: string;
}

export interface OrdinanceSource {
  title: string;
  subtitle?: string;
  zoning_codes?: string[];
  content: string;
  similarity_score?: number;
}

export interface Chat {
  chat_id: string;
  title: string;
  dts: number;
  messages: ChatMessage[];
  ordinance_sources?: OrdinanceSource[];
}

export interface StartChatRequest {
  content: string;
  city: string;
  latitude?: number;
  longitude?: number;
}

export interface ContinueChatRequest {
  content: string;
  latitude?: number;
  longitude?: number;
}

const SESSION_ID_KEY = 'spatially_session_id';

// Get or create session ID
const getSessionId = (): string => {
  if (typeof window === 'undefined') return 'default';

  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  return sessionId;
};

export const chatApi = {
  // Get all chats for the current session
  getChats: async (limit?: number): Promise<Chat[]> => {
    const { data } = await apiClient.get<Chat[]>('/api/v1/chats/', {
      params: { limit },
      headers: {
        'X-Session-ID': getSessionId(),
      },
    });
    return data;
  },

  // Get a specific chat by ID
  getChat: async (chatId: string): Promise<Chat> => {
    const { data } = await apiClient.get<Chat>(`/api/v1/chats/${chatId}`, {
      headers: {
        'X-Session-ID': getSessionId(),
      },
    });
    return data;
  },

  // Start a new chat
  startChat: async (request: StartChatRequest): Promise<Chat> => {
    const { data } = await apiClient.post<Chat>('/api/v1/chats/', request, {
      headers: {
        'X-Session-ID': getSessionId(),
      },
    });
    return data;
  },

  // Continue an existing chat
  continueChat: async (
    chatId: string,
    request: ContinueChatRequest
  ): Promise<Chat> => {
    const { data } = await apiClient.post<Chat>(
      `/api/v1/chats/${chatId}`,
      request,
      {
        headers: {
          'X-Session-ID': getSessionId(),
        },
      }
    );
    return data;
  },
};
