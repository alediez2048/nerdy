// Ad-Ops-Autopilot — Campaign API client

import type {
  CampaignCreate,
  CampaignDetail,
  CampaignListResponse,
  CampaignUpdate,
} from '../types/campaign'
import type { SessionListResponse } from '../types/session'

const API_ORIGIN = import.meta.env.DEV ? 'http://localhost:8000' : ''
const BASE = `${API_ORIGIN}/api/campaigns`

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function createCampaign(
  data: CampaignCreate,
): Promise<CampaignDetail> {
  const resp = await fetch(BASE, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<CampaignDetail>(resp)
}

export async function listCampaigns(params?: {
  status?: string
  offset?: number
  limit?: number
}): Promise<CampaignListResponse> {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.limit !== undefined) query.set('limit', String(params.limit))

  const url = query.toString() ? `${BASE}?${query}` : BASE
  const resp = await fetch(url, { headers: getHeaders() })
  return handleResponse<CampaignListResponse>(resp)
}

export async function getCampaign(
  campaignId: string,
): Promise<CampaignDetail> {
  const resp = await fetch(`${BASE}/${campaignId}`, { headers: getHeaders() })
  return handleResponse<CampaignDetail>(resp)
}

export async function updateCampaign(
  campaignId: string,
  data: CampaignUpdate,
): Promise<CampaignDetail> {
  const resp = await fetch(`${BASE}/${campaignId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<CampaignDetail>(resp)
}

export async function deleteCampaign(campaignId: string): Promise<CampaignDetail> {
  const resp = await fetch(`${BASE}/${campaignId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  })
  return handleResponse<CampaignDetail>(resp)
}

export async function getCampaignSessions(
  campaignId: string,
  params?: {
    offset?: number
    limit?: number
  },
): Promise<SessionListResponse> {
  const query = new URLSearchParams()
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.limit !== undefined) query.set('limit', String(params.limit))

  const url = query.toString() ? `${BASE}/${campaignId}/sessions?${query}` : `${BASE}/${campaignId}/sessions`
  const resp = await fetch(url, { headers: getHeaders() })
  return handleResponse<SessionListResponse>(resp)
}

// PC-12: Campaign duplication
export async function duplicateCampaign(
  campaignId: string,
): Promise<CampaignDetail> {
  const resp = await fetch(`${BASE}/${campaignId}/duplicate`, {
    method: 'POST',
    headers: getHeaders(),
  })
  return handleResponse<CampaignDetail>(resp)
}
