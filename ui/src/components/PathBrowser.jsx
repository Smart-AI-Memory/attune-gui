import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

export default function PathBrowser({ initialPath, onSelect, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (path) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api(`/api/fs/browse?path=${encodeURIComponent(path)}`)
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(initialPath || '~')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const breadcrumbs = data ? buildCrumbs(data.path) : []

  function handleKey(e) {
    if (e.key === 'Escape') onClose()
  }

  return (
    <div className="pb-backdrop" onClick={onClose} onKeyDown={handleKey}>
      <div className="pb-modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="pb-header">
          <span className="pb-title">Select directory</span>
          <button className="pb-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="pb-crumbs">
          {breadcrumbs.map((crumb, i) => (
            <span key={crumb.path} className="pb-crumb">
              {i > 0 && <span className="pb-sep">/</span>}
              <button className="pb-crumb-btn" onClick={() => load(crumb.path)}>
                {crumb.label || '/'}
              </button>
            </span>
          ))}
        </div>

        <div className="pb-list">
          {loading && <div className="pb-status">Loading…</div>}
          {error && <div className="pb-status pb-error">{error}</div>}
          {!loading && !error && data && (
            <>
              {data.parent && (
                <button className="pb-entry pb-up" onClick={() => load(data.parent)}>
                  ↑ ..
                </button>
              )}
              {data.entries.length === 0 && (
                <div className="pb-status">No subdirectories</div>
              )}
              {data.entries.map(entry => (
                <button
                  key={entry.path}
                  className="pb-entry"
                  onClick={() => load(entry.path)}
                >
                  <span className="pb-icon">📁</span>
                  <span className="pb-entry-name">{entry.name}</span>
                </button>
              ))}
            </>
          )}
        </div>

        <div className="pb-footer">
          {data && (
            <span className="pb-current-path">{data.path}</span>
          )}
          <div className="pb-actions">
            <button className="ghost" onClick={onClose}>Cancel</button>
            <button
              className="primary"
              disabled={!data}
              onClick={() => { if (data) onSelect(data.path) }}
            >
              Select
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function buildCrumbs(absPath) {
  const parts = absPath.split('/').filter(Boolean)
  const crumbs = [{ label: '', path: '/' }]
  for (let i = 0; i < parts.length; i++) {
    crumbs.push({
      label: parts[i],
      path: '/' + parts.slice(0, i + 1).join('/'),
    })
  }
  return crumbs
}
