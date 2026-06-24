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
