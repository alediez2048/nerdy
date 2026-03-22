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

/** Rough price/quality tier for Fal presets (copy-only UX; check fal.ai pricing). */
export type FalModelTier = 'budget' | 'balanced' | 'premium'

export const FAL_MODEL_TIER_LABELS: Record<FalModelTier, string> = {
  budget: 'Budget — best for drafts & volume',
  balanced: 'Balanced — quality vs cost',
  premium: 'Premium — highest quality ($$$)',
}

/** Fal.ai serverless endpoint IDs — passed to Fal `subscribe()` when Video Provider is Fal. */
export const FAL_VIDEO_MODEL_PRESETS: {
  value: string
  label: string
  tier: FalModelTier
  hint: string
}[] = [
  {
    value: 'fal-ai/wan/v2.2-5b/text-to-video/distill',
    label: 'Wan 2.2 · 5B distill',
    tier: 'budget',
    hint: 'Fast distil; lower cost, good for iteration (check Fal for resolution caps).',
  },
  {
    value: 'fal-ai/minimax/hailuo-02/standard/text-to-video',
    label: 'MiniMax Hailuo 02 · Standard',
    tier: 'budget',
    hint: 'Often among the cheaper $/s options on Fal; 768p class.',
  },
  {
    value: 'fal-ai/kling-video/v2.1/standard',
    label: 'Kling v2.1 · Standard',
    tier: 'balanced',
    hint: 'Strong all‑rounder on Fal; mid-tier cost vs Wan distill.',
  },
  {
    value: 'fal-ai/wan-22',
    label: 'Wan 2.2 · full',
    tier: 'balanced',
    hint: 'Full Wan 2.2 (not distil); better motion than 5B distill, more $ than distill.',
  },
  {
    value: 'fal-ai/minimax/hailuo-2.3/pro/text-to-video',
    label: 'MiniMax Hailuo 2.3 · Pro',
    tier: 'premium',
    hint: '1080p-class Pro; high quality, higher cost than Hailuo 02 Standard.',
  },
  {
    value: 'fal-ai/veo3',
    label: 'Veo 3',
    tier: 'premium',
    hint: 'Google Veo-class on Fal; flagship quality, typically the priciest tier.',
  },
]
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
  /** Fal serverless model id when video_provider is fal (e.g. fal-ai/veo3). */
  video_fal_model: string
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
  video_remote_url?: string | null
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
  campaign_id?: string | null
  campaign_name?: string | null
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
  video_fal_model: 'fal-ai/veo3',
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
