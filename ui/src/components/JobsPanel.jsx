import JobCard from './JobCard'

export default function JobsPanel({ jobs, expandedIds, onToggle, onClearDone }) {
  return (
    <section className="col" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="col-header">Jobs</div>
      <div className="jobs-toolbar">
        <button className="ghost" onClick={onClearDone}>Clear done</button>
      </div>
      <div className="col-body">
        {jobs.length === 0
          ? <div className="jobs-empty">No jobs yet. Run a command to see it here.</div>
          : jobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                expanded={expandedIds.has(job.id)}
                onToggle={() => onToggle(job.id)}
              />
            ))
        }
      </div>
    </section>
  )
}
