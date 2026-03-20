// PC-07: New Campaign Form
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { createCampaign } from '../api/campaigns'
import type { Audience, CampaignGoal, Persona, SessionType, ModelTier } from '../types/session'
import { PERSONA_LABELS } from '../types/session'

export default function NewCampaignForm() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [audience, setAudience] = useState<Audience | ''>('')
  const [goal, setGoal] = useState<CampaignGoal | ''>('')
  const [persona, setPersona] = useState<Persona>('auto')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [sessionType, setSessionType] = useState<SessionType>('image')
  const [adCount, setAdCount] = useState(50)
  const [qualityThreshold, setQualityThreshold] = useState(7.0)
  const [modelTier, setModelTier] = useState<ModelTier>('standard')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate name
    if (!name.trim()) {
      setError('Campaign name is required')
      return
    }

    setLoading(true)
    try {
      const defaultConfig: Record<string, unknown> = {
        persona,
      }

      if (showAdvanced) {
        defaultConfig.session_type = sessionType
        defaultConfig.ad_count = adCount
        defaultConfig.quality_threshold = qualityThreshold
        defaultConfig.model_tier = modelTier
      }

      const result = await createCampaign({
        name: name.trim(),
        description: description.trim() || undefined,
        audience: audience || undefined,
        campaign_goal: goal || undefined,
        default_config: defaultConfig,
      })
      navigate(`/campaigns/${result.campaign_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign')
    } finally {
      setLoading(false)
    }
  }

  const s = styles

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.header}>
          <button
            type="button"
            onClick={() => navigate('/campaigns')}
            style={s.backLink}
          >
            ← Back to Campaigns
          </button>
          <h1 style={s.title}>New Campaign</h1>
          <p style={s.subtitle}>
            Create a campaign to organize your sessions. Set default settings that will pre-fill when creating sessions within this campaign.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Campaign name - required */}
          <div style={s.field}>
            <label style={s.label}>
              Campaign Name <span style={s.required}>*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Q2 SAT Prep Campaign"
              maxLength={256}
              style={s.input}
              required
            />
          </div>

          {/* Description - optional */}
          <div style={s.field}>
            <label style={s.label}>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description for this campaign"
              rows={3}
              style={s.textarea}
              maxLength={2000}
            />
          </div>

          {/* Default Audience */}
          <div style={s.field}>
            <label style={s.label}>Default Audience</label>
            <div style={s.toggleGroup}>
              {(['parents', 'students'] as Audience[]).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setAudience(opt)}
                  style={audience === opt ? s.toggleActive : s.toggle}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </button>
              ))}
            </div>
            <div style={s.hint}>Leave unset to choose per session</div>
          </div>

          {/* Default Campaign Goal */}
          <div style={s.field}>
            <label style={s.label}>Default Campaign Goal</label>
            <div style={s.toggleGroup}>
              {(['awareness', 'conversion'] as CampaignGoal[]).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setGoal(opt)}
                  style={goal === opt ? s.toggleActive : s.toggle}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </button>
              ))}
            </div>
            <div style={s.hint}>Leave unset to choose per session</div>
          </div>

          {/* Default Persona */}
          <div style={s.field}>
            <label style={s.label}>Default Persona</label>
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value as Persona)}
              style={s.input}
            >
              {(Object.entries(PERSONA_LABELS) as [Persona, string][]).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Advanced Defaults Section */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={s.advancedToggle}
          >
            {showAdvanced ? '▼' : '▶'} Advanced Default Settings
          </button>

          {showAdvanced && (
            <div style={s.advancedSection}>
              <div style={s.field}>
                <label style={s.label}>Default Session Type</label>
                <div style={s.toggleGroup}>
                  {(['image', 'video'] as SessionType[]).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setSessionType(t)}
                      style={sessionType === t ? s.toggleActive : s.toggle}
                    >
                      {t === 'image' ? 'Image Ads' : 'Video Ads'}
                    </button>
                  ))}
                </div>
              </div>

              <div style={s.field}>
                <label style={s.label}>Default Ad Count</label>
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={adCount}
                  onChange={(e) => setAdCount(Number(e.target.value))}
                  style={s.input}
                />
              </div>

              <div style={s.field}>
                <label style={s.label}>Default Quality Threshold</label>
                <input
                  type="number"
                  min={5.0}
                  max={10.0}
                  step={0.1}
                  value={qualityThreshold}
                  onChange={(e) => setQualityThreshold(Number(e.target.value))}
                  style={s.input}
                />
              </div>

              <div style={s.field}>
                <label style={s.label}>Default Model Tier</label>
                <div style={s.toggleGroup}>
                  {(['standard', 'premium'] as ModelTier[]).map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setModelTier(opt)}
                      style={modelTier === opt ? s.toggleActive : s.toggle}
                    >
                      {opt.charAt(0).toUpperCase() + opt.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && <p style={s.error}>{error}</p>}

          <button type="submit" disabled={loading} style={s.submit}>
            {loading ? 'Creating...' : 'Create Campaign'}
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
  header: {
    marginBottom: '32px',
  },
  backLink: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
    marginBottom: '16px',
    padding: 0,
    textDecoration: 'none',
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
    lineHeight: 1.6,
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
  textarea: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: colors.ink,
    color: colors.white,
    fontSize: '14px',
    fontFamily: font.family,
    boxSizing: 'border-box',
    resize: 'vertical',
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
  hint: {
    fontSize: '12px',
    color: colors.muted,
    marginTop: '4px',
  },
  advancedToggle: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    fontFamily: font.family,
    textAlign: 'left',
    marginBottom: '16px',
  },
  advancedSection: {
    marginBottom: '20px',
    padding: '16px',
    background: `${colors.ink}80`,
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}20`,
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
