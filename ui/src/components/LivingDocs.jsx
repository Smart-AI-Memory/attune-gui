import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function personaLabel(p) {
  return { end_user: 'End User', developer: 'Developer', support: 'Support', author: 'Author' }[p] ?? p
}

function StatusBadge({ status }) {
  return <span className={`ld-badge ld-badge-${status}`}>{status}</span>
}

function TriggerBadge({ trigger }) {
  const labels = { manual: 'Manual', git_hook: 'Git Hook', scheduled: 'Scheduled' }
  return <span className="ld-trigger-badge">{labels[trigger] ?? trigger}</span>
}

// ---------------------------------------------------------------------------
// Health panel
// ---------------------------------------------------------------------------

function QualityBar({ label, value, gate }) {
  const pct = Math.round(value * 100)
  const passing = value >= gate
  return (
    <div className="ld-quality-bar">
      <div className="ld-quality-bar-header">
        <span>{label}</span>
        <span className={passing ? 'ld-ok' : 'ld-danger'}>{pct}%</span>
      </div>
      <div className="ld-bar-track">
        <div
          className="ld-bar-fill"
          style={{ width: `${pct}%`, background: passing ? 'var(--ok)' : 'var(--danger)' }}
        />
        <div className="ld-bar-gate" style={{ left: `${gate * 100}%` }} title={`Gate ≥${gate * 100}%`} />
      </div>
      <div className="ld-bar-labels">
        <span />
        <span className="ld-dim" style={{ position: 'absolute', left: `${gate * 100}%`, transform: 'translateX(-50%)' }}>
          {gate * 100}%
        </span>
      </div>
    </div>
  )
}

function WorkspaceEditor({ workspace, hasHelpDir, onSave }) {
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState(workspace ?? '')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!editing) setInput(workspace ?? '')
  }, [workspace, editing])

  async function handleSave() {
    setSaving(true)
    setErr(null)
    try {
      await onSave(input)
      setEditing(false)
    } catch (e) {
      setErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="ld-workspace-row">
      <span className="ld-workspace-label">Workspace</span>
      {editing ? (
        <div className="ld-workspace-edit">
          <input
            className="ld-workspace-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false) }}
            autoFocus
          />
          <button className="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button className="ghost" onClick={() => { setEditing(false); setErr(null) }}>Cancel</button>
          {err && <span className="ld-danger" style={{ fontSize: '0.75rem' }}>{err}</span>}
        </div>
      ) : (
        <div className="ld-workspace-display">
          <span className="ld-mono ld-workspace-path">{workspace || '—'}</span>
          <span className={hasHelpDir ? 'ld-ok' : 'ld-warn'} style={{ fontSize: '0.75rem' }}>
            {hasHelpDir ? '.help ✓' : 'no .help'}
          </span>
          <button className="ghost" onClick={() => setEditing(true)}>Edit</button>
        </div>
      )}
    </div>
  )
}

