// PJ-07 — Reusable agent chat component.
//
// One component, four consumers (onboarding, post-session, pre-session prep,
// refine). Each touchpoint just supplies its `touchpoint` prop; the
// backend's per-touchpoint prompt + whitelist drives the rest.
//
// The component is responsible for:
//   - Posting turns to /api/agent/converse
//   - Optimistic UX (user message renders before fetch resolves)
//   - File-drop upload → /api/brand-assets → /extract poll → include
//     asset_id in the next /converse
//   - Surfacing terminal exit (`good_enough_now` or `phase === 'complete'`)
//     via `onCompleted`
//
// Touchpoint-agnostic: passing `touchpoint='refine'` or
// `touchpoint='pre_session_prep'` works without any special-case code.
import { useCallback, useEffect, useRef, useState } from 'react'
import { converse } from '../api/agent'
import {
  inferAssetType,
  pollUntilReady,
  triggerExtract,
  uploadAsset,
} from '../api/brandAssets'
import { colors, font, radii } from '../design/tokens'
import type {
  ConverseResponse,
  Phase,
  Touchpoint,
} from '../types/agent'

interface Msg {
  role: 'user' | 'assistant' | 'tool'
  content: string
  /** When set, the message renders as a confirmation card (palette
      swatches, asset upload receipt, etc.) instead of a plain bubble. */
  card?: 'asset_uploaded' | 'asset_extracted' | 'error'
  cardData?: Record<string, unknown>
}

export interface ChatProps {
  touchpoint: Touchpoint
  sessionId?: string
  sessionSummary?: Record<string, unknown>
  sessionType?: string
  /** Called when the assistant emits a terminal `finish_touchpoint`.
      Note: `good_enough_now` is a profile status flag (already-good-
      enough), not a "stop the chat" signal — the agent may flip it
      mid-conversation and keep going. Consumers that want to react to
      gate transitions should use `onPhaseChange` + their own state. */
  onCompleted?: (snap: ConverseResponse) => void
  /** Optional override for the empty-state opening message. If unset,
      we POST an empty /converse turn and let the agent greet itself. */
  initialMessage?: string
  /** Hide the file-drop UI (e.g. for pre-session prep where assets
      don't belong). */
  allowUploads?: boolean
  onPhaseChange?: (phase: Phase) => void
}

