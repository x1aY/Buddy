# Fix Active Conversation Persistence Bug Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the bug where the active conversation is not properly persisted when switching conversations and refreshing the page. Currently, when a user switches from conversation A to conversation B and refreshes the page, it still shows conversation A instead of B.

**Architecture:** 
1. Add a new backend API endpoint to set a conversation as active
2. Update the frontend API client to call this endpoint
3. Modify the frontend VideoCallPage.vue to call the new endpoint when switching conversations

**Tech Stack:** 
- Backend: Python, FastAPI
- Frontend: Vue 3, TypeScript

---

## Task 1: Add backend API endpoint to set conversation as active

**Files:**
- Modify: `/Users/x1ay/Documents/AIcode/SeeWorldWeb/backend/api/conversations.py`

- [ ] **Step 1: Add the new endpoint to conversations API**

```python
@router.put("/{conversation_id}/active", response_model=SuccessResponse)
def set_conversation_active(
    conversation_id: UUID,
    user_id: str = Depends(get_user_id_from_token)
) -> SuccessResponse:
    """Set a conversation as the active one for the user.
    
    Args:
        conversation_id: Conversation UUID to set as active
        user_id: Current authenticated user ID
    
    Returns:
        Success status
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to set this conversation as active")
    
    # Set this as the active conversation
    set_active_conversation(user_id, conversation_id)
    
    return SuccessResponse(success=True)
```

- [ ] **Step 2: Verify the endpoint works**
  - Run the backend server
  - Test the endpoint using curl or API client
  - Check that the `is_active` field is properly updated in the CSV file

- [ ] **Step 3: Commit the backend changes**

```bash
git add /Users/x1ay/Documents/AIcode/SeeWorldWeb/backend/api/conversations.py
git commit -m "feat: add endpoint to set conversation as active"
```

---

## Task 2: Update frontend API client to call the new endpoint

**Files:**
- Modify: `/Users/x1ay/Documents/AIcode/SeeWorldWeb/frontend/src/api/conversations.ts`

- [ ] **Step 1: Add the new API method**

```typescript
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
```

- [ ] **Step 2: Commit the frontend API changes**

```bash
git add /Users/x1ay/Documents/AIcode/SeeWorldWeb/frontend/src/api/conversations.ts
git commit -m "feat: add API method to set conversation as active"
```

---

## Task 3: Update VideoCallPage.vue to use the new endpoint

**Files:**
- Modify: `/Users/x1ay/Documents/AIcode/SeeWorldWeb/frontend/src/components/VideoCallPage.vue`

- [ ] **Step 1: Import the new API method**

```typescript
import * as ConversationApi from '@/api/conversations';
```

- [ ] **Step 2: Update switchConversation function to call the new endpoint**

```typescript
const switchConversation = async (conversationId: string) => {
  try {
    const response = await ConversationApi.getConversation(conversationId);
    // Convert to frontend ConversationMessage format
    const loadedMessages: ConversationMessage[] = response.messages.map(msg => ({
      id: `${Date.now()}-${Math.random()}`,
      role: (msg.role === 'model' ? 'model' : 'user') as 'user' | 'model',
      text: msg.content,
      timestamp: Date.now()
    }));

    // If we already have unsaved messages from user speaking while loading, keep them
    // Only replace if the loaded conversation actually has messages
    if (loadedMessages.length > 0 || conversationMessages.value.length === 0) {
      conversationMessages.value = loadedMessages;
    }
    // Otherwise: keep existing unsaved messages since they'll be saved later

    currentConversationId.value = conversationId;
    historyDropdownOpen.value = false;
    
    // Set the conversation as active on the backend
    await ConversationApi.setConversationActive(conversationId);
  } catch (err) {
    console.error('Failed to switch conversation:', err);
    alert('加载对话失败，请重试');
  }
};
```

- [ ] **Step 3: Commit the frontend changes**

```bash
git add /Users/x1ay/Documents/AIcode/SeeWorldWeb/frontend/src/components/VideoCallPage.vue
git commit -m "fix: persist active conversation when switching conversations"
```

---

## Task 4: Test the fix

**Files:**
- Test: `/Users/x1ay/Documents/AIcode/SeeWorldWeb/frontend/src/components/VideoCallPage.vue`

- [ ] **Step 1: Test the fix by following these steps**
  1. Run both frontend and backend servers
  2. Create conversation A
  3. Switch to conversation B from the history dropdown
  4. Refresh the page
  5. Verify that conversation B is now loaded instead of conversation A

- [ ] **Step 2: Run any existing tests**
  - Check if there are any existing tests that need to be updated
  - Run the tests to ensure the fix doesn't break anything

---

## Summary

This fix will ensure that when a user switches conversations, the new active conversation is properly persisted on the backend and will be correctly loaded when the page is refreshed.
