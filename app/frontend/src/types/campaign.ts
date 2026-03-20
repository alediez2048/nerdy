// Ad-Ops-Autopilot — Campaign types (matches backend schemas from PC-04)

export interface CampaignCreate {
  name: string
  description?: string | null
  audience?: string | null
  campaign_goal?: string | null
  default_config?: Record<string, unknown>
}

export interface CampaignUpdate {
  name?: string
  description?: string | null
  status?: 'active' | 'archived'
}

export interface CampaignSummary {
  id: number
  campaign_id: string
  name: string
  description: string | null
  audience: string | null
  campaign_goal: string | null
  status: string
  created_at: string
  session_count: number
}

export interface CampaignDetail {
  id: number
  campaign_id: string
  name: string
  description: string | null
  audience: string | null
  campaign_goal: string | null
  default_config: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string | null
  session_count: number
}

export interface CampaignListResponse {
  campaigns: CampaignSummary[]
  total: number
  offset: number
  limit: number
}
