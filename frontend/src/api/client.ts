const API_BASE = import.meta.env.VITE_API_BASE_URL
const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID

export interface Thread {
  id: number
  user_id: number
  title: string | null
  created_at: string
}

export async function login(username: string, password: string): Promise<string> {
  const url = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`
  const body = new URLSearchParams({
    grant_type: 'password',
    client_id: KEYCLOAK_CLIENT_ID,
    username,
    password,
  })
  const res = await fetch(url, { method: 'POST', body })
  if (!res.ok) throw new Error('Login failed')
  const data = await res.json()
  return data.access_token
}

export async function getMe(token: string) {
  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to fetch user')
  return res.json()
}

export async function getThreads(token: string): Promise<Thread[]> {
  const res = await fetch(`${API_BASE}/threads`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to fetch threads')
  return res.json()
}

export interface Citation {
  document_id: number | null
  filename: string | null
  chunk_index: number | null
  text_snippet: string
}

export interface ChatMessage {
  role: string
  content: string
  citations: Citation[]
}

export async function startChatTurn(
  token: string,
  threadId: number,
  message: string
): Promise<{ turn_id: string }> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/chat`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? 'Chat request failed')
  }
  return res.json()
}

export async function getActiveTurn(
  token: string,
  threadId: number
): Promise<{ turn_id: string | null }> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/active-turn`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to check active turn')
  return res.json()
}

export type ChatStreamEvent =
  | { event_type: 'text_delta'; data: { delta: string } }
  | { event_type: 'tool_call_started'; data: { tool_name: string } }
  | { event_type: 'tool_call_finished'; data: { tool_name: string } }
  | { event_type: 'turn_complete'; data: { answer: string; citations: Citation[] } }
  | { event_type: 'turn_failed'; data: { error: string } }

/**
 * Hand-rolled SSE reader (not native EventSource — it can't send an Authorization
 * header). Streams events via `onEvent`, tracking the last event id internally so a
 * caller-driven reconnect can resume with Last-Event-ID instead of replaying from zero.
 * Returns the last event id seen, for exactly that purpose.
 */
export async function streamTurn(
  token: string,
  threadId: number,
  turnId: string,
  onEvent: (event: ChatStreamEvent) => void,
  options?: { lastEventId?: string; signal?: AbortSignal }
): Promise<string | undefined> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (options?.lastEventId) headers['Last-Event-ID'] = options.lastEventId

  const res = await fetch(`${API_BASE}/threads/${threadId}/turns/${turnId}/stream`, {
    headers,
    signal: options?.signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(res.status === 404 ? 'Turn not found or expired' : 'Stream failed')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastEventId = options?.lastEventId

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sepIndex
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex)
      buffer = buffer.slice(sepIndex + 2)

      let id: string | undefined
      let eventType = ''
      let data = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('id: ')) id = line.slice(4)
        else if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (id) lastEventId = id
      if (eventType) {
        onEvent({ event_type: eventType, data: JSON.parse(data) } as ChatStreamEvent)
      }
    }
  }

  return lastEventId
}

export async function getMessages(token: string, threadId: number): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to fetch messages')
  return res.json()
}

export async function createThread(token: string, title: string): Promise<Thread> {
  const res = await fetch(`${API_BASE}/threads`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error('Failed to create thread')
  return res.json()
}

export interface Document {
  id: number
  filename: string
  content_type: string
  size: number | null
  status: string
  created_at: string
}

export function uploadViaBackend(
  token: string,
  file: File,
  onProgress: (pct: number) => void
): Promise<Document> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/documents/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        const detail = (() => { try { return JSON.parse(xhr.responseText).detail } catch { return 'Upload failed' } })()
        reject(new Error(detail))
      }
    }

    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(form)
  })
}

export async function getDocuments(token: string): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function getDownloadUrl(token: string, documentId: number): Promise<string> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to get download URL')
  const data = await res.json()
  return data.url
}

export interface PresignResponse {
  document_id: number
  upload_url: string
}

export async function requestPresignedUrl(
  token: string,
  filename: string,
  content_type: string
): Promise<PresignResponse> {
  const res = await fetch(`${API_BASE}/documents/presign`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename, content_type }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? 'Failed to get upload URL')
  }
  return res.json()
}

export function uploadDirect(
  uploadUrl: string,
  file: File,
  onProgress: (pct: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', uploadUrl)
    xhr.setRequestHeader('Content-Type', file.type)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else reject(new Error('Direct upload to storage failed'))
    }

    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(file)
  })
}

export async function confirmUpload(token: string, documentId: number): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? 'Confirm failed')
  }
  return res.json()
}

export async function getDocumentStatus(
  token: string,
  documentId: number
): Promise<{ id: number; status: string }> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/status`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to get document status')
  return res.json()
}

export async function deleteDocument(token: string, documentId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to delete document')
}

export interface SearchResult {
  text: string
  filename: string
  document_id: number
  chunk_index: number
  score: number
}

export async function searchDocuments(
  token: string,
  query: string,
  k = 5
): Promise<SearchResult[]> {
  const res = await fetch(
    `${API_BASE}/search?q=${encodeURIComponent(query)}&k=${k}`,
    { headers: { Authorization: `Bearer ${token}` } }
  )
  if (!res.ok) throw new Error('Search failed')
  return res.json()
}