export default function Chat({
  touchpoint,
  sessionId,
  sessionSummary,
  sessionType,
  onCompleted,
  initialMessage,
  allowUploads = true,
  onPhaseChange,
}: ChatProps) {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [pendingAssetIds, setPendingAssetIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const scrollerRef = useRef<HTMLDivElement | null>(null)
  // React 18 strict-mode runs effects twice in dev. Use a ref (mutated
  // synchronously) instead of state (committed asynchronously) so the
  // first-turn /converse call doesn't fire twice.
  const openedRef = useRef(false)

  const sendTurn = useCallback(
    async (userMessage: string | undefined, assetIds: string[]) => {
      setPending(true)
      setError(null)
      try {
        const res = await converse({
          touchpoint,
          session_id: sessionId,
          user_message: userMessage,
          uploaded_asset_ids: assetIds.length ? assetIds : undefined,
          session_summary: sessionSummary,
          session_type: sessionType,
        })
        setMsgs((m) => [
          ...m,
          { role: 'assistant', content: res.assistant_message },
        ])
        if (onPhaseChange) onPhaseChange(res.phase)
        // Only treat an explicit `finish_touchpoint` as terminal.
        // `good_enough_now` is a profile-state flag the agent may set
        // mid-turn and continue talking; reacting to it here causes
        // single-turn refine sessions to close immediately the first
        // time we see a profile that's already good_enough_now.
        if (res.exit_reason === 'finish_touchpoint') {
          onCompleted?.(res)
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setPending(false)
      }
    },
    [touchpoint, sessionId, sessionSummary, sessionType, onCompleted, onPhaseChange],
  )

  // First turn: prime the conversation. If `initialMessage` is given,
  // we send it as the user; otherwise we POST an empty turn and let the
  // agent greet itself (PJ-06 kickoff seed).
  useEffect(() => {
    if (openedRef.current) return
    openedRef.current = true
    if (initialMessage) {
      setMsgs([{ role: 'user', content: initialMessage }])
      void sendTurn(initialMessage, [])
    } else {
      void sendTurn(undefined, [])
    }
  }, [initialMessage, sendTurn])

  // Auto-scroll to bottom on new messages.
  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [msgs.length, pending])

  const onSend = useCallback(async () => {
    const text = input.trim()
    if (!text && pendingAssetIds.length === 0) return
    setMsgs((m) => [...m, { role: 'user', content: text || '(uploaded asset)' }])
    setInput('')
    const assetIds = pendingAssetIds
    setPendingAssetIds([])
    await sendTurn(text || undefined, assetIds)
  }, [input, pendingAssetIds, sendTurn])

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    if (!allowUploads) return
    for (const f of Array.from(files)) {
      const tempId = `temp-${Date.now()}-${f.name}`
      setMsgs((m) => [
        ...m,
        {
          role: 'tool',
          content: `Uploading ${f.name}…`,
          card: 'asset_uploaded',
          cardData: { filename: f.name, status: 'uploading', tempId },
        },
      ])
      try {
        const up = await uploadAsset(f, inferAssetType(f))
        await triggerExtract(up.asset_id)
        setMsgs((m) =>
          m.map((msg) =>
            msg.cardData?.tempId === tempId
              ? {
                  ...msg,
                  content: `Analyzing ${f.name}…`,
                  cardData: { ...msg.cardData, status: 'extracting', assetId: up.asset_id },
                }
              : msg,
          ),
        )
        const status = await pollUntilReady(up.asset_id, { maxMs: 90_000 })
        if (status.status === 'ready') {
          setPendingAssetIds((ids) => [...ids, up.asset_id])
          setMsgs((m) =>
            m.map((msg) =>
              msg.cardData?.tempId === tempId
                ? {
                    ...msg,
                    content: `✓ ${f.name} analyzed`,
                    card: 'asset_extracted',
                    cardData: {
                      filename: f.name,
                      assetId: up.asset_id,
                      facts: status.extracted_facts,
                    },
                  }
                : msg,
            ),
          )
        } else {
          setMsgs((m) =>
            m.map((msg) =>
              msg.cardData?.tempId === tempId
                ? {
                    ...msg,
                    content: `${f.name}: ${status.error || 'extraction failed'}`,
                    card: 'error',
                  }
                : msg,
            ),
          )
        }
      } catch (e) {
        setMsgs((m) =>
          m.map((msg) =>
            msg.cardData?.tempId === tempId
              ? {
                  ...msg,
                  content: `${f.name}: ${e instanceof Error ? e.message : 'upload failed'}`,
                  card: 'error',
                }
              : msg,
          ),
        )
      }
    }
  }, [allowUploads])

  return (
    <div
      style={{
        ...s.shell,
        ...(dragOver ? { boxShadow: `inset 0 0 0 2px ${colors.cyan}` } : {}),
      }}
      onDragOver={(e) => {
        if (!allowUploads) return
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        if (allowUploads && e.dataTransfer.files.length > 0) {
          void handleFiles(e.dataTransfer.files)
        }
      }}
    >
      <div ref={scrollerRef} style={s.messages}>
        {msgs.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}
        {pending && <TypingIndicator />}
        {error && <p style={s.error}>{error}</p>}
      </div>

      <div style={s.inputRow}>
        {allowUploads && (
          <>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              style={s.attachBtn}
              title="Attach a logo or style guide"
              disabled={pending}
            >
              + File
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,application/pdf"
              multiple
              hidden
              onChange={(e) => {
                if (e.target.files) void handleFiles(e.target.files)
                e.target.value = ''
              }}
            />
          </>
        )}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={pending ? 'Waiting for the agent…' : 'Type your reply…'}
          style={s.textarea}
          rows={2}
          disabled={pending}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void onSend()
            }
          }}
        />
        <button onClick={onSend} disabled={pending} style={s.sendBtn}>
          {pending ? '…' : 'Send'}
        </button>
      </div>
      {allowUploads && (
        <p style={s.dropHint}>
          Drop a logo (PNG/SVG) or style guide (PDF) here, or click + File.
        </p>
      )}
    </div>
  )
}

