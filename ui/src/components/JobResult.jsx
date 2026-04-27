export default function JobResult({ job }) {
  const r = job.result

  if (job.name === 'rag.query' && r.hits) {
    return (
      <div>
        <div style={{ fontSize: '0.75rem', color: 'var(--fg-dim)', marginBottom: '0.3rem' }}>
          {r.total_hits} hit(s)
        </div>
        <ul className="hits-list">
          {r.hits.map((h, i) => (
            <li key={i} className="hit">
              <div className="hit-path">{h.path}</div>
              <div className="hit-meta">score {h.score} · {h.category}</div>
              <div className="hit-excerpt">{(h.excerpt || '').slice(0, 200)}</div>
            </li>
          ))}
        </ul>
        {r.augmented_prompt && (
          <details className="augmented">
            <summary>Augmented prompt</summary>
            <pre>{r.augmented_prompt}</pre>
          </details>
        )}
      </div>
    )
  }

  if (job.name === 'author.lookup' && r.content) {
    return (
      <div>
        <div style={{ fontSize: '0.72rem', color: 'var(--fg-dim)', marginBottom: '0.3rem' }}>
          {r.feature} · {r.depth}
        </div>
        <div className="lookup-content">{r.content}</div>
      </div>
    )
  }

  if (job.name === 'author.status' && r.report) {
    return (
      <div>
        <div style={{ fontSize: '0.72rem', color: 'var(--fg-dim)', marginBottom: '0.3rem' }}>
          {r.stale} stale / {r.total} total
        </div>
        <div className="lookup-content">{r.report}</div>
      </div>
    )
  }

  if (job.name === 'help.lookup' && r.content) {
    return (
      <div>
        <div style={{ fontSize: '0.72rem', color: 'var(--fg-dim)', marginBottom: '0.3rem' }}>
          {r.topic} · {r.depth} · {r.total_topics} topics available
        </div>
        <div className="lookup-content">{r.content}</div>
      </div>
    )
  }

  if (job.name === 'help.search' && r.results) {
    return (
      <div>
        <div style={{ fontSize: '0.72rem', color: 'var(--fg-dim)', marginBottom: '0.4rem' }}>
          {r.count} result(s) for &ldquo;{r.query}&rdquo;
        </div>
        <ul className="hits-list">
          {r.results.map((slug, i) => (
            <li key={i} className="hit">
              <div className="hit-path">{slug}</div>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  if (job.name === 'help.list' && r.topics) {
    return (
      <div>
        <div style={{ fontSize: '0.72rem', color: 'var(--fg-dim)', marginBottom: '0.4rem' }}>
          {r.count} topic(s){r.type_filter ? ` · type: ${r.type_filter}` : ''}
        </div>
        <div className="job-result">{r.topics.join('\n')}</div>
      </div>
    )
  }

  return <div className="job-result">{JSON.stringify(r, null, 2)}</div>
}
