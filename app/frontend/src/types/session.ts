// Ad-Ops-Autopilot — Session types (matches backend schemas from PA-04, PC-00)

export type SessionType = 'image' | 'video'
export type Audience = 'parents' | 'students'
export type CampaignGoal = 'awareness' | 'conversion'
export type DimensionWeights = 'awareness_profile' | 'conversion_profile' | 'equal'
export type ModelTier = 'standard' | 'premium'
export type AspectRatio = '1:1' | '4:5' | '9:16'
export type VideoAspectRatio = '9:16' | '16:9' | '1:1'
export type VideoProvider = 'fal' | 'veo' | 'kling'

export const VIDEO_PROVIDER_LABELS: Record<VideoProvider, string> = {
  fal: 'Fal.ai (recommended)',
  veo: 'Google Veo 3.1',
  kling: 'Kling AI',
}
export type Persona = 'auto' | 'athlete_recruit' | 'suburban_optimizer' | 'immigrant_navigator' | 'cultural_investor' | 'system_optimizer' | 'neurodivergent_advocate' | 'burned_returner'

export const PERSONA_LABELS: Record<Persona, string> = {
  auto: 'Auto (recommended)',
  athlete_recruit: 'Athlete-Recruit Gatekeeper',
  suburban_optimizer: 'Proactive Suburban Optimizer',
  immigrant_navigator: 'Immigrant Family Navigator',
  cultural_investor: 'Education-First Cultural Investor',
  system_optimizer: 'System Optimizer',
  neurodivergent_advocate: 'Neurodivergent Advocate',
  burned_returner: 'Burned Returner',
}

export const PERSONA_KEY_MESSAGES: Record<Persona, string> = {
  auto: '',
  athlete_recruit: 'SAT score needed for scholarship eligibility',
  suburban_optimizer: "Your child's SAT doesn't match their GPA",
  immigrant_navigator: 'Expert guidance through US college admissions',
  cultural_investor: 'One system to replace scattered resources',
  system_optimizer: 'Close the score gap in 10 weeks',
  neurodivergent_advocate: 'Tutoring that adapts to how your child learns',
  burned_returner: "This time will be different — here's why",
}

export const CREATIVE_BRIEF_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: 'gap_report', label: 'Gap Report (data dashboard)' },
  { value: 'ugc_testimonial', label: 'UGC Testimonial' },
  { value: 'before_after', label: 'Before/After Score' },
  { value: 'lifestyle', label: 'Lifestyle / Aspirational' },
  { value: 'stat_focused', label: 'Stat-Focused' },
] as const

export const CAMERA_MOVEMENT_OPTIONS = [
  { value: '', label: 'Auto' },
  { value: 'handheld', label: 'Handheld (UGC)' },
  { value: 'dolly-in', label: 'Dolly-in' },
  { value: 'tracking', label: 'Tracking Shot' },
  { value: 'static', label: 'Static' },
  { value: 'slow-motion', label: 'Slow Motion' },
] as const

export interface SessionConfig {
  session_type: SessionType
  audience: Audience
  campaign_goal: CampaignGoal
  ad_count: number
  cycle_count: number
  quality_threshold: number
  dimension_weights: DimensionWeights
  model_tier: ModelTier
  budget_cap_usd: number | null
  image_enabled: boolean
  aspect_ratio: AspectRatio
  persona: Persona
  key_message: string
  creative_brief: string
  copy_on_image: boolean
  video_provider: VideoProvider
  video_count: number
  video_duration: number
  video_audio_mode: string
  video_aspect_ratio: VideoAspectRatio
  video_scene: string
  video_visual_style: string
  video_camera_movement: string
  video_subject_action: string
  video_setting: string
  video_lighting_mood: string
  video_audio_detail: string
  video_color_palette: string
  video_negative_prompt: string
}

export interface SessionCreate {
  name?: string
  config: SessionConfig
}

export interface ProgressSummary {
  current_cycle: number
  ads_generated: number
  ads_evaluated: number
  ads_published: number
  current_score_avg: number
  cost_so_far: number
}

export interface SessionAdPreview {
  ad_id: string
  image_url: string | null
  video_url?: string | null
  primary_text: string
  headline: string
  cta_button: string | null
  status: string
  aggregate_score: number
}

export interface SessionSummary {
  id: number
  session_id: string
  name: string | null
  status: string
  config: Record<string, unknown>
  created_at: string
  progress_summary: ProgressSummary | null
  results_summary?: Record<string, unknown> | null
  ad_preview?: SessionAdPreview | null
}

export interface SessionDetail {
  id: number
  session_id: string
  name: string | null
  user_id: string
  config: Record<string, unknown>
  status: string
  celery_task_id: string | null
  results_summary: Record<string, unknown> | null
  ledger_path: string | null
  output_path: string | null
  created_at: string
  updated_at: string | null
  completed_at: string | null
}

export interface SessionListResponse {
  sessions: SessionSummary[]
  total: number
  offset: number
  limit: number
}

export const DEFAULT_CONFIG: SessionConfig = {
  session_type: 'image',
  audience: 'parents',
  campaign_goal: 'conversion',
  ad_count: 50,
  cycle_count: 3,
  quality_threshold: 7.0,
  dimension_weights: 'equal',
  model_tier: 'standard',
  budget_cap_usd: null,
  image_enabled: true,
  aspect_ratio: '1:1',
  persona: 'auto',
  key_message: '',
  creative_brief: 'auto',
  copy_on_image: false,
  video_provider: 'fal',
  video_count: 3,
  video_duration: 8,
  video_audio_mode: 'silent',
  video_aspect_ratio: '9:16',
  video_scene: '',
  video_visual_style: '',
  video_camera_movement: '',
  video_subject_action: '',
  video_setting: '',
  video_lighting_mood: '',
  video_audio_detail: '',
  video_color_palette: '',
  video_negative_prompt: '',
}
