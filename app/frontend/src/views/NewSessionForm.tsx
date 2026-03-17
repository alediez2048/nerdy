// PA-05: Brief configuration form with progressive disclosure
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { createSession, listSessions } from '../api/sessions'
import type {
  SessionConfig,
  Audience,
  CampaignGoal,
  DimensionWeights,
  ModelTier,
  AspectRatio,
  Persona,
  SessionSummary,
} from '../types/session'
import { DEFAULT_CONFIG, PERSONA_LABELS, PERSONA_KEY_MESSAGES, CREATIVE_BRIEF_OPTIONS } from '../types/session'

export default function NewSessionForm() {
  const navigate = useNavigate()
  const [config, setConfig] = useState<SessionConfig>({ ...DEFAULT_CONFIG })
  const [name, setName] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([])
  const [showClone, setShowClone] = useState(false)

  useEffect(() => {
    listSessions({ limit: 10 })
      .then((res) => setRecentSessions(res.sessions))
      .catch(() => {})
  }, [])

  const update = <K extends keyof SessionConfig>(key: K, value: SessionConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const toggleAspectRatio = (ratio: AspectRatio) => {
    setConfig((prev) => {
      const has = prev.aspect_ratios.includes(ratio)
      const next = has
        ? prev.aspect_ratios.filter((r) => r !== ratio)
        : [...prev.aspect_ratios, ratio]
      return { ...prev, aspect_ratios: next.length ? next : [ratio] }
    })
  }

  const cloneFrom = (session: SessionSummary) => {
    const c = session.config as Record<string, unknown>
    setConfig({
      audience: (c.audience as Audience) || 'parents',
      campaign_goal: (c.campaign_goal as CampaignGoal) || 'conversion',
      ad_count: (c.ad_count as number) || 50,
      cycle_count: (c.cycle_count as number) || 3,
      quality_threshold: (c.quality_threshold as number) || 7.0,
      dimension_weights: (c.dimension_weights as DimensionWeights) || 'equal',
      model_tier: (c.model_tier as ModelTier) || 'standard',
      budget_cap_usd: (c.budget_cap_usd as number | null) ?? null,
      image_enabled: c.image_enabled !== false,
      aspect_ratios: (c.aspect_ratios as AspectRatio[]) || ['1:1'],
      persona: (c.persona as Persona) || 'auto',
      key_message: (c.key_message as string) || '',
      creative_brief: (c.creative_brief as string) || 'auto',
      copy_on_image: c.copy_on_image === true,
    })
    setShowClone(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await createSession({
        name: name || undefined,
        config,
      })
      navigate(`/sessions/${result.session_id}`)
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
        <p style={s.subtitle}>Configure a pipeline run for Varsity Tutors ad generation</p>

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

          {/* Required: Audience */}
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

          {/* Required: Campaign Goal */}
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

          {/* Required: Ad Count */}
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

          {/* Persona selector */}
          <div style={s.field}>
            <label style={s.label}>Target Persona</label>
            <select
              value={config.persona}
              onChange={(e) => {
                const p = e.target.value as Persona
                update('persona', p)
                // Pre-fill key message based on persona
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

          {/* Creative Direction */}
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

          {/* Advanced toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={s.advancedToggle}
          >
            {showAdvanced ? '▼' : '▶'} Advanced Settings
          </button>

          {showAdvanced && (
            <div style={s.advancedSection}>
              {/* Cycle count */}
              <div style={s.field}>
                <label style={s.label}>Cycle Count</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={config.cycle_count}
                  onChange={(e) => update('cycle_count', Number(e.target.value))}
                  style={s.input}
                />
              </div>

              {/* Quality threshold */}
              <div style={s.field}>
                <label style={s.label}>Quality Threshold</label>
                <input
                  type="number"
                  min={5.0}
                  max={10.0}
                  step={0.1}
                  value={config.quality_threshold}
                  onChange={(e) =>
                    update('quality_threshold', Number(e.target.value))
                  }
                  style={s.input}
                />
              </div>

              {/* Dimension weights */}
              <div style={s.field}>
                <label style={s.label}>Dimension Weights</label>
                <select
                  value={config.dimension_weights}
                  onChange={(e) =>
                    update('dimension_weights', e.target.value as DimensionWeights)
                  }
                  style={s.input}
                >
                  <option value="equal">Equal</option>
                  <option value="awareness_profile">Awareness Profile</option>
                  <option value="conversion_profile">Conversion Profile</option>
                </select>
              </div>

              {/* Model tier */}
              <div style={s.field}>
                <label style={s.label}>Model Tier</label>
                <div style={s.toggleGroup}>
                  {(['standard', 'premium'] as ModelTier[]).map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => update('model_tier', opt)}
                      style={
                        config.model_tier === opt ? s.toggleActive : s.toggle
                      }
                    >
                      {opt.charAt(0).toUpperCase() + opt.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Budget cap */}
              <div style={s.field}>
                <label style={s.label}>Budget Cap (USD)</label>
                <input
                  type="number"
                  min={1}
                  step={0.5}
                  value={config.budget_cap_usd ?? ''}
                  onChange={(e) =>
                    update(
                      'budget_cap_usd',
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                  placeholder="No limit"
                  style={s.input}
                />
              </div>

              {/* Image enabled */}
              <div style={s.field}>
                <label style={s.checkLabel}>
                  <input
                    type="checkbox"
                    checked={config.image_enabled}
                    onChange={(e) => update('image_enabled', e.target.checked)}
                  />
                  Enable image generation
                </label>
              </div>

              {/* Aspect ratios */}
              <div style={s.field}>
                <label style={s.label}>Aspect Ratios</label>
                <div style={s.checkGroup}>
                  {(['1:1', '4:5', '9:16'] as AspectRatio[]).map((ratio) => (
                    <label key={ratio} style={s.checkLabel}>
                      <input
                        type="checkbox"
                        checked={config.aspect_ratios.includes(ratio)}
                        onChange={() => toggleAspectRatio(ratio)}
                      />
                      {ratio}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && <p style={s.error}>{error}</p>}

          <button type="submit" disabled={loading} style={s.submit}>
            {loading ? 'Creating...' : 'Create Session'}
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
