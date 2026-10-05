import { useState, useEffect, useMemo } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000/eligibility'
const UNIVERSITIES_URL = 'http://127.0.0.1:8000/universities'

const STATUS_ICON = {
  met: '✅',
  not_met: '❌',
  needs_review: '⚠️',
  not_applicable: '➖',
  informational: 'ℹ️',
}

const MAX_COMPARE = 3
const MAX_COUNTRIES = 2

// KNOWN_REQUIREMENTS: Fields the frontend has custom UI for.
// Anything NOT in this list will be auto-generated as a text input.
const KNOWN_REQUIREMENTS = ['cgpa', 'english_test', 'gre', 'gate', 'german_test']

function emptyProfile() {
  return {
    flow: 'early_planner',
    citizenship: '',
    undergrad_country: '',
    cgpa: '',
    gre_quant_scaled: '',
    gre_quant_percentile: '',
    gre_verbal_percentile: '',
    gre_awa: '',
    gate_score_reported: false,
    english_test_type: '',
    english_score: '',
    toefl_test_date_on_or_after_2026_01_21: false,
    undergrad_institution_english_medium: null,
    german_level: '',
    is_eu_eea_citizen: false,
    is_bildungsinlaender: false,
  }
}

function toRequestBody(profile, dynamicProfile) {
  const numOrNull = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  const strOrNull = (v) => (v === '' ? null : v)
  
  const baseProfile = {
    flow: profile.flow,
    citizenship: strOrNull(profile.citizenship),
    undergrad_country: strOrNull(profile.undergrad_country),
    cgpa: numOrNull(profile.cgpa),
    gre_quant_scaled: numOrNull(profile.gre_quant_scaled),
    gre_quant_percentile: numOrNull(profile.gre_quant_percentile),
    gre_verbal_percentile: numOrNull(profile.gre_verbal_percentile),
    gre_awa: numOrNull(profile.gre_awa),
    gate_score_reported: !!profile.gate_score_reported,
    english_test_type: strOrNull(profile.english_test_type),
    english_score: numOrNull(profile.english_score),
    toefl_test_date_on_or_after_2026_01_21: !!profile.toefl_test_date_on_or_after_2026_01_21,
    undergrad_institution_english_medium: profile.undergrad_institution_english_medium,
    german_level: strOrNull(profile.german_level),
    is_eu_eea_citizen: !!profile.is_eu_eea_citizen,
    is_bildungsinlaender: !!profile.is_bildungsinlaender,
  }

  // Merge the dynamic auto-generated fields directly into the root object
  return { ...baseProfile, ...dynamicProfile }
}

function deriveCountry(universityName) {
  if (!universityName) return 'Unknown'
  const lower = universityName.toLowerCase()
  if (lower.includes('tum') || lower.includes('munich') || lower.includes('rwth') || lower.includes('aachen')) return 'Germany'
  if (lower.includes('kaist') || lower.includes('seoul')) return 'South Korea'
  if (lower.includes('uva') || lower.includes('delft') || lower.includes('eindhoven')) return 'Netherlands'
  if (lower.includes('copenhagen')) return 'Denmark'
  if (lower.includes('sorbonne') || lower.includes('paris')) return 'France'
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
      <select
        value={value === null ? 'unknown' : value ? 'yes' : 'no'}
        onChange={(e) => {
          const v = e.target.value
          onChange(v === 'unknown' ? null : v === 'yes')
        }}
      >
        <option value="unknown">Not sure / N/A</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </label>
  )
}

