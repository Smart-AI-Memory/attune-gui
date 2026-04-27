export default function TopBar({ healthy, version, profile, onProfileChange, mode, onModeChange }) {
  const cls = healthy === null ? '' : healthy ? 'healthy' : 'unhealthy'
  return (
    <header className={`topbar ${cls}`}>
      <h1><span className="status-dot" />attune-gui</h1>

      <div className="topbar-center">
        <div className="mode-switcher">
          <button
            className={`mode-btn${mode === 'commands' ? ' active' : ''}`}
            onClick={() => onModeChange('commands')}
          >
            Commands
          </button>
          <button
            className={`mode-btn${mode === 'living-docs' ? ' active' : ''}`}
            onClick={() => onModeChange('living-docs')}
          >
            Living Docs
          </button>
        </div>
      </div>

      <div className="topbar-right">
        <div className="profile-switcher">
          {['developer', 'author', 'support'].map(p => (
            <button
              key={p}
              className={`profile-btn${profile === p ? ' active' : ''}`}
              onClick={() => onProfileChange(p)}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <span className="version">{version || '—'}</span>
      </div>
    </header>
  )
}
