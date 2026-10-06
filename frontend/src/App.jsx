import { useState, useEffect, useMemo, useRef } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000/eligibility'
const UNIVERSITIES_URL = 'http://127.0.0.1:8000/universities'

const STATUS_ICON = { met: '✅', not_met: '❌', needs_review: '⚠️', not_applicable: '➖', informational: 'ℹ️️' }
const MAX_COMPARE = 3
const MAX_COUNTRIES = 2
const KNOWN_REQUIREMENTS = ['cgpa', 'english_test', 'gre', 'gate', 'german_test']

function emptyProfile() {
  return {
    flow: 'early_planner', citizenship: '', undergrad_country: '', cgpa: '', gre_quant_scaled: '', gre_quant_percentile: '',
    gre_verbal_percentile: '', gre_awa: '', gate_score_reported: false, english_test_type: '', english_score: '',
    toefl_test_date_on_or_after_2026_01_21: false, undergrad_institution_english_medium: null, german_level: '',
    is_eu_eea_citizen: false, is_bildungsinlaender: false,
  }
}

function toRequestBody(profile, dynamicProfile) {
  const numOrNull = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  const strOrNull = (v) => (v === '' ? null : v)
  
  const baseProfile = {
    flow: profile.flow, citizenship: strOrNull(profile.citizenship), undergrad_country: strOrNull(profile.undergrad_country),
    cgpa: numOrNull(profile.cgpa), gre_quant_scaled: numOrNull(profile.gre_quant_scaled), gre_quant_percentile: numOrNull(profile.gre_quant_percentile),
    gre_verbal_percentile: numOrNull(profile.gre_verbal_percentile), gre_awa: numOrNull(profile.gre_awa), gate_score_reported: !!profile.gate_score_reported,
    english_test_type: strOrNull(profile.english_test_type), english_score: numOrNull(profile.english_score),
    toefl_test_date_on_or_after_2026_01_21: !!profile.toefl_test_date_on_or_after_2026_01_21, undergrad_institution_english_medium: profile.undergrad_institution_english_medium,
    german_level: strOrNull(profile.german_level), is_eu_eea_citizen: !!profile.is_eu_eea_citizen, is_bildungsinlaender: !!profile.is_bildungsinlaender,
  }
  return { ...baseProfile, ...dynamicProfile }
}

function deriveCountry(universityName) {
  if (!universityName) return 'Unknown'
  const lower = universityName.toLowerCase()
  if (lower.includes('tum') || lower.includes('munich') || lower.includes('rwth') || lower.includes('aachen')) return 'Germany'
  if (lower.includes('kaist') || lower.includes('seoul')) return 'South Korea'
  return 'Unknown'
}

function buildEligibilityUrl({ selectedUniversities, selectedCountries, countryMode, programMode, appMode, availableUniversities }) {
  if (appMode === 'check') {
    if (countryMode === 'all' && programMode === 'all') return API_URL
    const params = new URLSearchParams()
    let targetUnis = []

    if (programMode === 'specific' && selectedUniversities.length > 0) {
      targetUnis = selectedUniversities
    } else if (countryMode === 'specific') {
      targetUnis = availableUniversities
        .filter((u) => selectedCountries.includes(u.country || deriveCountry(u.university)))
        .map((u) => u.university)
    }

    const unique = [...new Set(targetUnis)]
    if (unique.length === 0) return API_URL
    unique.forEach((u) => params.append('universities', u))
    return `${API_URL}?${params.toString()}`
  }

  if (appMode === 'compare') {
    if (!selectedUniversities || selectedUniversities.length === 0) return API_URL
    const params = new URLSearchParams()
    selectedUniversities.forEach((u) => params.append('universities', u))
    return `${API_URL}?${params.toString()}`
  }
  return API_URL
}

function TriStateSelect({ label, value, onChange }) {
  return (
    <label className="field">
      {label}
      <select value={value === null ? 'unknown' : value ? 'yes' : 'no'} onChange={(e) => { const v = e.target.value; onChange(v === 'unknown' ? null : v === 'yes') }}>
        <option value="unknown">Not sure / N/A</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </label>
  )
}

