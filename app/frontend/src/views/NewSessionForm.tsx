// PA-05 + PC-00: Brief configuration form with progressive disclosure + video track
// PC-09: Campaign pre-fill support
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { createSession, listSessions } from '../api/sessions'
import { getCampaign } from '../api/campaigns'
import type {
  SessionConfig,
  SessionType,
  Audience,
  CampaignGoal,
  DimensionWeights,
  ModelTier,
  AspectRatio,
  VideoAspectRatio,
  VideoProvider,
  Persona,
  SessionSummary,
  FalModelTier,
} from '../types/session'
import {
  DEFAULT_CONFIG,
  PERSONA_LABELS,
  PERSONA_KEY_MESSAGES,
  CREATIVE_BRIEF_OPTIONS,
  CAMERA_MOVEMENT_OPTIONS,
  VIDEO_PROVIDER_LABELS,
  FAL_VIDEO_MODEL_PRESETS,
  FAL_MODEL_TIER_LABELS,
} from '../types/session'

const FAL_PRESET_IDS = new Set(FAL_VIDEO_MODEL_PRESETS.map((p) => p.value))
const FAL_MODEL_FALLBACK = 'fal-ai/veo3'

function normalizeVideoFalModel(id: string): string {
  return FAL_PRESET_IDS.has(id) ? id : FAL_MODEL_FALLBACK
}

