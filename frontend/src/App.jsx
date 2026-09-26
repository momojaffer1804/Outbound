import { useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000/eligibility'

const STATUS_ICON = {
  met: '✅',
  not_met: '❌',
  needs_review: '⚠️',
  not_applicable: '➖',
  informational: 'ℹ️',
}

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
    undergrad_institution_english_medium: null, // true / false / null (unknown)
    german_level: '',
    is_eu_eea_citizen: false,
    is_bildungsinlaender: false,
  }
}

// Convert empty-string number fields to null, cast others, before sending to the API.
function toRequestBody(profile) {
  const numOrNull = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  const strOrNull = (v) => (v === '' ? null : v)
  return {
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
}

function TriStateSelect({ label, value, onChange }) {
  // value: true | false | null
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
  const overallColor = {
    eligible: '#1a7f37',
    not_eligible: '#c0392b',
    needs_review: '#b7791f',
  }[result.overall_status] || '#555'

  return (
    <div className="result-card">
      <div className="result-header">
        <div>
          <h3>{result.university}</h3>
          <p className="program">{result.program} — {result.academic_year}</p>
        </div>
        <span className="overall-badge" style={{ backgroundColor: overallColor }}>
          {result.overall_status.replace('_', ' ')}
        </span>
      </div>

      {result.error && (
        <p className="error-banner">Couldn't fetch live data for this university: {result.error}</p>
      )}

      <ul className="judgment-list">
        {result.judgments.map((j, i) => (
          <li key={i} className={`judgment ${j.status}`}>
            <span className="icon">{STATUS_ICON[j.status] || '•'}</span>
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

function App() {
  const [profile, setProfile] = useState(emptyProfile())
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [countryFilter, setCountryFilter] = useState('All')

  const availableCountries = results
    ? ['All', ...new Set(results.map((r) => r.country))]
    : ['All']

  const visibleResults = results
    ? results.filter((r) => countryFilter === 'All' || r.country === countryFilter)
    : null

  const isNearTerm = profile.flow === 'near_term'

  const set = (key) => (e) => {
    const val = e && e.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e
    setProfile((p) => ({ ...p, [key]: val }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const resp = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toRequestBody(profile)),
      })
      if (!resp.ok) {
        throw new Error(`API returned ${resp.status}`)
      }
      const data = await resp.json()
      setResults(data)
    } catch (err) {
      setError(
        `Couldn't reach the eligibility API. Is it running at ${API_URL}? (${err.message})`
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <h1>Outbound — Masters Eligibility Check</h1>

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="flow-toggle">
          <label>
            <input
              type="radio"
              name="flow"
              value="early_planner"
              checked={profile.flow === 'early_planner'}
              onChange={set('flow')}
            />
            Early planner (CGPA only — I don't have GRE/English scores yet)
          </label>
          <label>
            <input
              type="radio"
              name="flow"
              value="near_term"
              checked={profile.flow === 'near_term'}
              onChange={set('flow')}
            />
            Near-term applicant (I have my scores)
          </label>
        </div>

        <div className="field-grid">
          <label className="field">
            Citizenship
            <input type="text" placeholder="e.g. India" value={profile.citizenship} onChange={set('citizenship')} />
          </label>
          <label className="field">
            Undergrad country (leave blank if same as citizenship)
            <input type="text" placeholder="e.g. India" value={profile.undergrad_country} onChange={set('undergrad_country')} />
          </label>
          <label className="field">
            CGPA (10-point scale)
            <input type="number" step="0.01" value={profile.cgpa} onChange={set('cgpa')} />
          </label>

          {isNearTerm && (
            <>
              <TriStateSelect
                label="Was your Bachelor's institution English-medium?"
                value={profile.undergrad_institution_english_medium}
                onChange={(v) => setProfile((p) => ({ ...p, undergrad_institution_english_medium: v }))}
              />

              <label className="field">
                English test type
                <select value={profile.english_test_type} onChange={set('english_test_type')}>
                  <option value="">Not taken / N/A</option>
                  <option value="IELTS">IELTS</option>
                  <option value="TOEFL">TOEFL</option>
                  <option value="TOEIC">TOEIC</option>
                  <option value="TEPS">TEPS</option>
                </select>
              </label>
              <label className="field">
                English score
                <input type="number" step="0.1" value={profile.english_score} onChange={set('english_score')} />
              </label>
              {profile.english_test_type === 'TOEFL' && (
                <label className="field checkbox">
                  <input
                    type="checkbox"
                    checked={profile.toefl_test_date_on_or_after_2026_01_21}
                    onChange={set('toefl_test_date_on_or_after_2026_01_21')}
                  />
                  My TOEFL test date was on/after 21 Jan 2026 (new scale)
                </label>
              )}

              <label className="field">
                GRE Quant — scaled score (130-170, used by TUM)
                <input type="number" value={profile.gre_quant_scaled} onChange={set('gre_quant_scaled')} />
              </label>
              <label className="field">
                GRE AWA
                <input type="number" step="0.5" value={profile.gre_awa} onChange={set('gre_awa')} />
              </label>
              <label className="field">
                GRE Quant — percentile (0-100, used by RWTH — different scale from above)
                <input type="number" value={profile.gre_quant_percentile} onChange={set('gre_quant_percentile')} />
              </label>
              <label className="field">
                GRE Verbal — percentile (used by RWTH)
                <input type="number" value={profile.gre_verbal_percentile} onChange={set('gre_verbal_percentile')} />
              </label>
              <label className="field checkbox">
                <input type="checkbox" checked={profile.gate_score_reported} onChange={set('gate_score_reported')} />
                I have a GATE (CS) score instead of GRE (India only, TUM)
              </label>

              <label className="field">
                German level
                <select value={profile.german_level} onChange={set('german_level')}>
                  <option value="">None / not sure</option>
                  <option value="A1">A1</option>
                  <option value="A2">A2</option>
                  <option value="B1">B1</option>
                  <option value="B2">B2</option>
                  <option value="C1">C1</option>
                  <option value="C2">C2</option>
                </select>
              </label>
              <label className="field checkbox">
                <input type="checkbox" checked={profile.is_eu_eea_citizen} onChange={set('is_eu_eea_citizen')} />
                I'm an EU/EEA citizen
              </label>
              <label className="field checkbox">
                <input type="checkbox" checked={profile.is_bildungsinlaender} onChange={set('is_bildungsinlaender')} />
                I completed secondary education in Germany (Bildungsinländer)
              </label>
            </>
          )}
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Checking...' : 'Check eligibility'}
        </button>
      </form>

      {error && <p className="error-banner">{error}</p>}

      {results && (
        <>
          <div className="country-filter">
            <label>
              Filter by country:{' '}
              <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
                {availableCountries.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="results">
            {visibleResults.map((r, i) => (
              <ResultCard key={i} result={r} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default App