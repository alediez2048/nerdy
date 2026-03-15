// Progress event types — matches backend event schema

export interface ProgressEvent {
  type: string
  cycle: number
  batch: number
  ads_generated: number
  ads_evaluated: number
  ads_published: number
  current_score_avg: number
  cost_so_far: number
  timestamp: number
  error?: string
  // Ad detail (if included in ad_evaluated events)
  ad_id?: string
  score?: number
  copy?: string
  scores?: Record<string, number>
}