function ResultCard({ result }) {
  const overallColor = { eligible: '#16a34a', not_eligible: '#dc2626', needs_review: '#d97706' }[result.overall_status] || '#555'
  return (
    <div className="result-card">
      <div className="result-header">
        <div>
          <h3 style={{ margin: 0 }}>{result.university}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{result.program} — {result.academic_year === 'unknown_year' ? 'Year Unspecified' : result.academic_year}</p>
        </div>
        <span className="overall-badge" style={{ backgroundColor: overallColor }}>{result.overall_status.replace('_', ' ')}</span>
      </div>
      {result.error && <p style={{ color: 'var(--danger)', marginBottom: '1rem' }}>Error: {result.error}</p>}
      <ul className="judgment-list">
        {result.judgments.map((j, i) => (
          <li key={i} className="judgment">
            <span>{STATUS_ICON[j.status] || '•'}</span>
            <div>
              <strong>{j.requirement_type.replace(/_/g, ' ')}</strong>
              <p>{j.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ComparisonTable({ results }) {
  const requirementTypes = []
  results.forEach((r) => { r.judgments.forEach((j) => { if (!requirementTypes.includes(j.requirement_type)) requirementTypes.push(j.requirement_type) }) })
  
  return (
    <div className="comparison-table-wrapper">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Requirement</th>
            {results.map((r) => (
              <th key={r.university + r.program}>{r.university}<br /><span style={{ color: 'var(--text-muted)', fontWeight: 'normal' }}>{r.program}</span></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requirementTypes.map((type) => (
            <tr key={type}>
              <td style={{ fontWeight: 500, textTransform: 'capitalize' }}>{type.replace(/_/g, ' ')}</td>
              {results.map((r) => {
                const judgment = r.judgments.find((j) => j.requirement_type === type)
                if (!judgment) return <td key={r.university + r.program} style={{ textAlign: 'center' }}>—</td>
                return (
                  <td key={r.university + r.program}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <span>{STATUS_ICON[judgment.status] || '•'}</span>
                      <span>{judgment.detail}</span>
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatLabel(str) { return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ') }

function RagChatView() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Hi! Ask me anything about university requirements, deadlines, or test scores. I will cross-reference official pages and warn you if Yocket or other sites are wrong.' }])
  const [loading, setLoading] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    const userQ = query
    setQuery('')
    setMessages(prev => [...prev, { role: 'user', content: userQ }])
    setLoading(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: userQ }) })
      if (!res.ok) throw new Error(`API returned ${res.status}`)
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <span style={{ fontSize: '1.25rem' }}>🧠</span> Outbound Intelligence
      </div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message-wrapper ${msg.role}`}>
            <div className="chat-bubble">{msg.content}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="chat-sources">
                {msg.sources.map((src, idx) => (
                  <a key={idx} href={src} target="_blank" rel="noreferrer">Source {idx + 1}</a>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message-wrapper assistant"><div className="chat-bubble" style={{ opacity: 0.7 }}>Thinking...</div></div>}
        <div ref={endRef} />
      </div>
      <form onSubmit={handleSend} className="chat-input-form">
        <input type="text" className="chat-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask about TUM deadlines or Yocket accuracy..." />
        <button type="submit" className="chat-send-btn" disabled={loading}>Send</button>
      </form>
    </div>
  )
}

export default function App() {
  const [appMode, setAppMode] = useState('check') // 'check' | 'compare' | 'chat'
  const [profile, setProfile] = useState(emptyProfile())
  const [dynamicProfile, setDynamicProfile] = useState({})
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const [countryMode, setCountryMode] = useState('all') 
  const [selectedCountries, setSelectedCountries] = useState([])
  const [programMode, setProgramMode] = useState('all')
  const [selectedUniversities, setSelectedUniversities] = useState([])

  const [availableUniversities, setAvailableUniversities] = useState([])

  useEffect(() => {
    if (availableUniversities.length === 0) {
      fetch(UNIVERSITIES_URL).then((resp) => resp.json()).then((data) => setAvailableUniversities(data)).catch(() => {})
    }
  }, [availableUniversities.length])

  const backendRequiredFields = useMemo(() => {
    const required = new Set()
    if (programMode === 'specific' || appMode === 'compare') {
      selectedUniversities.forEach(uniName => {
        const uniData = availableUniversities.find(u => u.university === uniName)
        if (uniData && Array.isArray(uniData.active_requirements)) uniData.active_requirements.forEach(req => required.add(req))
      })
    }
    return required
  }, [appMode, programMode, selectedUniversities, availableUniversities])

  const unknownRequirements = Array.from(backendRequiredFields).filter(req => !KNOWN_REQUIREMENTS.includes(req))

  function toggleCountry(countryName) {
    setSelectedCountries((prev) => {
      const next = prev.includes(countryName) ? prev.filter((c) => c !== countryName) : prev.length < MAX_COUNTRIES ? [...prev, countryName] : prev
      setSelectedUniversities((currentUnis) => currentUnis.filter((uName) => {
        const uObj = availableUniversities.find((item) => item.university === uName)
        return next.includes(uObj?.country || deriveCountry(uName))
      }))
      return next
    })
  }

  function toggleUniversity(universityName) {
    const maxLimit = appMode === 'compare' ? MAX_COMPARE : null
    setSelectedUniversities((prev) => {
      if (prev.includes(universityName)) return prev.filter((u) => u !== universityName)
      if (maxLimit && prev.length >= maxLimit) return prev
      return [...prev, universityName]
    })
  }

  const set = (key) => (e) => setProfile((p) => ({ ...p, [key]: e && e.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e }))
  const setDynamic = (key) => (e) => setDynamicProfile((p) => ({ ...p, [key]: e.target.value }))

  const filteredUniversities = availableUniversities.filter((u) => countryMode === 'all' || selectedCountries.includes(u.country || deriveCountry(u.university)))
  const isNearTerm = profile.flow === 'near_term'
  const isGermanyInScope = appMode === 'check' 
    ? (countryMode === 'specific' && selectedCountries.includes('Germany')) || (programMode === 'specific' && selectedUniversities.some((u) => deriveCountry(u) === 'Germany'))
    : selectedUniversities.some((u) => deriveCountry(u) === 'Germany')

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true); setError(null); setResults(null)
    try {
      const url = buildEligibilityUrl({ selectedUniversities, selectedCountries, countryMode, programMode, appMode, availableUniversities })
      const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(toRequestBody(profile, dynamicProfile)) })
      if (!resp.ok) throw new Error(`API returned ${resp.status}`)
      setResults(await resp.json())
    } catch (err) { setError(`Couldn't reach API: ${err.message}`) } 
    finally { setLoading(false) }
  }

  const availableCountries = [...new Set(availableUniversities.map((u) => u.country || deriveCountry(u.university)))].sort()

  return (
    <div className="app-container">
      <h1>Outbound</h1>

      <div className="app-mode-tabs">
        <button type="button" className={`tab-btn ${appMode === 'check' ? 'active' : ''}`} onClick={() => { setAppMode('check'); setResults(null); setError(null) }}>Eligibility Engine</button>
        <button type="button" className={`tab-btn ${appMode === 'compare' ? 'active' : ''}`} onClick={() => { setAppMode('compare'); setResults(null); setError(null); setSelectedUniversities(prev => prev.slice(0, MAX_COMPARE)) }}>Compare Programs</button>
        <button type="button" className={`tab-btn chat-tab ${appMode === 'chat' ? 'active' : ''}`} onClick={() => { setAppMode('chat'); setResults(null); setError(null) }}>✨ Smart Assistant</button>
      </div>

      {appMode !== 'chat' && (
        <>
          <form onSubmit={handleSubmit}>
            <div className="section-panel">
              <div className="section-title">Application Timeline</div>
              <div className="radio-group row">
                <label className="checkable"><input type="radio" checked={profile.flow === 'early_planner'} onChange={() => setProfile(p => ({...p, flow: 'early_planner'}))} /> Early planner (CGPA only)</label>
                <label className="checkable"><input type="radio" checked={profile.flow === 'near_term'} onChange={() => setProfile(p => ({...p, flow: 'near_term'}))} /> Near-term (I have my scores)</label>
              </div>
            </div>

            <div className="section-panel">
              <div className="section-title">Basic Profile</div>
              <div className="field-grid">
                <label className="field">Citizenship<input type="text" placeholder="e.g. India" value={profile.citizenship} onChange={set('citizenship')} /></label>
                <label className="field">Undergrad Country<input type="text" placeholder="e.g. India" value={profile.undergrad_country} onChange={set('undergrad_country')} /></label>
                <label className="field">CGPA (10-point scale)<input type="number" step="0.01" value={profile.cgpa} onChange={set('cgpa')} /></label>
              </div>
            </div>

            {isNearTerm && (
              <div className="section-panel">
                <div className="section-title">English Proficiency</div>
                <div className="field-grid">
                  <TriStateSelect label="Was undergrad English-medium?" value={profile.undergrad_institution_english_medium} onChange={(v) => setProfile((p) => ({ ...p, undergrad_institution_english_medium: v }))} />
                  <label className="field">Test Type<select value={profile.english_test_type} onChange={set('english_test_type')}><option value="">Not taken / N/A</option><option value="IELTS">IELTS</option><option value="TOEFL">TOEFL</option><option value="TOEIC">TOEIC</option><option value="TEPS">TEPS</option></select></label>
                  <label className="field">Score<input type="number" step="0.1" value={profile.english_score} onChange={set('english_score')} /></label>
                  {profile.english_test_type === 'TOEFL' && (
                    <label className="checkable" style={{ gridColumn: '1 / -1' }}><input type="checkbox" checked={profile.toefl_test_date_on_or_after_2026_01_21} onChange={set('toefl_test_date_on_or_after_2026_01_21')} /> My TOEFL date was on/after 21 Jan 2026 (new scale)</label>
                  )}
                </div>
              </div>
            )}

            {appMode === 'check' && (
              <div className="section-panel">
                <div className="section-title">Target Countries & Programs</div>
                <div className="radio-group row" style={{ marginBottom: '1.5rem' }}>
                  <label className="checkable"><input type="radio" checked={countryMode === 'all'} onChange={() => { setCountryMode('all'); setSelectedCountries([]) }} /> Anywhere</label>
                  <label className="checkable"><input type="radio" checked={countryMode === 'specific'} onChange={() => setCountryMode('specific')} /> Specific countries</label>
                </div>

                {countryMode === 'specific' && (
                  <div className="checkbox-list" style={{ marginBottom: '2rem', display: 'flex', flexDirection: 'row', gap: '1rem' }}>
                    {availableCountries.map((c) => {
                      const isSelected = selectedCountries.includes(c)
                      const disabled = !isSelected && selectedCountries.length >= MAX_COUNTRIES
                      return (
                        <label key={c} className="checkable" style={{ opacity: disabled ? 0.4 : 1 }}><input type="checkbox" checked={isSelected} disabled={disabled} onChange={() => toggleCountry(c)} /> {c}</label>
                      )
                    })}
                  </div>
                )}

                {(countryMode === 'all' || selectedCountries.length > 0) && (
                  <>
                    <div className="radio-group row" style={{ marginBottom: '1.5rem' }}>
                      <label className="checkable"><input type="radio" checked={programMode === 'all'} onChange={() => { setProgramMode('all'); setSelectedUniversities([]) }} /> All programs</label>
                      <label className="checkable"><input type="radio" checked={programMode === 'specific'} onChange={() => setProgramMode('specific')} /> Specific programs</label>
                    </div>

                    {programMode === 'specific' && (
                      <div className="checkbox-list">
                        {filteredUniversities.map((u) => (
                          <label key={`${u.university}-${u.program}`} className="checkable"><input type="checkbox" checked={selectedUniversities.includes(u.university)} onChange={() => toggleUniversity(u.university)} /> {u.university} — {u.program}</label>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {appMode === 'compare' && (
              <div className="section-panel">
                <div className="section-title">Select Programs to Compare (up to {MAX_COMPARE})</div>
                <div className="checkbox-list">
                  {availableUniversities.map((u) => {
                    const isSelected = selectedUniversities.includes(u.university)
                    const disabled = !isSelected && selectedUniversities.length >= MAX_COMPARE
                    return (
                      <label key={`${u.university}-${u.program}`} className="checkable" style={{ opacity: disabled ? 0.4 : 1 }}><input type="checkbox" checked={isSelected} disabled={disabled} onChange={() => toggleUniversity(u.university)} /> {u.university} — {u.program}</label>
                    )
                  })}
                </div>
              </div>
            )}

            {isNearTerm && (isGermanyInScope || (backendRequiredFields.size > 0 && (programMode === 'specific' || appMode === 'compare'))) && (
              <div className="section-panel">
                <div className="section-title">Contextual Requirements</div>
                {isGermanyInScope && (
                  <div className="field-grid" style={{ marginBottom: '1.5rem' }}>
                    <label className="field">German level<select value={profile.german_level} onChange={set('german_level')}><option value="">None</option><option value="A1">A1</option><option value="A2">A2</option><option value="B1">B1</option><option value="B2">B2</option><option value="C1">C1</option><option value="C2">C2</option></select></label>
                    <label className="checkable" style={{ marginTop: 'auto', paddingBottom: '0.5rem' }}><input type="checkbox" checked={profile.is_eu_eea_citizen} onChange={set('is_eu_eea_citizen')} /> EU/EEA Citizen</label>
                    <label className="checkable" style={{ marginTop: 'auto', paddingBottom: '0.5rem' }}><input type="checkbox" checked={profile.is_bildungsinlaender} onChange={set('is_bildungsinlaender')} /> Bildungsinländer</label>
                  </div>
                )}
                
                {(backendRequiredFields.has('gre') || backendRequiredFields.has('gate')) && (
                  <div className="field-grid">
                    {backendRequiredFields.has('gre') && (
                      <>
                        <label className="field">GRE Quant Scaled<input type="number" value={profile.gre_quant_scaled} onChange={set('gre_quant_scaled')} /></label>
                        <label className="field">GRE Quant %<input type="number" value={profile.gre_quant_percentile} onChange={set('gre_quant_percentile')} /></label>
                        <label className="field">GRE Verbal %<input type="number" value={profile.gre_verbal_percentile} onChange={set('gre_verbal_percentile')} /></label>
                        <label className="field">GRE AWA<input type="number" step="0.5" value={profile.gre_awa} onChange={set('gre_awa')} /></label>
                      </>
                    )}
                    {backendRequiredFields.has('gate') && <label className="checkable" style={{ gridColumn: '1 / -1', marginTop: '1rem' }}><input type="checkbox" checked={profile.gate_score_reported} onChange={set('gate_score_reported')} /> I have a GATE score</label>}
                  </div>
                )}

                {unknownRequirements.length > 0 && (
                  <div className="field-grid" style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }}>
                    {unknownRequirements.map(req => (
                      <label key={req} className="field">{formatLabel(req)}<input type="text" value={dynamicProfile[req] || ''} onChange={setDynamic(req)} /></label>
                    ))}
                  </div>
                )}
              </div>
            )}

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Processing...' : appMode === 'compare' ? 'Compare Selected' : 'Run Eligibility Engine'}
            </button>
          </form>

          {error && <div style={{ color: 'var(--danger)', marginTop: '2rem', padding: '1rem', border: '1px solid var(--danger)', borderRadius: '6px' }}>{error}</div>}
          
          {results && appMode === 'compare' && <ComparisonTable results={results} />}
          {results && appMode === 'check' && (
            <div className="results-grid">
              {results.map((r, i) => <ResultCard key={i} result={r} />)}
            </div>
          )}
        </>
      )}

      {appMode === 'chat' && <RagChatView />}
    </div>
  )
}