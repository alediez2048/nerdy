// PJ-07 — Brand assets upload + vision-pass polling client.
import { clearToken, getAuthTokenSync } from './auth'
import type {
  AssetType,
  BrandAssetUploadResponse,
  ExtractStatusResponse,
} from '../types/agent'

const API_ORIGIN = import.meta.env.DEV ? 'http://localhost:8000' : ''
const BASE = `${API_ORIGIN}/api/brand-assets`

function authHeader(): HeadersInit {
  const token = getAuthTokenSync()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    if (resp.status === 401) {
      clearToken()
      throw new Error('Session expired — please sign in again')
    }
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function uploadAsset(
  file: File,
  assetType: AssetType,
): Promise<BrandAssetUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('asset_type', assetType)
  const resp = await fetch(BASE, {
    method: 'POST',
    headers: authHeader(),
    body: form,
  })
  return handle<BrandAssetUploadResponse>(resp)
}

export async function triggerExtract(
  assetId: string,
): Promise<ExtractStatusResponse> {
  const resp = await fetch(`${BASE}/${assetId}/extract`, {
    method: 'POST',
    headers: authHeader(),
  })
  return handle<ExtractStatusResponse>(resp)
}

export async function getExtractStatus(
  assetId: string,
): Promise<ExtractStatusResponse> {
  const resp = await fetch(`${BASE}/${assetId}/extract/status`, {
    headers: authHeader(),
  })
  return handle<ExtractStatusResponse>(resp)
}

/** Poll status every 1.5s until ready / failed / aborted. */
export async function pollUntilReady(
  assetId: string,
  opts: { intervalMs?: number; maxMs?: number; abortSignal?: AbortSignal } = {},
): Promise<ExtractStatusResponse> {
  const interval = opts.intervalMs ?? 1500
  const max = opts.maxMs ?? 60_000
  const started = Date.now()
  while (Date.now() - started < max) {
    if (opts.abortSignal?.aborted) {
      return { status: 'failed', error: 'aborted' }
    }
    const status = await getExtractStatus(assetId)
    if (status.status === 'ready' || status.status === 'failed') {
      return status
    }
    await new Promise((r) => setTimeout(r, interval))
  }
  return { status: 'failed', error: 'timeout' }
}

export function inferAssetType(file: File): AssetType {
  if (file.type === 'application/pdf') return 'style_guide'
  return 'logo'
}
