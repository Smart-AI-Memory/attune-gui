import { useState, useEffect, useCallback } from 'react'
import { api, setSessionToken } from './api'
import TopBar from './components/TopBar'
import CommandsPanel from './components/CommandsPanel'
import FormPanel from './components/FormPanel'
import JobsPanel from './components/JobsPanel'
import LivingDocs from './components/LivingDocs'

export default function App() {
  const [healthy, setHealthy] = useState(null)
  const [version, setVersion] = useState('')
  const [commands, setCommands] = useState([])
  const [selected, setSelected] = useState(null)
  const [jobs, setJobs] = useState([])
  const [expandedIds, setExpandedIds] = useState(new Set())
  const [bootError, setBootError] = useState(null)
  const [profile, setProfile] = useState('developer')
  const [mode, setMode] = useState('commands')

  const fetchJobs = useCallback(async () => {
    try {
      const { jobs: js } = await api('/api/jobs')
      setJobs(js)
    } catch { /* quiet — will retry */ }
  }, [])

  const fetchCommands = useCallback(async (activeProfile) => {
    const { commands: cs } = await api(`/api/commands?profile=${activeProfile}`)
    setCommands(cs)
    setSelected(prev => cs.find(c => c.name === prev) ? prev : (cs[0]?.name ?? null))
  }, [])

  useEffect(() => {
    async function boot() {
      try {
        const t = await api('/api/session/token')
        setSessionToken(t.token)
      } catch (e) {
        setHealthy(false)
        setBootError(e.message)
        return
      }
      try {
        const h = await api('/api/health')
        setVersion(`sidecar ${h.version} · py ${h.python}`)
        setHealthy(true)
      } catch {
        setHealthy(false)
      }
      try {
        const { profile: p } = await api('/api/profile')
        setProfile(p)
        await fetchCommands(p)
      } catch (e) {
        setBootError(e.message)
      }
      await fetchJobs()
    }
    boot()
  }, [fetchJobs, fetchCommands])

  useEffect(() => {
    const id = setInterval(fetchJobs, 1200)
    return () => clearInterval(id)
  }, [fetchJobs])

  const handleProfileChange = useCallback(async (newProfile) => {
    try {
      await api('/api/profile', { method: 'PUT', body: JSON.stringify({ profile: newProfile }) })
      setProfile(newProfile)
      await fetchCommands(newProfile)
    } catch { /* ignore */ }
  }, [fetchCommands])

  const selectedCmd = commands.find(c => c.name === selected) ?? null

  const handleJobStarted = useCallback((job) => {
    setJobs(prev => [job, ...prev.filter(j => j.id !== job.id)])
    setExpandedIds(prev => new Set([...prev, job.id]))
  }, [])

  const toggleExpanded = useCallback((id) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const clearDone = useCallback(() => {
    const done = new Set(['completed', 'errored', 'cancelled'])
    setJobs(prev => {
      const removed = prev.filter(j => done.has(j.status)).map(j => j.id)
      setExpandedIds(ids => {
        const next = new Set(ids)
        removed.forEach(id => next.delete(id))
        return next
      })
      return prev.filter(j => !done.has(j.status))
    })
  }, [])

  return (
    <div className="app">
      <TopBar
        healthy={healthy}
        version={version}
        profile={profile}
        onProfileChange={handleProfileChange}
        mode={mode}
        onModeChange={setMode}
      />
      {mode === 'commands' ? (
        <main className="cols">
          <CommandsPanel commands={commands} selected={selected} onSelect={setSelected} />
          <FormPanel cmd={selectedCmd} onJobStarted={handleJobStarted} bootError={bootError} />
          <JobsPanel
            jobs={jobs}
            expandedIds={expandedIds}
            onToggle={toggleExpanded}
            onClearDone={clearDone}
          />
        </main>
      ) : (
        <main className="ld-main">
          <LivingDocs profile={profile} />
        </main>
      )}
    </div>
  )
}
