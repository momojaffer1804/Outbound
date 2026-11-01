import { useState, useEffect, useMemo, useRef } from 'react'
import { marked } from 'marked'
import './App.css'

marked.setOptions({
  gfm: true,
  breaks: true,
})

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const API_URL = `${API_BASE_URL}/eligibility`
const UNIVERSITIES_URL = `${API_BASE_URL}/universities`

const MAX_COMPARE = 3
const MAX_COUNTRIES = 3
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
  if (lower.includes('tum') || lower.includes('munich') || lower.includes('rwth') || lower.includes('aachen') || lower.includes('berlin') || lower.includes('stuttgart') || lower.includes('darmstadt')) return 'Germany'
  if (lower.includes('kaist') || lower.includes('seoul')) return 'South Korea'
  if (lower.includes('delft') || lower.includes('netherlands')) return 'Netherlands'
  if (lower.includes('eth') || lower.includes('zurich') || lower.includes('switzerland')) return 'Switzerland'
  if (lower.includes('nus') || lower.includes('singapore')) return 'Singapore'
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

function StatusPill({ status }) {
  const labels = {
    met: 'MET',
    not_met: 'UNMET',
    needs_review: 'REVIEW',
    not_applicable: 'N/A',
    informational: 'INFO',
  }
  const label = labels[status] || (status ? status.toUpperCase() : 'UNKNOWN')
  return <span className={`status-pill ${status}`}>{label}</span>
}