function HealthPanel({ health, workspace, hasHelpDir, onScan, scanning, onSaveWorkspace }) {
  const { summary = {}, by_persona = {}, quality = {}, last_scan_at } = health
  const hasQuality = quality.faithfulness != null

  return (
    <div className="ld-health">
      <WorkspaceEditor workspace={workspace} hasHelpDir={hasHelpDir} onSave={onSaveWorkspace} />

      <div className="ld-panel-toolbar">
        <span className="ld-panel-title">Health Overview</span>
        <div className="ld-toolbar-actions">
          {last_scan_at && (
            <span className="ld-dim ld-scan-time">
              Last scan: {new Date(last_scan_at).toLocaleTimeString()}
            </span>
          )}
          <button className="primary" onClick={onScan} disabled={scanning}>
            {scanning ? 'Scanning…' : 'Scan Now'}
          </button>
        </div>
      </div>

      <div className="ld-stat-row">
        <div className="ld-stat-card">
          <div className="ld-stat-value">{summary.total ?? 0}</div>
          <div className="ld-stat-label">Total Docs</div>
        </div>
        <div className="ld-stat-card ld-stat-ok">
          <div className="ld-stat-value">{summary.current ?? 0}</div>
          <div className="ld-stat-label">Current</div>
        </div>
        <div className="ld-stat-card ld-stat-warn">
          <div className="ld-stat-value">{summary.stale ?? 0}</div>
          <div className="ld-stat-label">Stale</div>
        </div>
        <div className="ld-stat-card ld-stat-danger">
          <div className="ld-stat-value">{summary.missing ?? 0}</div>
          <div className="ld-stat-label">Missing</div>
        </div>
      </div>

      <h3 className="ld-section-heading">By Persona</h3>
      <div className="ld-persona-row">
        {['end_user', 'developer', 'support'].map(p => {
          const d = by_persona[p] ?? {}
          return (
            <div key={p} className="ld-persona-card">
              <div className="ld-persona-name">{personaLabel(p)}</div>
              <div className="ld-persona-stats">
                <span className="ld-ok">{d.current ?? 0} current</span>
                <span className="ld-warn">{d.stale ?? 0} stale</span>
                <span className="ld-danger">{d.missing ?? 0} missing</span>
              </div>
            </div>
          )
        })}
      </div>

      {hasQuality && (
        <>
          <h3 className="ld-section-heading">RAG Quality Gates</h3>
          <div className="ld-quality-section">
            <QualityBar label="Faithfulness (End User)" value={quality.faithfulness} gate={0.95} />
            <QualityBar label="Strict Accuracy (Developer)" value={quality.strict_accuracy} gate={0.85} />
          </div>
          {quality.last_run_at && (
            <p className="ld-dim" style={{ fontSize: '0.72rem', marginTop: '0.4rem' }}>
              Eval: {new Date(quality.last_run_at).toLocaleString()}
            </p>
          )}
        </>
      )}

      {!hasQuality && (
        <p className="ld-empty" style={{ marginTop: '1.5rem' }}>
          No quality scores yet. Run <code>make eval-smoke</code> to populate.
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Doc registry panel
// ---------------------------------------------------------------------------

function DocRegistryPanel({ docs, onRegenerate, profile }) {
  const [personaFilter, setPersonaFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const personaOptions =
    profile === 'author'
      ? ['all', 'end_user', 'developer', 'support']
      : ['all', profile]

  const filtered = docs.filter(d => {
    const pOk = personaFilter === 'all' || d.persona === personaFilter
    const sOk = statusFilter === 'all' || d.status === statusFilter
    return pOk && sOk
  })

  return (
    <div className="ld-registry">
      <div className="ld-panel-toolbar">
        <span className="ld-panel-title">Documents</span>
        <div className="ld-toolbar-actions">
          <select
            className="ld-select"
            value={personaFilter}
            onChange={e => setPersonaFilter(e.target.value)}
          >
            {personaOptions.map(p => (
              <option key={p} value={p}>
                {p === 'all' ? 'All personas' : personaLabel(p)}
              </option>
            ))}
          </select>
          <select
            className="ld-select"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="current">Current</option>
            <option value="stale">Stale</option>
            <option value="missing">Missing</option>
          </select>
          <span className="ld-dim" style={{ fontSize: '0.78rem' }}>{filtered.length} docs</span>
        </div>
      </div>

      <div className="ld-table-wrap">
        {filtered.length === 0 ? (
          <p className="ld-empty">No documents match the current filters.</p>
        ) : (
          <table className="ld-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Depth</th>
                <th>Persona</th>
                <th>Status</th>
                <th>Reason</th>
                <th>Modified</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => (
                <tr key={doc.id}>
                  <td className="ld-mono">{doc.feature}</td>
                  <td className="ld-mono">{doc.depth}</td>
                  <td>{personaLabel(doc.persona)}</td>
                  <td><StatusBadge status={doc.status} /></td>
                  <td className="ld-dim ld-reason">
                    {doc.reason || '—'}
                  </td>
                  <td className="ld-dim">
                    {doc.last_modified
                      ? new Date(doc.last_modified).toLocaleDateString()
                      : '—'}
                  </td>
                  <td>
                    {doc.status !== 'current' && (
                      <button className="ghost" onClick={() => onRegenerate(doc.id)}>
                        Regenerate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Review queue panel
// ---------------------------------------------------------------------------

function QueueItem({ item, onApprove, onRevert }) {
  return (
    <div className={`ld-queue-item${item.reviewed ? ' ld-queue-reviewed' : ''}`}>
      <div className="ld-queue-header">
        <span className="ld-mono">{item.doc_id}</span>
        <span className="ld-dim">{personaLabel(item.persona)}</span>
        <TriggerBadge trigger={item.trigger} />
        <span className="ld-dim" style={{ fontSize: '0.72rem' }}>
          {new Date(item.auto_applied_at).toLocaleString()}
        </span>
      </div>
      {item.diff_summary && (
        <pre className="ld-diff">{item.diff_summary}</pre>
      )}
      {!item.reviewed && (
        <div className="ld-queue-actions">
          <button className="primary" onClick={() => onApprove(item.id)}>Approve</button>
          <button className="cancel" onClick={() => onRevert(item.id)}>Revert</button>
        </div>
      )}
      {item.reviewed && (
        <span className="ld-reviewed-label">✓ Reviewed</span>
      )}
    </div>
  )
}

function ReviewQueuePanel({ queue, onApprove, onRevert, profile }) {
  const visible = profile === 'author' ? queue : queue.filter(i => i.persona === profile)
  const pending = visible.filter(i => !i.reviewed)
  const done = visible.filter(i => i.reviewed)

  return (
    <div className="ld-queue">
      <div className="ld-panel-toolbar">
        <span className="ld-panel-title">Review Queue</span>
        <span className="ld-dim" style={{ fontSize: '0.78rem' }}>
          {pending.length} pending · {done.length} reviewed
        </span>
      </div>

      {pending.length === 0 && (
        <p className="ld-empty">No items pending review.</p>
      )}
      {pending.map(item => (
        <QueueItem key={item.id} item={item} onApprove={onApprove} onRevert={onRevert} />
      ))}

      {done.length > 0 && (
        <>
          <h3 className="ld-section-heading" style={{ marginTop: '1.5rem' }}>
            Reviewed
          </h3>
          {done.map(item => (
            <QueueItem key={item.id} item={item} onApprove={onApprove} onRevert={onRevert} />
          ))}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------

export default function LivingDocs({ profile }) {
  const [tab, setTab] = useState('health')
  const [health, setHealth] = useState({})
  const [docs, setDocs] = useState([])
  const [queue, setQueue] = useState([])
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const [hasHelpDir, setHasHelpDir] = useState(false)

  const fetchConfig = useCallback(async () => {
    try {
      const c = await api('/api/living-docs/config')
      setWorkspace(c.workspace)
      setHasHelpDir(c.has_help_dir)
    } catch { /* quiet */ }
  }, [])

  const fetchAll = useCallback(async (signal = undefined) => {
    try {
      const opts = signal ? { signal } : {}
      const [h, d, q] = await Promise.all([
        api('/api/living-docs/health', opts),
        api('/api/living-docs/docs', opts),
        api('/api/living-docs/queue', opts),
      ])
      if (signal?.aborted) return
      setHealth(h)
      setDocs(d.docs ?? [])
      setQueue(q.queue ?? [])
      setScanning(h.scanning ?? false)
      if (h.workspace) setWorkspace(h.workspace)
    } catch (e) {
      if (e.name === 'AbortError') return
      setError(e.message)
    }
  }, [])

  useEffect(() => { fetchConfig(); fetchAll() }, [fetchConfig, fetchAll])

  useEffect(() => {
    const controller = new AbortController()
    const tick = () => { if (!document.hidden) fetchAll(controller.signal) }
    const id = setInterval(tick, 3000)
    return () => { clearInterval(id); controller.abort() }
  }, [fetchAll])

  const handleSaveWorkspace = useCallback(async (newPath) => {
    const c = await api('/api/living-docs/config', {
      method: 'PUT',
      body: JSON.stringify({ workspace: newPath }),
    })
    setWorkspace(c.workspace)
    setHasHelpDir(c.has_help_dir)
    await fetchAll()
  }, [fetchAll])

  const handleScan = useCallback(async () => {
    setScanning(true)
    try {
      await api('/api/living-docs/scan', {
        method: 'POST',
        body: JSON.stringify({ trigger: 'manual' }),
      })
    } catch (e) {
      setError(e.message)
      setScanning(false)
    }
  }, [])

  const handleRegenerate = useCallback(async (docId) => {
    try {
      await api(`/api/living-docs/docs/${docId}/regenerate`, {
        method: 'POST',
        body: '{}',
      })
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const handleApprove = useCallback(async (itemId) => {
    try {
      await api(`/api/living-docs/queue/${itemId}/approve`, {
        method: 'POST',
        body: '{}',
      })
      await fetchAll()
    } catch (e) {
      setError(e.message)
    }
  }, [fetchAll])

  const handleRevert = useCallback(async (itemId) => {
    try {
      await api(`/api/living-docs/queue/${itemId}/revert`, {
        method: 'POST',
        body: '{}',
      })
      await fetchAll()
    } catch (e) {
      setError(e.message)
    }
  }, [fetchAll])

  const pendingCount = queue.filter(i => !i.reviewed).length

  return (
    <div className="ld-root">
      <div className="ld-tabs">
        <button
          className={`ld-tab${tab === 'health' ? ' active' : ''}`}
          onClick={() => setTab('health')}
        >
          Health
        </button>
        <button
          className={`ld-tab${tab === 'docs' ? ' active' : ''}`}
          onClick={() => setTab('docs')}
        >
          Documents
          {docs.length > 0 && (
            <span className="ld-tab-pill">{docs.length}</span>
          )}
        </button>
        <button
          className={`ld-tab${tab === 'queue' ? ' active' : ''}`}
          onClick={() => setTab('queue')}
        >
          Review Queue
          {pendingCount > 0 && (
            <span className="ld-tab-pill ld-tab-pill-warn">{pendingCount}</span>
          )}
        </button>
      </div>

      {error && (
        <div className="ld-error-banner" onClick={() => setError(null)}>
          {error} <span className="ld-dim">(click to dismiss)</span>
        </div>
      )}

      <div className="ld-tab-content">
        {tab === 'health' && (
          <HealthPanel
            health={health}
            workspace={workspace}
            hasHelpDir={hasHelpDir}
            onScan={handleScan}
            scanning={scanning}
            onSaveWorkspace={handleSaveWorkspace}
          />
        )}
        {tab === 'docs' && (
          <DocRegistryPanel docs={docs} onRegenerate={handleRegenerate} profile={profile} />
        )}
        {tab === 'queue' && (
          <ReviewQueuePanel
            queue={queue}
            onApprove={handleApprove}
            onRevert={handleRevert}
            profile={profile}
          />
        )}
      </div>
    </div>
  )
}
