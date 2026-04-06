/**
 * Conversation history API client
 * Frontend wrapper for backend conversation endpoints
 */

export interface ConversationItem {
  id: string;
  title: string;
  updated_at: string;
  is_active: boolean;
}

export interface ConversationListResponse {
  conversations: ConversationItem[];
}

export interface ConversationMessage {
  role: string;
  content: string;
  created_at: string;
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  messages: ConversationMessage[];
}

export interface CreateConversationRequest {
  title?: string;
}

export interface CreateConversationResponse {
  id: string;
  title: string;
}

export interface AddMessageRequest {
  role: string;
  content: string;
}

export interface AddMessageResponse {
  success: boolean;
  message_id: string;
}

export interface UpdateConversationTitleRequest {
  title: string;
}

export interface SuccessResponse {
  success: boolean;
}

export interface DeleteConversationResponse {
  success: boolean;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('token');
  if (token) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }
  return {
    'Content-Type': 'application/json',
  };
}

export async function listConversations(): Promise<ConversationListResponse> {
  /** Get all conversations for current user */
  const response = await fetch(`${API_BASE}/api/conversations`, {
    method: 'GET',
    headers: getAuthHeader(),
  });
  if (!response.ok) {
    throw new Error(`Failed to list conversations: ${response.status}`);
  }
  return await response.json();
}

export async function getConversation(id: string): Promise<ConversationDetailResponse> {
  /** Get full conversation details with all messages */
  const response = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: 'GET',
    headers: getAuthHeader(),
  });
  if (!response.ok) {
    throw new Error(`Failed to get conversation: ${response.status}`);
  }
  return await response.json();
}

export async function createConversation(title?: string): Promise<CreateConversationResponse> {
  /** Create a new conversation */
  const body: CreateConversationRequest = {};
  if (title) {
    body.title = title;
  }

  const response = await fetch(`${API_BASE}/api/conversations`, {
    method: 'POST',
    headers: getAuthHeader(),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.status}`);
  }
  return await response.json();
}

export async function addMessage(
  conversationId: string,
  role: string,
  content: string
): Promise<AddMessageResponse> {
  /** Add a new message to a conversation */
  const body: AddMessageRequest = { role, content };

  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: getAuthHeader(),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Failed to add message: ${response.status}`);
  }
  return await response.json();
}

export async function updateConversationTitle(
  conversationId: string,
  title: string
): Promise<SuccessResponse> {
  /** Update conversation title */
  const body: UpdateConversationTitleRequest = { title };

  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
    method: 'PUT',
    headers: getAuthHeader(),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Failed to update title: ${response.status}`);
  }
  return await response.json();
}

export async function deleteConversation(conversationId: string): Promise<DeleteConversationResponse> {
  /** Delete a conversation */
  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: getAuthHeader(),
  });
  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.status}`);
  }
  return await response.json();
}

export async function setConversationActive(conversationId: string): Promise<SuccessResponse> {
  /** Set a conversation as active for the current user */
  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/active`, {
    method: 'PUT',
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`Failed to set conversation as active: ${response.status}`);
  }

  return await response.json();
}
