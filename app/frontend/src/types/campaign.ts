// Campaign types

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

// PC-11: Campaign stats
export interface CampaignStats {
  total_sessions: number
  sessions_by_status: Record<string, number>
  total_ads_generated: number
  total_ads_published: number
  avg_quality_score: number
  total_cost: number
  session_types: Record<string, number>
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
  // PC-11: Lightweight summary stats
  total_ads_published?: number
  avg_quality_score?: number
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
  // PC-11: Full stats
  stats: CampaignStats
}

export interface CampaignListResponse {
  campaigns: CampaignSummary[]
  total: number
  offset: number
  limit: number
}
