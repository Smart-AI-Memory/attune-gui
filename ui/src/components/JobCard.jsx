import { api } from '../api'
import JobResult from './JobResult'

function formatRelTime(iso) {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 1000) return 'just now'
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`
  return new Date(iso).toLocaleTimeString()
}

function formatDuration(start, end) {
  if (!start) return ''
  const ms = (end ? new Date(end).getTime() : Date.now()) - new Date(start).getTime()
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function JobCard({ job, expanded, onToggle }) {
  const canCancel = job.status === 'running' || job.status === 'pending'
  const duration = formatDuration(job.started_at, job.finished_at)

  async function cancel(e) {
    e.stopPropagation()
    try {
      await api(`/api/jobs/${job.id}`, { method: 'DELETE' })
    } catch (err) {
      alert(`Cancel failed: ${err.message}`)
    }
  }

  return (
    <div className={`job${expanded ? ' expanded' : ''}`}>
      <div className="job-header" onClick={onToggle}>
        <span>
          <span className="job-name">{job.name}</span>
          <span className="job-meta">
            {' · '}{formatRelTime(job.created_at)}{duration ? ` · ${duration}` : ''}
          </span>
        </span>
        <span>
          <span className={`job-status status-${job.status}`}>{job.status}</span>
          {canCancel && (
            <button className="cancel" onClick={cancel} style={{ marginLeft: '0.4rem' }}>
              Cancel
            </button>
          )}
        </span>
      </div>
      <div className="job-body">
        {Object.keys(job.args || {}).length > 0 && (
          <>
            <div className="job-section-label">Args</div>
            <div className="job-result">{JSON.stringify(job.args, null, 2)}</div>
          </>
        )}
        {job.output_lines?.length > 0 && (
          <>
            <div className="job-section-label">Log</div>
            <pre className="job-logs">{job.output_lines.join('\n')}</pre>
          </>
        )}
        {job.error && (
          <>
            <div className="job-section-label">Error</div>
            <div className="job-error">{job.error}</div>
          </>
        )}
        {job.result && (
          <>
            <div className="job-section-label">Result</div>
            <JobResult job={job} />
          </>
        )}
      </div>
    </div>
  )
}
