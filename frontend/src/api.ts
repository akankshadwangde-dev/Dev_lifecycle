import type { Role } from './types'

export interface Identity { user: string; role: Role; modelId: number | null }

let identity: Identity = { user: 'demo.user', role: 'developer', modelId: null }

export function setIdentity(next: Identity) {
  identity = next
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {
    'X-Studio-User': identity.user,
    'X-Studio-Role': identity.role,
    'X-Studio-Project': '1',
  }
  if (identity.modelId != null) headers['X-Studio-Model'] = String(identity.modelId)
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      /* keep the status text */
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T,>(path: string) => request<T>('GET', path),
  post: <T,>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T,>(path: string, body: unknown) => request<T>('PUT', path, body),
  del: <T,>(path: string) => request<T>('DELETE', path),
}