function ResultCard({ result }) {
  const overallColor = { eligible: '#1a7f37', not_eligible: '#c0392b', needs_review: '#b7791f' }[result.overall_status] || '#555'
  const displayYear = result.academic_year === 'unknown_year' ? 'Year Unspecified' : result.academic_year
  
  return (
    <div className="result-card">
      <div className="result-header">
        <div>
          <h3>{result.university}</h3>
          <p className="program">{result.program} — {displayYear}</p>
        </div>
        <span className="overall-badge" style={{ backgroundColor: overallColor }}>{result.overall_status.replace('_', ' ')}</span>
      </div>
      {result.error && <p className="error-banner">Couldn't fetch live data for this university: {result.error}</p>}
      <ul className="judgment-list">
        {result.judgments.map((j, i) => (
          <li key={i} className={`judgment ${j.status}`}>
            <span className="icon">{STATUS_ICON[j.status] || '•'}</span>
            <div><strong>{j.requirement_type.replace(/_/g, ' ')}</strong><p>{j.detail}</p></div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ComparisonTable({ results }) {
  const requirementTypes = []
  results.forEach((r) => { 
    r.judgments.forEach((j) => { 
      if (!requirementTypes.includes(j.requirement_type)) requirementTypes.push(j.requirement_type) 
    }) 
  })
  
  return (
    <div className="comparison-table-wrapper">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Requirement</th>
            {results.map((r) => (
              <th key={r.university + r.program}>{r.university}<br /><span className="comparison-program">{r.program}</span></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requirementTypes.map((type) => (
            <tr key={type}>
              <td className="requirement-label">{type.replace(/_/g, ' ')}</td>
              {results.map((r) => {
                const judgment = r.judgments.find((j) => j.requirement_type === type)
                if (!judgment) return <td key={r.university + r.program} className="comparison-cell empty">—</td>
                return (
                  <td key={r.university + r.program} className={`comparison-cell ${judgment.status}`}>
                    <span className="icon">{STATUS_ICON[judgment.status] || '•'}</span>
                    <span className="comparison-detail">{judgment.detail}</span>
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

// Formats snake_case requirement strings into clean Title Case labels
function formatLabel(str) {
  return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

export default function App() {
  const [appMode, setAppMode] = useState('check')
  const [profile, setProfile] = useState(emptyProfile())
  
  // Dynamic state for auto-generated backend requirements
  const [dynamicProfile, setDynamicProfile] = useState({})
  
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [countryFilter, setCountryFilter] = useState('All')

  // Target Selections (4-Way Matrix)
  const [countryMode, setCountryMode] = useState('all') // 'all' | 'specific'
  const [selectedCountries, setSelectedCountries] = useState([])
  const [programMode, setProgramMode] = useState('all') // 'all' | 'specific'
  const [selectedUniversities, setSelectedUniversities] = useState([])

  const [availableUniversities, setAvailableUniversities] = useState([])
  const [universitiesLoading, setUniversitiesLoading] = useState(false)

  useEffect(() => {
    if (availableUniversities.length === 0) {
      setUniversitiesLoading(true)
      fetch(UNIVERSITIES_URL)
        .then((resp) => resp.json())
        .then((data) => setAvailableUniversities(data))
        .catch(() => {})
        .finally(() => setUniversitiesLoading(false))
    }
  }, [availableUniversities.length])

  // --- CORE PROGRESSIVE DISCLOSURE LOGIC ---
  // Only queries backend requirements IF the user is explicitly targeting specific programs
  const backendRequiredFields = useMemo(() => {
    const required = new Set()
    
    // Only fetch specific fields if they are in "Sniper Mode"
    if (programMode === 'specific' || appMode === 'compare') {
      selectedUniversities.forEach(uniName => {
        const uniData = availableUniversities.find(u => u.university === uniName)
        if (uniData && Array.isArray(uniData.active_requirements)) {
          uniData.active_requirements.forEach(req => required.add(req))
        }
      })
    }
    return required
  }, [appMode, programMode, selectedUniversities, availableUniversities])

  const unknownRequirements = Array.from(backendRequiredFields).filter(req => !KNOWN_REQUIREMENTS.includes(req))

  function toggleCountry(countryName) {
    setSelectedCountries((prev) => {
      const next = prev.includes(countryName) 
        ? prev.filter((c) => c !== countryName) 
        : prev.length < MAX_COUNTRIES ? [...prev, countryName] : prev
      
      // Auto-remove universities that don't match the new country scope
      setSelectedUniversities((currentUnis) =>
        currentUnis.filter((uName) => {
          const uObj = availableUniversities.find((item) => item.university === uName)
          return next.includes(uObj?.country || deriveCountry(uName))
        })
      )
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

  const set = (key) => (e) => {
    const val = e && e.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e
    setProfile((p) => ({ ...p, [key]: val }))
  }

  const setDynamic = (key) => (e) => {
    const val = e.target.value
    setDynamicProfile((p) => ({ ...p, [key]: val }))
  }

  const filteredUniversities = availableUniversities.filter((u) => {
    if (countryMode === 'all') return true
    return selectedCountries.includes(u.country || deriveCountry(u.university))
  })

  const isNearTerm = profile.flow === 'near_term'

  // Determine if Germany-specific contextual fields should show
  const isGermanyInScope =
    appMode === 'check' 
      ? (countryMode === 'specific' && selectedCountries.includes('Germany')) ||
        (programMode === 'specific' && selectedUniversities.some((u) => deriveCountry(u) === 'Germany'))
      : selectedUniversities.some((u) => deriveCountry(u) === 'Germany')

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true); setError(null); setResults(null)
    
    try {
      const url = buildEligibilityUrl({ selectedUniversities, selectedCountries, countryMode, programMode, appMode, availableUniversities })
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toRequestBody(profile, dynamicProfile)),
      })
      if (!resp.ok) throw new Error(`API returned ${resp.status}`)
      const data = await resp.json()
      setResults(data)
    } catch (err) {
      setError(`Couldn't reach API: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const availableCountries = [...new Set(availableUniversities.map((u) => u.country || deriveCountry(u.university)))].sort()
  const visibleResults = results ? results.filter((r) => countryFilter === 'All' || r.country === countryFilter) : null

  return (
    <div className="app">
      <h1>Outbound — Masters Eligibility Check</h1>

      {/* --- TABS --- */}
      <div className="app-mode-tabs" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid #333', paddingBottom: '1rem' }}>
        <button type="button" onClick={() => { setAppMode('check'); setResults(null); setError(null) }} style={{ padding: '0.6rem 1.2rem', background: appMode === 'check' ? '#1a7f37' : '#2d2d2d', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: appMode === 'check' ? 'bold' : 'normal' }}>
          Eligibility Check
        </button>
        <button type="button" onClick={() => { setAppMode('compare'); setResults(null); setError(null); setSelectedUniversities((prev) => prev.slice(0, MAX_COMPARE)) }} style={{ padding: '0.6rem 1.2rem', background: appMode === 'compare' ? '#1a7f37' : '#2d2d2d', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: appMode === 'compare' ? 'bold' : 'normal' }}>
          Compare Programs
        </button>
      </div>

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="flow-toggle">
          <label><input type="radio" name="flow" value="early_planner" checked={profile.flow === 'early_planner'} onChange={set('flow')} />Early planner (CGPA only)</label>
          <label><input type="radio" name="flow" value="near_term" checked={profile.flow === 'near_term'} onChange={set('flow')} />Near-term applicant (I have my scores)</label>
        </div>

        {/* --- LAYER 1: BASE UNIVERSAL FIELDS --- */}
        <div className="field-grid">
          <label className="field">Citizenship<input type="text" placeholder="e.g. India" value={profile.citizenship} onChange={set('citizenship')} /></label>
          <label className="field">Undergrad country<input type="text" placeholder="e.g. India" value={profile.undergrad_country} onChange={set('undergrad_country')} /></label>
          <label className="field">CGPA (10-point scale)<input type="number" step="0.01" value={profile.cgpa} onChange={set('cgpa')} /></label>
        </div>

        {/* English Proficiency (Always visible for near-term) */}
        {isNearTerm && (
          <div className="near-term-section" style={{ marginTop: '1rem', padding: '1.2rem', backgroundColor: '#1e1e1e', borderRadius: '8px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.05rem', color: '#4a9eff' }}>English Proficiency</h3>
            <div className="field-grid">
              <TriStateSelect label="Was undergrad English-medium?" value={profile.undergrad_institution_english_medium} onChange={(v) => setProfile((p) => ({ ...p, undergrad_institution_english_medium: v }))} />
              <label className="field">Test type<select value={profile.english_test_type} onChange={set('english_test_type')}><option value="">Not taken / N/A</option><option value="IELTS">IELTS</option><option value="TOEFL">TOEFL</option><option value="TOEIC">TOEIC</option><option value="TEPS">TEPS</option></select></label>
              <label className="field">Score<input type="number" step="0.1" value={profile.english_score} onChange={set('english_score')} /></label>
              {profile.english_test_type === 'TOEFL' && (
                <label className="field checkbox"><input type="checkbox" checked={profile.toefl_test_date_on_or_after_2026_01_21} onChange={set('toefl_test_date_on_or_after_2026_01_21')} />My TOEFL test date was on/after 21 Jan 2026 (new scale)</label>
              )}
            </div>
          </div>
        )}

        {/* --- LAYER 2: TARGET SELECTOR (4-WAY MATRIX) --- */}
        {appMode === 'check' && (
          <div className="target-section" style={{ marginTop: '1.5rem', padding: '1.2rem', backgroundColor: '#252525', borderRadius: '8px' }}>
            
            {/* Step 1: Country Picker */}
            <p style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Step 1: Target Countries</p>
            <div style={{ display: 'flex', gap: '2rem', marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" checked={countryMode === 'all'} onChange={() => { setCountryMode('all'); setSelectedCountries([]) }} />Open to any country
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" checked={countryMode === 'specific'} onChange={() => setCountryMode('specific')} />Specific countries (up to {MAX_COUNTRIES})
              </label>
            </div>

            {countryMode === 'specific' && (
              <div style={{ marginBottom: '1.5rem' }}>
                {universitiesLoading && <p className="compare-status">Loading country list…</p>}
                {availableCountries.map((c) => {
                  const isSelected = selectedCountries.includes(c)
                  const disabled = !isSelected && selectedCountries.length >= MAX_COUNTRIES
                  return (
                    <label key={c} style={{ display: 'inline-block', marginRight: '1.5rem', marginBottom: '0.5rem', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1 }}>
                      <input type="checkbox" checked={isSelected} disabled={disabled} onChange={() => toggleCountry(c)} style={{ marginRight: '6px' }} />{c}
                    </label>
                  )
                })}
              </div>
            )}

            {/* Step 2: Program Picker */}
            {(countryMode === 'all' || selectedCountries.length > 0) && (
              <>
                <hr style={{ borderColor: '#333', margin: '1rem 0' }} />
                <p style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Step 2: Target Programs</p>
                <div style={{ display: 'flex', gap: '2rem', marginBottom: '1rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input type="radio" checked={programMode === 'all'} onChange={() => { setProgramMode('all'); setSelectedUniversities([]) }} />All programs {countryMode === 'specific' ? 'in selected countries' : ''}
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input type="radio" checked={programMode === 'specific'} onChange={() => setProgramMode('specific')} />Pick specific programs
                  </label>
                </div>

                {programMode === 'specific' && (
                  <div style={{ maxHeight: '200px', overflowY: 'auto', padding: '0.5rem', background: '#1c1c1c', borderRadius: '4px' }}>
                    {filteredUniversities.map((u) => {
                      const isSelected = selectedUniversities.includes(u.university)
                      return (
                        <label key={`${u.university}-${u.program}`} style={{ display: 'block', marginBottom: '0.5rem', cursor: 'pointer' }}>
                          <input type="checkbox" checked={isSelected} onChange={() => toggleUniversity(u.university)} style={{ marginRight: '8px' }} />{u.university} — {u.program}
                        </label>
                      )
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Compare Mode Target Selector */}
        {appMode === 'compare' && (
          <div className="target-section" style={{ marginTop: '1.5rem', padding: '1.2rem', backgroundColor: '#252525', borderRadius: '8px' }}>
            <p style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Select Programs to Compare (up to {MAX_COMPARE})</p>
            {availableUniversities.map((u) => {
              const isSelected = selectedUniversities.includes(u.university)
              const disabled = !isSelected && selectedUniversities.length >= MAX_COMPARE
              return (
                <label key={`${u.university}-${u.program}`} style={{ display: 'block', marginBottom: '0.5rem', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1 }}>
                  <input type="checkbox" checked={isSelected} disabled={disabled} onChange={() => toggleUniversity(u.university)} style={{ marginRight: '8px' }} />{u.university} — {u.program}
                </label>
              )
            })}
          </div>
        )}

        {/* --- LAYER 3: DYNAMIC CONTEXTUAL REQUIREMENTS --- */}
        {isNearTerm && (
          <div className="contextual-requirements-section" style={{ marginTop: '1.5rem' }}>
            
            {/* Country Level: German fields */}
            {isGermanyInScope && (
               <div style={{ padding: '1.5rem', backgroundColor: '#21262d', borderRadius: '8px', border: '1px solid #30363d', marginBottom: '1rem' }}>
                 <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.05rem', color: '#ffb347' }}>Germany Requirements</h3>
                 <div className="field-grid">
                   <label className="field">
                     German level
                     <select value={profile.german_level} onChange={set('german_level')}>
                       <option value="">None / not sure</option>
                       <option value="A1">A1</option><option value="A2">A2</option><option value="B1">B1</option>
                       <option value="B2">B2</option><option value="C1">C1</option><option value="C2">C2</option>
                     </select>
                   </label>
                   <label className="field checkbox"><input type="checkbox" checked={profile.is_eu_eea_citizen} onChange={set('is_eu_eea_citizen')} />I'm an EU/EEA citizen</label>
                   <label className="field checkbox"><input type="checkbox" checked={profile.is_bildungsinlaender} onChange={set('is_bildungsinlaender')} />Completed secondary education in Germany (Bildungsinländer)</label>
                 </div>
               </div>
            )}

            {/* Program Level: Dynamically pulled from backend only when specific programs are targeted */}
            {backendRequiredFields.size > 0 && (programMode === 'specific' || appMode === 'compare') && (
              <div style={{ padding: '1.5rem', backgroundColor: '#161b22', borderRadius: '8px', border: '1px solid #30363d' }}>
                <h3 style={{ marginTop: 0, marginBottom: '1rem', color: '#ff6b6b' }}>Specific Program Requirements</h3>
                
                {/* Custom Block: Standardized Tests */}
                {(backendRequiredFields.has('gre') || backendRequiredFields.has('gate')) && (
                  <div className="field-grid">
                    {backendRequiredFields.has('gre') && (
                      <>
                        <label className="field">GRE Quant Scaled (130-170)<input type="number" value={profile.gre_quant_scaled} onChange={set('gre_quant_scaled')} /></label>
                        <label className="field">GRE Quant Percentile (0-100)<input type="number" value={profile.gre_quant_percentile} onChange={set('gre_quant_percentile')} /></label>
                        <label className="field">GRE Verbal Percentile<input type="number" value={profile.gre_verbal_percentile} onChange={set('gre_verbal_percentile')} /></label>
                        <label className="field">GRE AWA<input type="number" step="0.5" value={profile.gre_awa} onChange={set('gre_awa')} /></label>
                      </>
                    )}
                    {backendRequiredFields.has('gate') && (
                      <label className="field checkbox"><input type="checkbox" checked={profile.gate_score_reported} onChange={set('gate_score_reported')} />I have a GATE score (India only)</label>
                    )}
                  </div>
                )}

                {/* Auto-Generator Block: For unknown requirements scraped by the backend */}
                {unknownRequirements.length > 0 && (
                  <>
                    {(backendRequiredFields.has('gre') || backendRequiredFields.has('gate')) && <hr style={{ borderColor: '#333', margin: '1.5rem 0' }} />}
                    <div className="field-grid">
                      {unknownRequirements.map(req => (
                        <label key={req} className="field">
                          {formatLabel(req)}
                          <input type="text" placeholder={`Enter ${formatLabel(req)}...`} value={dynamicProfile[req] || ''} onChange={setDynamic(req)} />
                        </label>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        <button type="submit" disabled={loading} style={{ marginTop: '1.5rem' }}>
          {loading ? 'Processing...' : appMode === 'compare' ? 'Compare selected' : 'Check eligibility'}
        </button>
      </form>

      {error && <p className="error-banner">{error}</p>}
      
      {results && appMode === 'compare' && (
        <ComparisonTable results={results} />
      )}
      
      {results && appMode === 'check' && (
        <>
          <div className="country-filter" style={{ marginTop: '2rem' }}>
            <label>Filter by country:{' '}
              <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
                {['All', ...new Set(results.map(r => r.country))].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
          <div className="results">
            {visibleResults.map((r, i) => <ResultCard key={i} result={r} />)}
          </div>
        </>
      )}
    </div>
  )
}