function ResultCard({ result }) {
  return (
    <div className="result-card">
      <div className="result-header">
        <div>
          <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700 }}>{result.university}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
            {result.program} — {result.academic_year === 'unknown_year' ? 'Year Unspecified' : result.academic_year}
          </p>
        </div>
        <span className={`overall-badge ${result.overall_status}`}>
          {result.overall_status.replace('_', ' ')}
        </span>
      </div>
      {result.error && <p style={{ color: 'var(--status-unmet-text)', marginBottom: '1rem', fontSize: '0.85rem' }}>Error: {result.error}</p>}
      <ul className="judgment-list">
        {result.judgments.map((j, i) => (
          <li key={i} className="judgment">
            <StatusPill status={j.status} />
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
              <th key={r.university + r.program}>
                {r.university}<br />
                <span style={{ color: 'var(--text-muted)', fontWeight: 500, fontSize: '0.8rem' }}>{r.program}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requirementTypes.map((type) => (
            <tr key={type}>
              <td style={{ fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-main)' }}>{type.replace(/_/g, ' ')}</td>
              {results.map((r) => {
                const judgment = r.judgments.find((j) => j.requirement_type === type)
                if (!judgment) return <td key={r.university + r.program} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>—</td>
                return (
                  <td key={r.university + r.program}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', alignItems: 'flex-start' }}>
                      <StatusPill status={judgment.status} />
                      <span style={{ fontSize: '0.825rem', color: 'var(--text-main)' }}>{judgment.detail}</span>
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

function getSourceInfo(url) {
  if (!url) return { name: 'University Page', type: 'Official Source', isOfficial: true }
  const lower = url.toLowerCase()
  if (lower.includes('yocket')) {
    return { name: 'Yocket', type: 'Third-Party Portal', isOfficial: false }
  }
  if (lower.includes('mygermanuniversity')) {
    return { name: 'MyGermanUniversity', type: 'Third-Party Portal', isOfficial: false }
  }
  if (lower.includes('tum.de') || lower.includes('rwth-aachen.de') || lower.includes('kaist.ac.kr') || lower.includes('tu.berlin') || lower.includes('uni-stuttgart.de') || lower.includes('tu-darmstadt.de') || lower.includes('tudelft.nl') || lower.includes('ethz.ch') || lower.includes('nus.edu.sg')) {
    return { name: 'Official University Website', type: 'Tier-1 Official Source', isOfficial: true }
  }
  return { name: 'Official Website', type: 'Official Source', isOfficial: true }
}

function CourseworkAuditorView() {
  const [credits, setCredits] = useState({
    theoretical_cs: 24,
    practical_cs: 35,
    technical_cs: 20,
    mathematics: 28,
  })
  const [creditSystem, setCreditSystem] = useState('ECTS')
  const [auditResult, setAuditResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const runAudit = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/audit/coursework`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credits, credit_system: creditSystem }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAuditResult(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runAudit()
  }, [credits, creditSystem])

  const setCreditVal = (key, val) => {
    setCredits(prev => ({ ...prev, [key]: Number(val) || 0 }))
  }

  return (
    <div className="coursework-auditor">
      <div className="section-panel" style={{ marginBottom: '1.5rem' }}>
        <div className="section-title">ECTS Credit Gap & Curricular Overlap Auditor</div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Evaluate your undergraduate coursework coverage against standard European Computer Science clusters to test university-specific deficit limits (e.g. RWTH Aachen's 42 CP ceiling, TU Berlin's subject minimums, TU Darmstadt's 30 CP deficit rule).
        </p>

        <div style={{ marginBottom: '1.25rem' }}>
          <label className="field">
            Undergraduate Credit Scale:
            <select value={creditSystem} onChange={(e) => setCreditSystem(e.target.value)}>
              <option value="ECTS">European ECTS Credits (1 credit = 1 ECTS)</option>
              <option value="INDIAN_CREDIT">Indian University Credits (approx. 1 credit = 1.5 ECTS)</option>
              <option value="US_SEMESTER">US Semester Credit Hours (approx. 1 credit = 1.8 ECTS)</option>
            </select>
          </label>
        </div>

        <div className="field-grid">
          <label className="field">
            Theoretical CS (Formal Lang, Automata, Logic)
            <input type="number" step="0.5" value={credits.theoretical_cs} onChange={(e) => setCreditVal('theoretical_cs', e.target.value)} />
          </label>
          <label className="field">
            Practical CS (OOP, DSA, Databases, SE, ML)
            <input type="number" step="0.5" value={credits.practical_cs} onChange={(e) => setCreditVal('practical_cs', e.target.value)} />
          </label>
          <label className="field">
            Systems & Tech CS (OS, Arch, Networks, Security)
            <input type="number" step="0.5" value={credits.technical_cs} onChange={(e) => setCreditVal('technical_cs', e.target.value)} />
          </label>
          <label className="field">
            Higher Mathematics (Calculus, Linear Alg, Stats)
            <input type="number" step="0.5" value={credits.mathematics} onChange={(e) => setCreditVal('mathematics', e.target.value)} />
          </label>
        </div>
      </div>

      {auditResult && (
        <>
          {/* Institutional Verdicts */}
          <div className="section-panel" style={{ marginBottom: '1.5rem' }}>
            <div className="section-title">Institutional Eligibility Verdicts</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              
              <div style={{ background: 'var(--bg-base)', padding: '1.25rem', borderRadius: '8px', border: `1px solid ${auditResult.rwth_eligible ? 'var(--status-met-border)' : 'var(--status-unmet-border)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>RWTH Aachen</strong>
                  <span className={`status-pill ${auditResult.rwth_eligible ? 'met' : 'not_met'}`}>{auditResult.rwth_eligible ? 'PASS' : 'FAIL'}</span>
                </div>
                <p style={{ fontSize: '0.825rem', marginTop: '0.5rem', color: 'var(--text-main)' }}>{auditResult.rwth_verdict}</p>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Threshold: Max 42 CP deficit allowed.</div>
              </div>

              <div style={{ background: 'var(--bg-base)', padding: '1.25rem', borderRadius: '8px', border: `1px solid ${auditResult.tu_berlin_eligible ? 'var(--status-met-border)' : 'var(--status-unmet-border)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>TU Berlin</strong>
                  <span className={`status-pill ${auditResult.tu_berlin_eligible ? 'met' : 'not_met'}`}>{auditResult.tu_berlin_eligible ? 'PASS' : 'FAIL'}</span>
                </div>
                <p style={{ fontSize: '0.825rem', marginTop: '0.5rem', color: 'var(--text-main)' }}>{auditResult.tu_berlin_verdict}</p>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Threshold: $\ge$12 Theory, $\ge$12 Systems, $\ge$18 Math.</div>
              </div>

              <div style={{ background: 'var(--bg-base)', padding: '1.25rem', borderRadius: '8px', border: `1px solid ${auditResult.tu_darmstadt_eligible ? 'var(--status-met-border)' : 'var(--status-unmet-border)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>TU Darmstadt</strong>
                  <span className={`status-pill ${auditResult.tu_darmstadt_eligible ? 'met' : 'not_met'}`}>{auditResult.tu_darmstadt_eligible ? 'PASS' : 'FAIL'}</span>
                </div>
                <p style={{ fontSize: '0.825rem', marginTop: '0.5rem', color: 'var(--text-main)' }}>{auditResult.tu_darmstadt_verdict}</p>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Threshold: Max 30 CP entrance deficit.</div>
              </div>

            </div>
          </div>

          {/* Breakdown Table */}
          <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="comparison-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Subject Competency Cluster</th>
                  <th>Required (ECTS)</th>
                  <th>Completed (ECTS)</th>
                  <th>Gap / Deficit</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {auditResult.category_breakdown.map((cat, i) => (
                  <tr key={i}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{cat.label}</div>
                      <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>{cat.description}</div>
                    </td>
                    <td>{cat.required_ects} ECTS</td>
                    <td><strong style={{ color: 'var(--accent)' }}>{cat.completed_ects} ECTS</strong></td>
                    <td>{cat.gap_ects > 0 ? <span style={{ color: 'var(--status-unmet-text)', fontWeight: 600 }}>-{cat.gap_ects} ECTS</span> : <span style={{ color: 'var(--status-met-text)' }}>0 ECTS</span>}</td>
                    <td><StatusPill status={cat.is_satisfied ? 'met' : 'not_met'} /></td>
                  </tr>
                ))}
                <tr style={{ background: 'var(--bg-surface-elevated)', fontWeight: 700 }}>
                  <td>TOTAL OVERALL</td>
                  <td>{auditResult.total_required_ects} ECTS</td>
                  <td>{auditResult.total_completed_ects} ECTS</td>
                  <td style={{ color: auditResult.total_gap_ects > 0 ? 'var(--status-unmet-text)' : 'var(--status-met-text)' }}>-{auditResult.total_gap_ects} ECTS</td>
                  <td><StatusPill status={auditResult.rwth_eligible ? 'met' : 'not_met'} /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function RagChatView() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Welcome to Outbound Grounding Assistant. Ask any question about university requirements, deadlines, or test cutoffs. All answers are cross-referenced with Tier-1 official university documents.' }])
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
      const res = await fetch(`${API_BASE_URL}/ask`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: userQ }) })
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
        <span>Outbound Grounding Engine</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Tier-1 Source Verified</span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message-wrapper ${msg.role}`}>
            {msg.role === 'assistant' ? (
              <div
                className="chat-bubble markdown-content"
                dangerouslySetInnerHTML={{ __html: marked.parse(msg.content) }}
              />
            ) : (
              <div className="chat-bubble">{msg.content}</div>
            )}
            {msg.sources && msg.sources.length > 0 && (
              <div className="chat-sources-panel">
                <div className="chat-sources-header">Sources:</div>
                <div className="chat-sources-list">
                  {msg.sources
                    .map((src) => ({ src, info: getSourceInfo(src) }))
                    .sort((a, b) => (b.info.isOfficial ? 1 : 0) - (a.info.isOfficial ? 1 : 0))
                    .map(({ src, info }, idx) => (
                      <a key={idx} href={src} target="_blank" rel="noreferrer" className={`source-item ${info.isOfficial ? 'official' : 'third-party'}`}>
                        <span className="source-label">Source {idx + 1}: {info.name}</span>
                        <span className="source-type">{info.type}</span>
                      </a>
                    ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message-wrapper assistant"><div className="chat-bubble" style={{ opacity: 0.7 }}>Retrieving tier-1 facts...</div></div>}
        <div ref={endRef} />
      </div>
      <form onSubmit={handleSend} className="chat-input-form">
        <input type="text" className="chat-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search requirement facts, TOEFL rules, or conflict checks..." />
        <button type="submit" className="chat-send-btn" disabled={loading}>Send</button>
      </form>
    </div>
  )
}

export default function App() {
  const [appMode, setAppMode] = useState('check') // 'check' | 'compare' | 'auditor' | 'chat'
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
      <header className="app-header">
        <div className="app-title-group">
          <h1>Outbound</h1>
          <span className="app-subtitle">Source-Grounded Masters Eligibility Engine</span>
        </div>
      </header>

      <div className="app-mode-tabs">
        <button type="button" className={`tab-btn ${appMode === 'check' ? 'active' : ''}`} onClick={() => { setAppMode('check'); setResults(null); setError(null) }}>Eligibility Engine</button>
        <button type="button" className={`tab-btn ${appMode === 'compare' ? 'active' : ''}`} onClick={() => { setAppMode('compare'); setResults(null); setError(null); setSelectedUniversities(prev => prev.slice(0, MAX_COMPARE)) }}>Compare Programs</button>
        <button type="button" className={`tab-btn ${appMode === 'auditor' ? 'active' : ''}`} onClick={() => { setAppMode('auditor'); setResults(null); setError(null) }}>ECTS Credit Auditor</button>
        <button type="button" className={`tab-btn ${appMode === 'chat' ? 'active' : ''}`} onClick={() => { setAppMode('chat'); setResults(null); setError(null) }}>Grounding Assistant</button>
      </div>

      {(appMode === 'check' || appMode === 'compare') && (
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
                  <label className="checkable"><input type="radio" checked={countryMode === 'specific'} onChange={() => setCountryMode('specific')} /> Specific countries (up to {MAX_COUNTRIES})</label>
                </div>

                {countryMode === 'specific' && (
                  <div className="checkbox-list" style={{ marginBottom: '2rem', display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '1rem' }}>
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
                          <label key={`${u.university}-${u.program}`} className="checkable"><input type="checkbox" checked={selectedUniversities.includes(u.university)} onChange={() => toggleUniversity(u.university)} /> {u.university} — {u.program} <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({u.country})</span></label>
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
                      <label key={`${u.university}-${u.program}`} className="checkable" style={{ opacity: disabled ? 0.4 : 1 }}><input type="checkbox" checked={isSelected} disabled={disabled} onChange={() => toggleUniversity(u.university)} /> {u.university} — {u.program} <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({u.country})</span></label>
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
                    {backendRequiredFields.has('gate') && <label className="checkable" style={{ gridColumn: '1 / -1', marginTop: '1rem' }}><input type="checkbox" checked={profile.gate_score_reported} onChange={set('gate_score_reported')} /> I have a GATE CS score</label>}
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

          {error && <div style={{ color: 'var(--status-unmet-text)', backgroundColor: 'var(--status-unmet-bg)', marginTop: '2rem', padding: '1rem', border: '1px solid var(--status-unmet-border)', borderRadius: '8px', fontSize: '0.9rem' }}>{error}</div>}
          
          {results && appMode === 'compare' && <ComparisonTable results={results} />}
          {results && appMode === 'check' && (
            <div className="results-grid">
              {results.map((r, i) => <ResultCard key={i} result={r} />)}
            </div>
          )}
        </>
      )}

      {appMode === 'auditor' && <CourseworkAuditorView />}
      {appMode === 'chat' && <RagChatView />}
    </div>
  )
}
