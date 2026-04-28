const DOMAIN_LABELS = {
  rag: 'Search & Query',
  author: 'Author Docs',
  help: 'Help Lookup',
}

export default function CommandsPanel({ commands, selected, onSelect }) {
  const byDomain = {}
  for (const c of commands) {
    ;(byDomain[c.domain] ??= []).push(c)
  }

  return (
    <aside className="col">
      <div className="col-header">Commands</div>
      <div className="col-body">
        {Object.entries(byDomain).map(([domain, cmds]) => (
          <div key={domain} className="cmd-domain">
            <div className="cmd-domain-label">{DOMAIN_LABELS[domain] ?? domain}</div>
            {cmds.map(c => (
              <button
                key={c.name}
                className={`cmd-item${selected === c.name ? ' active' : ''}`}
                onClick={() => onSelect(c.name)}
              >
                <div className="cmd-item-title">{c.title}</div>
                <div className="cmd-item-desc">{c.description}</div>
              </button>
            ))}
          </div>
        ))}
      </div>
    </aside>
  )
}