export default function NewSessionForm() {
  const navigate = useNavigate()
  const { campaignId } = useParams<{ campaignId?: string }>()
  const [config, setConfig] = useState<SessionConfig>({ ...DEFAULT_CONFIG })
  const [name, setName] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([])
  const [showClone, setShowClone] = useState(false)
  const [campaignName, setCampaignName] = useState<string | null>(null)

  // Load campaign defaults if campaignId is present
  useEffect(() => {
    if (!campaignId) return
    getCampaign(campaignId)
      .then((campaign) => {
        setCampaignName(campaign.name)
        const defaults = campaign.default_config || {}
        
        // Merge campaign defaults into form config
        setConfig((prev) => ({
          ...prev,
          // Override with campaign top-level fields if present
          audience: (campaign.audience as Audience) || prev.audience,
          campaign_goal: (campaign.campaign_goal as CampaignGoal) || prev.campaign_goal,
          // Merge default_config fields
          ...defaults,
          // Ensure required fields are set
          persona: (defaults.persona as Persona) || (campaign.audience ? prev.persona : prev.persona),
        }))
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load campaign defaults')
      })
  }, [campaignId])

  useEffect(() => {
    listSessions({ limit: 10 })
      .then((res) => setRecentSessions(res.sessions))
      .catch(() => {})
  }, [])

  // Legacy configs may have a custom endpoint string; map to a known preset
  useEffect(() => {
    if (config.session_type !== 'video' || config.video_provider !== 'fal') return
    if (!FAL_PRESET_IDS.has(config.video_fal_model)) {
      setConfig((prev) => ({ ...prev, video_fal_model: FAL_MODEL_FALLBACK }))
    }
  }, [config.session_type, config.video_provider, config.video_fal_model])

  const update = <K extends keyof SessionConfig>(key: K, value: SessionConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }


  const cloneFrom = (session: SessionSummary) => {
    const c = session.config as Record<string, unknown>
    setConfig({
      session_type: (c.session_type as SessionType) || 'image',
      audience: (c.audience as Audience) || 'parents',
      campaign_goal: (c.campaign_goal as CampaignGoal) || 'conversion',
      ad_count: (c.ad_count as number) || 50,
      cycle_count: (c.cycle_count as number) || 3,
      quality_threshold: (c.quality_threshold as number) || 7.0,
      dimension_weights: (c.dimension_weights as DimensionWeights) || 'equal',
      model_tier: (c.model_tier as ModelTier) || 'standard',
      budget_cap_usd: (c.budget_cap_usd as number | null) ?? null,
      image_enabled: c.image_enabled !== false,
      aspect_ratio: (c.aspect_ratio as AspectRatio) || (c.aspect_ratios as AspectRatio[])?.[0] || '1:1',
      persona: (c.persona as Persona) || 'auto',
      key_message: (c.key_message as string) || '',
      creative_brief: (c.creative_brief as string) || 'auto',
      copy_on_image: c.copy_on_image === true,
      video_provider: (c.video_provider as VideoProvider) || 'fal',
      video_fal_model: normalizeVideoFalModel((c.video_fal_model as string) || FAL_MODEL_FALLBACK),
      video_count: (c.video_count as number) || 3,
      video_duration: (c.video_duration as number) || 8,
      video_audio_mode: (c.video_audio_mode as string) || 'silent',
      video_aspect_ratio: (c.video_aspect_ratio as VideoAspectRatio) || '9:16',
      video_scene: (c.video_scene as string) || '',
      video_visual_style: (c.video_visual_style as string) || '',
      video_camera_movement: (c.video_camera_movement as string) || '',
      video_subject_action: (c.video_subject_action as string) || '',
      video_setting: (c.video_setting as string) || '',
      video_lighting_mood: (c.video_lighting_mood as string) || '',
      video_audio_detail: (c.video_audio_detail as string) || '',
      video_color_palette: (c.video_color_palette as string) || '',
      video_negative_prompt: (c.video_negative_prompt as string) || '',
    })
    setShowClone(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payloadConfig =
        config.session_type === 'video' && config.video_provider === 'fal'
          ? { ...config, video_fal_model: normalizeVideoFalModel(config.video_fal_model) }
          : config
      const result = await createSession({
        name: name || undefined,
        config: payloadConfig,
        campaign_id: campaignId,
      })
      // Navigate to campaign detail if created from campaign, otherwise to session detail
      if (campaignId) {
        navigate(`/campaigns/${campaignId}`)
      } else {
        navigate(`/sessions/${result.session_id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session')
    } finally {
      setLoading(false)
    }
  }

  const s = styles

  return (
    <div style={s.page}>
      <div style={s.card}>
        <h1 style={s.title}>New Session</h1>
        <p style={s.subtitle}>Configure a pipeline run for ad generation</p>

        {campaignId && campaignName && (
          <div style={s.campaignBanner}>
            <span style={s.campaignBannerText}>
              Creating session for <strong>{campaignName}</strong>
            </span>
            <button
              type="button"
              onClick={() => navigate(`/campaigns/${campaignId}`)}
              style={s.campaignBannerLink}
            >
              ← Back to Campaign
            </button>
          </div>
        )}

        {recentSessions.length > 0 && (
          <div style={s.cloneSection}>
            <button
              type="button"
              onClick={() => setShowClone(!showClone)}
              style={s.cloneButton}
            >
              Clone from previous
            </button>
            {showClone && (
              <div style={s.cloneDropdown}>
                {recentSessions.map((sess) => (
                  <button
                    key={sess.session_id}
                    onClick={() => cloneFrom(sess)}
                    style={s.cloneItem}
                  >
                    {sess.name || sess.session_id} — {sess.status}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Session type toggle */}
          <div style={s.field}>
            <label style={s.label}>Session Type <span style={s.required}>*</span></label>
            <div style={s.toggleGroup}>
              {([
                { type: 'image' as SessionType, imageEnabled: false, label: 'Copy Only' },
                { type: 'image' as SessionType, imageEnabled: true, label: 'Copy + Image' },
                { type: 'video' as SessionType, imageEnabled: false, label: 'Copy + Video' },
              ]).map(({ type, imageEnabled, label }) => {
                const isActive = config.session_type === type && config.image_enabled === imageEnabled
                const isVideo = type === 'video'
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => {
                      update('session_type', type)
                      update('image_enabled', imageEnabled)
                    }}
                    style={isActive ? (isVideo ? s.toggleActiveVideo : s.toggleActive) : s.toggle}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <div style={s.hint}>
              {config.session_type === 'video'
                ? 'Generate copy + video ads for Stories/Reels placements'
                : config.image_enabled
                  ? 'Generate copy + image ads for Meta feed placements'
                  : 'Generate ad copy only — no images or video'}
            </div>
          </div>

          {/* Session name */}
          <div style={s.field}>
            <label style={s.label}>Session Name (optional)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Auto-generated if empty"
              style={s.input}
            />
          </div>

          {/* Shared fields: Audience */}
          <div style={s.field}>
            <label style={s.label}>
              Audience <span style={s.required}>*</span>
            </label>
            <div style={s.toggleGroup}>
              {(['parents', 'students'] as Audience[]).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => update('audience', opt)}
                  style={config.audience === opt ? s.toggleActive : s.toggle}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Shared fields: Campaign Goal */}
          <div style={s.field}>
            <label style={s.label}>
              Campaign Goal <span style={s.required}>*</span>
            </label>
            <div style={s.toggleGroup}>
              {(['awareness', 'conversion'] as CampaignGoal[]).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => update('campaign_goal', opt)}
                  style={
                    config.campaign_goal === opt ? s.toggleActive : s.toggle
                  }
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Shared: Persona selector */}
          <div style={s.field}>
            <label style={s.label}>Target Persona</label>
            <select
              value={config.persona}
              onChange={(e) => {
                const p = e.target.value as Persona
                update('persona', p)
                const msg = PERSONA_KEY_MESSAGES[p] || ''
                if (msg) update('key_message', msg)
              }}
              style={s.input}
            >
              {(Object.entries(PERSONA_LABELS) as [Persona, string][]).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>

          {/* Shared: Key Message */}
          <div style={s.field}>
            <label style={s.label}>Key Message</label>
            <input
              type="text"
              value={config.key_message}
              onChange={(e) => update('key_message', e.target.value)}
              placeholder="What's the core message? (auto-fills from persona)"
              style={s.input}
            />
          </div>

          {/* ===== COPY / IMAGE FIELDS ===== */}
          {config.session_type === 'image' && (
            <>
              <div style={s.field}>
                <label style={s.label}>
                  Ad Count <span style={s.required}>*</span>
                </label>
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={config.ad_count}
                  onChange={(e) => update('ad_count', Number(e.target.value))}
                  style={s.input}
                />
              </div>

              <div style={s.field}>
                <label style={s.label}>Creative Brief</label>
                <select
                  value={config.creative_brief}
                  onChange={(e) => update('creative_brief', e.target.value)}
                  style={s.input}
                >
                  {CREATIVE_BRIEF_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Image-specific fields — hidden for copy-only */}
              {config.image_enabled && (
                <div style={s.field}>
                  <label style={s.checkLabel}>
                    <input
                      type="checkbox"
                      checked={config.copy_on_image}
                      onChange={(e) => update('copy_on_image', e.target.checked)}
                    />
                    Include headline text on generated images
                  </label>
                </div>
              )}

              {/* Advanced Settings */}
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={s.advancedToggle}
              >
                {showAdvanced ? '▼' : '▶'} Advanced Settings
              </button>

              {showAdvanced && (
                <div style={s.advancedSection}>
                  <div style={s.field}>
                    <label style={s.label}>Cycle Count</label>
                    <input type="number" min={1} max={10} value={config.cycle_count}
                      onChange={(e) => update('cycle_count', Number(e.target.value))} style={s.input} />
                  </div>
                  <div style={s.field}>
                    <label style={s.label}>Quality Threshold</label>
                    <input type="number" min={5.0} max={10.0} step={0.1} value={config.quality_threshold}
                      onChange={(e) => update('quality_threshold', Number(e.target.value))} style={s.input} />
                  </div>
                  <div style={s.field}>
                    <label style={s.label}>Dimension Weights</label>
                    <select value={config.dimension_weights}
                      onChange={(e) => update('dimension_weights', e.target.value as DimensionWeights)} style={s.input}>
                      <option value="equal">Equal</option>
                      <option value="awareness_profile">Awareness Profile</option>
                      <option value="conversion_profile">Conversion Profile</option>
                    </select>
                  </div>
                  <div style={s.field}>
                    <label style={s.label}>Model Tier</label>
                    <div style={s.toggleGroup}>
                      {(['standard', 'premium'] as ModelTier[]).map((opt) => (
                        <button key={opt} type="button" onClick={() => update('model_tier', opt)}
                          style={config.model_tier === opt ? s.toggleActive : s.toggle}>
                          {opt.charAt(0).toUpperCase() + opt.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div style={s.field}>
                    <label style={s.label}>Budget Cap (USD)</label>
                    <input type="number" min={1} step={0.5} value={config.budget_cap_usd ?? ''}
                      onChange={(e) => update('budget_cap_usd', e.target.value ? Number(e.target.value) : null)}
                      placeholder="No limit" style={s.input} />
                  </div>
                  {config.image_enabled && (
                    <div style={s.field}>
                      <label style={s.label}>Aspect Ratio</label>
                      <div style={s.checkGroup}>
                        {(['1:1', '4:5', '9:16'] as AspectRatio[]).map((ratio) => (
                          <label key={ratio} style={s.checkLabel}>
                            <input type="radio" name="aspect_ratio"
                              checked={config.aspect_ratio === ratio}
                              onChange={() => update('aspect_ratio', ratio)} />
                            {ratio}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* ===== VIDEO-ONLY FIELDS ===== */}
          {config.session_type === 'video' && (
            <>
              <div style={s.field}>
                <label style={s.label}>Video Provider</label>
                <div style={s.toggleGroup}>
                  {(['fal', 'veo', 'kling'] as VideoProvider[]).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => update('video_provider', p)}
                      style={config.video_provider === p ? s.toggleActiveVideo : s.toggle}
                    >
                      {VIDEO_PROVIDER_LABELS[p]}
                    </button>
                  ))}
                </div>
              </div>

              {config.video_provider === 'fal' && (
                <div style={s.field}>
                  <label style={s.label}>
                    Fal model <span style={s.required}>*</span>
                  </label>
                  <p style={{ ...s.hint, marginBottom: '8px' }}>
                    Serverless endpoints on Fal — tiers are rough guides; confirm current $ on{' '}
                    <a href="https://fal.ai/models" target="_blank" rel="noreferrer" style={{ color: colors.cyan }}>
                      fal.ai/models
                    </a>
                    .
                  </p>
                  <select
                    value={normalizeVideoFalModel(config.video_fal_model)}
                    onChange={(e) => update('video_fal_model', e.target.value)}
                    style={s.input}
                  >
                    {(['budget', 'balanced', 'premium'] as FalModelTier[]).map((tier) => (
                      <optgroup key={tier} label={FAL_MODEL_TIER_LABELS[tier]}>
                        {FAL_VIDEO_MODEL_PRESETS.filter((p) => p.tier === tier).map((p) => (
                          <option key={p.value} value={p.value} title={p.hint}>
                            {p.label}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  <div style={s.hint}>
                    {FAL_VIDEO_MODEL_PRESETS.find((p) => p.value === normalizeVideoFalModel(config.video_fal_model))
                      ?.hint ?? ''}
                  </div>
                </div>
              )}

              <div style={s.field}>
                <label style={s.label}>
                  Video Count <span style={s.required}>*</span>
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={config.video_count}
                  onChange={(e) => update('video_count', Number(e.target.value))}
                  style={s.input}
                />
                <div style={s.hint}>Cost varies widely by provider and model — check provider pricing.</div>
              </div>

              <div style={s.field}>
                <label style={s.label}>Duration</label>
                <div style={s.toggleGroup}>
                  {[8].map((d) => (
                    <button key={d} type="button"
                      onClick={() => update('video_duration', d)}
                      style={config.video_duration === d ? s.toggleActiveVideo : s.toggle}>
                      {d}s
                    </button>
                  ))}
                </div>
              </div>

              <div style={s.field}>
                <label style={s.label}>Audio</label>
                <div style={s.toggleGroup}>
                  {[{ v: 'silent', l: 'Silent' }, { v: 'with_audio', l: 'With Audio' }].map(({ v, l }) => (
                    <button key={v} type="button"
                      onClick={() => update('video_audio_mode', v)}
                      style={config.video_audio_mode === v ? s.toggleActiveVideo : s.toggle}>
                      {l}
                    </button>
                  ))}
                </div>
                <div style={s.hint}>
                  {config.video_audio_mode === 'silent'
                    ? 'No dialogue or music — text overlays carry the message'
                    : 'AI-generated audio — doubles credit cost'}
                </div>
              </div>

              <div style={s.field}>
                <label style={s.label}>Aspect Ratio</label>
                <div style={s.checkGroup}>
                  {(['9:16', '16:9', '1:1'] as VideoAspectRatio[]).map((ratio) => (
                    <label key={ratio} style={s.checkLabel}>
                      <input type="radio" name="video_aspect_ratio"
                        checked={config.video_aspect_ratio === ratio}
                        onChange={() => update('video_aspect_ratio', ratio)} />
                      {ratio}{ratio === '9:16' ? ' (Stories/Reels)' : ratio === '16:9' ? ' (YouTube/Web)' : ' (Feed)'}
                    </label>
                  ))}
                </div>
              </div>

              {/* Video Advanced Settings — 8-part prompt framework */}
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={s.advancedToggle}
              >
                {showAdvanced ? '▼' : '▶'} Advanced Video Settings
              </button>

              {showAdvanced && (
                <div style={s.advancedSection}>
                  <div style={s.hint}>
                    Leave blank to auto-generate from persona and key message. Fill in for full creative control.
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Scene</label>
                    <textarea value={config.video_scene}
                      onChange={(e) => update('video_scene', e.target.value)}
                      placeholder="One-sentence summary: e.g. 'Parent and student celebrate SAT score at kitchen table'"
                      style={s.textarea} rows={2} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Visual Style</label>
                    <input type="text" value={config.video_visual_style}
                      onChange={(e) => update('video_visual_style', e.target.value)}
                      placeholder="UGC realistic, shot on phone"
                      style={s.input} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Camera Movement</label>
                    <select value={config.video_camera_movement}
                      onChange={(e) => update('video_camera_movement', e.target.value)}
                      style={s.input}>
                      {CAMERA_MOVEMENT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Subject & Action</label>
                    <textarea value={config.video_subject_action}
                      onChange={(e) => update('video_subject_action', e.target.value)}
                      placeholder="Who is in the scene and what are they doing?"
                      style={s.textarea} rows={2} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Background / Setting</label>
                    <input type="text" value={config.video_setting}
                      onChange={(e) => update('video_setting', e.target.value)}
                      placeholder="Bright home study area, afternoon sunlight"
                      style={s.input} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Lighting & Mood</label>
                    <input type="text" value={config.video_lighting_mood}
                      onChange={(e) => update('video_lighting_mood', e.target.value)}
                      placeholder="Natural, soft morning light"
                      style={s.input} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Audio Detail</label>
                    <textarea value={config.video_audio_detail}
                      onChange={(e) => update('video_audio_detail', e.target.value)}
                      placeholder="Ambient classroom sounds, no dialogue"
                      style={s.textarea} rows={2} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Color Palette</label>
                    <input type="text" value={config.video_color_palette}
                      onChange={(e) => update('video_color_palette', e.target.value)}
                      placeholder="Brand teal #17e2ea, navy #0a2240"
                      style={s.input} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Negative Prompt</label>
                    <textarea value={config.video_negative_prompt}
                      onChange={(e) => update('video_negative_prompt', e.target.value)}
                      placeholder="no text, no subtitles, no brand logos"
                      style={s.textarea} rows={2} />
                  </div>

                  <div style={s.field}>
                    <label style={s.label}>Budget Cap (USD)</label>
                    <input type="number" min={1} step={0.5} value={config.budget_cap_usd ?? ''}
                      onChange={(e) => update('budget_cap_usd', e.target.value ? Number(e.target.value) : null)}
                      placeholder="No limit" style={s.input} />
                  </div>
                </div>
              )}
            </>
          )}

          {error && <p style={s.error}>{error}</p>}

          <button type="submit" disabled={loading} style={s.submit}>
            {loading ? 'Creating...' : config.session_type === 'video' ? 'Create Video Session' : 'Create Session'}
          </button>
        </form>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: colors.ink,
    display: 'flex',
    paddingTop: '96px', // Adjusted for NavBar (64px + 32px top padding)
    justifyContent: 'center',
    padding: '40px 20px',
    fontFamily: font.family,
  },
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '40px',
    width: '100%',
    maxWidth: '600px',
    color: colors.white,
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 8px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    color: colors.muted,
    margin: '0 0 24px',
    fontSize: '14px',
  },
  campaignBanner: {
    background: `${colors.cyan}15`,
    border: `1px solid ${colors.cyan}40`,
    borderRadius: radii.input,
    padding: '12px 16px',
    marginBottom: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  campaignBannerText: {
    color: colors.cyan,
    fontSize: '14px',
    fontFamily: font.family,
  },
  campaignBannerLink: {
    background: 'transparent',
    border: `1px solid ${colors.cyan}40`,
    borderRadius: radii.button,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '12px',
    padding: '6px 12px',
    fontFamily: font.family,
  },
  field: { marginBottom: '20px' },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: '6px',
    color: colors.white,
  },
  required: { color: colors.red },
  input: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: colors.ink,
    color: colors.white,
    fontSize: '14px',
    fontFamily: font.family,
    boxSizing: 'border-box',
  },
  toggleGroup: { display: 'flex', gap: '8px' },
  toggle: {
    padding: '8px 20px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
  },
  toggleActive: {
    padding: '8px 20px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}20`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
  },
  toggleActiveVideo: {
    padding: '8px 20px',
    borderRadius: radii.button,
    border: `1px solid ${colors.lightPurple}`,
    background: `${colors.lightPurple}20`,
    color: colors.lightPurple,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
  },
  advancedToggle: {
    background: 'none',
    border: 'none',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '14px',
    padding: '8px 0',
    marginBottom: '12px',
    fontFamily: font.family,
  },
  advancedSection: {
    borderTop: `1px solid ${colors.muted}20`,
    paddingTop: '16px',
    marginBottom: '16px',
  },
  hint: {
    fontSize: '12px',
    color: colors.muted,
    marginTop: '6px',
  },
  textarea: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: colors.ink,
    color: colors.white,
    fontSize: '14px',
    fontFamily: font.family,
    boxSizing: 'border-box' as const,
    resize: 'vertical' as const,
  },
  checkLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: colors.white,
    fontSize: '14px',
    cursor: 'pointer',
  },
  checkGroup: { display: 'flex', gap: '16px' },
  cloneSection: { marginBottom: '20px' },
  cloneButton: {
    padding: '6px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: font.family,
  },
  cloneDropdown: {
    marginTop: '8px',
    background: colors.ink,
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    overflow: 'hidden',
  },
  cloneItem: {
    display: 'block',
    width: '100%',
    padding: '10px 14px',
    background: 'transparent',
    border: 'none',
    borderBottom: `1px solid ${colors.muted}20`,
    color: colors.white,
    cursor: 'pointer',
    textAlign: 'left',
    fontSize: '13px',
    fontFamily: font.family,
  },
  error: {
    color: colors.red,
    fontSize: '14px',
    margin: '0 0 12px',
  },
  submit: {
    width: '100%',
    padding: '14px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '16px',
    cursor: 'pointer',
    fontFamily: font.family,
    marginTop: '8px',
  },
}
