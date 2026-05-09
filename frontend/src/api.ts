import { clearAdminToken, getAdminToken } from './lib/auth'

const API_BASE = import.meta.env.VITE_API_BASE || '/yiyin/api'

export interface LoginResponse {
  access_token: string
  expires_at: string
}

export interface ToggleItem {
  name: string
  enabled: boolean
}

export interface FeatureGroup {
  name: string
  members: string[]
}

export interface ToggleGroup {
  group_id: string
  group_name: string
  toggles: ToggleItem[]
}

export interface ToggleListResponse {
  feature_groups: FeatureGroup[]
  groups: ToggleGroup[]
}

export interface DebugGroupItem {
  group_id: string
  group_name: string
  quote_member_count: number
  quote_count: number
  food_count: number
  token: string
  preview_path: string
}

export interface DebugGroupListResponse {
  groups: DebugGroupItem[]
}

export interface GroupSummary {
  group_id: string
  group_name: string
  quote_member_count: number
  quote_count: number
  food_count: number
  expires_at: string
}

export interface QuoteEntry {
  id: string
  image_url: string
  content?: string
  speaker_name?: string
  avatar_url?: string
}

export interface QuoteMemberGroup {
  member: string
  entries: QuoteEntry[]
}

export interface QuotesResponse {
  group_id: string
  group_name: string
  quote_groups: QuoteMemberGroup[]
}

export interface FoodItem {
  id: string
  name: string
  tags: string[]
  image_url: string
}

export interface FoodsResponse {
  group_id: string
  group_name: string
  items: FoodItem[]
}

async function request<T>(path: string, init: RequestInit = {}, useAdminToken = false): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (useAdminToken) {
    const token = getAdminToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let detail = '请求失败'
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      detail = response.statusText || detail
    }
    if (response.status === 401 && useAdminToken) {
      clearAdminToken()
    }
    throw new Error(detail)
  }

  return (await response.json()) as T
}

export const api = {
  admin: {
    login(password: string) {
      return request<LoginResponse>('/admin/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
    },
    getToggles() {
      return request<ToggleListResponse>('/admin/toggles', {}, true)
    },
    getGroups() {
      return request<DebugGroupListResponse>('/admin/groups', {}, true)
    },
    updateToggle(groupId: string, featureName: string, enabled: boolean) {
      return request<ToggleGroup>(`/admin/toggles/${encodeURIComponent(groupId)}`, {
        method: 'PATCH',
        body: JSON.stringify({ feature_name: featureName, enabled }),
      }, true)
    },
  },
  public: {
    getSummary(groupId: string, token: string) {
      return request<GroupSummary>(`/public/groups/${encodeURIComponent(groupId)}/summary?token=${encodeURIComponent(token)}`)
    },
    getQuotes(groupId: string, token: string) {
      return request<QuotesResponse>(`/public/groups/${encodeURIComponent(groupId)}/quotes?token=${encodeURIComponent(token)}`)
    },
    getFoods(groupId: string, token: string) {
      return request<FoodsResponse>(`/public/groups/${encodeURIComponent(groupId)}/foods?token=${encodeURIComponent(token)}`)
    },
  },
}