// --- Subcomponents -----------------------------------------------

function MessageBubble({ msg }: { msg: Msg }) {
  if (msg.card === 'asset_extracted') {
    const facts = (msg.cardData?.facts ?? {}) as Record<string, unknown>
    const palette =
      (facts['dominant_colors'] as string[] | undefined) ||
      (facts['palette_hex'] as string[] | undefined) ||
      []
    return (
      <div style={s.cardBubble}>
        <strong style={{ color: colors.cyan }}>{msg.content}</strong>
        {palette.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
            {palette.slice(0, 5).map((hex) => (
              <div
                key={hex}
                title={hex}
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '4px',
                  background: hex,
                  border: `1px solid ${colors.muted}40`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    )
  }
  if (msg.card === 'asset_uploaded' || msg.card === 'error') {
    const isErr = msg.card === 'error'
    return (
      <div
        style={{
          ...s.cardBubble,
          color: isErr ? colors.red : colors.muted,
          fontStyle: 'italic',
        }}
      >
        {msg.content}
      </div>
    )
  }
  const isUser = msg.role === 'user'
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        margin: '6px 0',
      }}
    >
      <div
        style={{
          ...s.bubble,
          background: isUser ? `${colors.cyan}1f` : colors.surface,
          color: isUser ? colors.cyan : colors.white,
          border: `1px solid ${isUser ? colors.cyan : colors.muted}30`,
        }}
      >
        {msg.content}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', margin: '6px 0' }}>
      <div
        style={{
          ...s.bubble,
          background: colors.surface,
          color: colors.muted,
          border: `1px solid ${colors.muted}30`,
          fontStyle: 'italic',
        }}
      >
        assistant typing…
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  shell: {
    display: 'flex',
    flexDirection: 'column',
    height: '70vh',
    minHeight: '480px',
    border: `1px solid ${colors.muted}20`,
    borderRadius: radii.card,
    background: colors.ink,
    fontFamily: font.family,
    overflow: 'hidden',
    transition: 'box-shadow 0.15s ease',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 16px 8px',
  },
  bubble: {
    maxWidth: '78%',
    padding: '10px 14px',
    borderRadius: '14px',
    fontSize: '14px',
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  cardBubble: {
    background: `${colors.cyan}0a`,
    border: `1px dashed ${colors.cyan}40`,
    borderRadius: radii.card,
    padding: '10px 14px',
    margin: '6px 0',
    fontSize: '13px',
    color: colors.white,
  },
  error: {
    color: colors.red,
    margin: '8px 0',
    fontSize: '13px',
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
    padding: '10px 12px',
    borderTop: `1px solid ${colors.muted}20`,
    background: colors.surface,
    alignItems: 'flex-end',
  },
  attachBtn: {
    padding: '10px 12px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  textarea: {
    flex: 1,
    padding: '10px 12px',
    border: `1px solid ${colors.muted}40`,
    background: colors.ink,
    color: colors.white,
    borderRadius: radii.button,
    fontFamily: font.family,
    fontSize: '14px',
    resize: 'none',
  },
  sendBtn: {
    padding: '10px 18px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: '#000',
    cursor: 'pointer',
    fontFamily: font.family,
    fontWeight: 700,
    fontSize: '13px',
  },
  dropHint: {
    color: colors.muted,
    fontSize: '11px',
    textAlign: 'center',
    padding: '6px 0',
    margin: 0,
    borderTop: `1px solid ${colors.muted}10`,
  },
}
