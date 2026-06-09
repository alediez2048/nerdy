// PJ-07 — Agent + brand-assets shared types.

export type Touchpoint =
  | 'onboarding'
  | 'post_session'
  | 'pre_session_prep'
  | 'refine'

export type Phase =
  | 'identify'
  | 'core'
  | 'extras'
  | 'assets'
  | 'good_enough'
  | 'complete'

export interface BrandProfileSnapshot {
  user_id: string
  business_name: string | null
  industry: string | null
  audience: string | null
  mission: string | null
  value_props: string[]
  tone_descriptors: string[]
  avoid_phrases: string[]
  do_dont_rules: Record<string, unknown> | null
  palette_primary_hex: string | null
  palette_secondary_hex: string | null
  palette_accent_hex: string | null
  logo_asset_id: string | null
  extras: Record<string, unknown>
  onboarding_phase: Phase
  good_enough_at: string | null
}

export interface ConverseRequest {
  touchpoint: Touchpoint
  session_id?: string
  user_message?: string
  uploaded_asset_ids?: string[]
  session_summary?: Record<string, unknown>
  session_type?: string
}

export interface ConverseResponse {
  assistant_message: string
  phase: Phase
  good_enough_now: boolean
  profile_snapshot: BrandProfileSnapshot
  exit_reason?: string
  asset_extractions?: Record<string, unknown>
  proposed_brief?: {
    audience: string
    persona: string
    campaign_goal: string
    key_message: string
    creative_brief: string
  }
}

export interface ProfileStatus {
  phase: Phase
  good_enough_now: boolean
}

export type AssetType = 'logo' | 'style_guide' | 'font' | 'reference' | 'other'

export interface BrandAssetUploadResponse {
  asset_id: string
  storage_path: string
}

export interface ExtractStatusResponse {
  status: 'running' | 'ready' | 'failed' | 'queued'
  extracted_facts?: Record<string, unknown>
  error?: string
  task_id?: string
}
