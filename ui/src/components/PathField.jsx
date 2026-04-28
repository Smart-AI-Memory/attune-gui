import { useState } from 'react'
import PathBrowser from './PathBrowser'

function isValidPath(val) {
  return val === '' || val.startsWith('/') || val.startsWith('~')
}

export default function PathField({ id, value, label, isRequired, description, onChange }) {
  const [browserOpen, setBrowserOpen] = useState(false)
  const invalid = value !== '' && !isValidPath(value)

  return (
    <div className="field">
      <label htmlFor={id}>{label}{isRequired ? ' *' : ''}</label>
      <div className="path-field-row">
        <input
          type="text"
          id={id}
          value={value}
          autoComplete="off"
          className={invalid ? 'path-invalid' : ''}
          placeholder="/absolute/path or ~/relative-to-home"
          onChange={e => onChange(e.target.value)}
        />
        <button
          type="button"
          className="ghost path-browse-btn"
          onClick={() => setBrowserOpen(true)}
        >
          Browse…
        </button>
      </div>
      {invalid && (
        <div className="field-error">Must start with / or ~ (got a relative path)</div>
      )}
      {description && <div className="field-desc">{description}</div>}
      {browserOpen && (
        <PathBrowser
          initialPath={isValidPath(value) && value ? value : '~'}
          onSelect={path => { onChange(path); setBrowserOpen(false) }}
          onClose={() => setBrowserOpen(false)}
        />
      )}
    </div>
  )
}
