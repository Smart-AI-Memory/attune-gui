import { useState, useEffect } from 'react'
import { api } from '../api'

function buildDefaults(schema) {
  const props = schema?.properties || {}
  const defaults = {}
  for (const [key, prop] of Object.entries(props)) {
    if (prop.default !== undefined) defaults[key] = prop.default
    else if (prop.type === 'boolean') defaults[key] = false
    else defaults[key] = ''
  }
  return defaults
}

export default function FormPanel({ cmd, onJobStarted, bootError }) {
  const [values, setValues] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  useEffect(() => {
    if (cmd) setValues(buildDefaults(cmd.args_schema))
    setSubmitError(null)
  }, [cmd?.name])  // eslint-disable-line react-hooks/exhaustive-deps

  if (bootError) {
    return (
      <section className="col">
        <div className="col-header">Arguments</div>
        <div className="col-body"><div className="form-empty">Error: {bootError}</div></div>
      </section>
    )
  }
  if (!cmd) {
    return (
      <section className="col">
        <div className="col-header">Arguments</div>
        <div className="col-body"><div className="form-empty">Select a command.</div></div>
      </section>
    )
  }

  const schema = cmd.args_schema || {}
  const props = schema.properties || {}
  const required = new Set(schema.required || [])

  function set(key, val) {
    setValues(prev => ({ ...prev, [key]: val }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    const args = {}
    for (const [key, prop] of Object.entries(props)) {
      const val = values[key]
      if (prop.type === 'boolean') { args[key] = !!val }
      else if (prop.type === 'integer') { if (val !== '') args[key] = parseInt(val, 10) }
      else if (prop.type === 'number') { if (val !== '') args[key] = parseFloat(val) }
      else { if (val !== '') args[key] = val }
    }
    try {
      const job = await api('/api/jobs', {
        method: 'POST',
        body: JSON.stringify({ name: cmd.name, args }),
      })
      onJobStarted(job)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const fields = Object.entries(props).map(([key, prop]) => {
    const label = prop.title || key
    const isReq = required.has(key)
    const desc = prop.description || ''
    const val = values[key] ?? ''

    if (prop.type === 'boolean') {
      return (
        <div key={key} className="field field-checkbox">
          <input type="checkbox" id={`f_${key}`} checked={!!val} onChange={e => set(key, e.target.checked)} />
          <label htmlFor={`f_${key}`}>{label}</label>
          {desc && <div className="field-desc">{desc}</div>}
        </div>
      )
    }
    if (prop.type === 'integer' || prop.type === 'number') {
      return (
        <div key={key} className="field">
          <label htmlFor={`f_${key}`}>{label}{isReq ? ' *' : ''}</label>
          <input
            type="number" id={`f_${key}`} value={val}
            min={prop.minimum} max={prop.maximum}
            onChange={e => set(key, e.target.value)}
          />
          {desc && <div className="field-desc">{desc}</div>}
        </div>
      )
    }
    if (prop['ui:widget'] === 'textarea') {
      return (
        <div key={key} className="field">
          <label htmlFor={`f_${key}`}>{label}{isReq ? ' *' : ''}</label>
          <textarea id={`f_${key}`} value={val} onChange={e => set(key, e.target.value)} />
          {desc && <div className="field-desc">{desc}</div>}
        </div>
      )
    }
    return (
      <div key={key} className="field">
        <label htmlFor={`f_${key}`}>{label}{isReq ? ' *' : ''}</label>
        <input
          type="text" id={`f_${key}`} value={val} autoComplete="off"
          onChange={e => set(key, e.target.value)}
        />
        {desc && <div className="field-desc">{desc}</div>}
      </div>
    )
  })

  return (
    <section className="col">
      <div className="col-header">Arguments</div>
      <div className="col-body">
        <div className="form-wrap">
          <h2 className="form-title">{cmd.title}</h2>
          <div className="form-desc">{cmd.description}</div>
          <form onSubmit={handleSubmit}>
            {fields}
            {submitError && <div className="form-error">{submitError}</div>}
            <button type="submit" className="primary" disabled={submitting}>
              {submitting ? 'Starting…' : 'Run'}
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
