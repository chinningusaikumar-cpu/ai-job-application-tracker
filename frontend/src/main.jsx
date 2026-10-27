import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const DEFAULTS = {
  keyword: 'Software Developer',
  country: 'Worldwide',
  locations: ['Hyderabad', 'Bangalore', 'Chennai'],
  experience: 'Entry level / Fresher',
  workplace: 'Any',
  employment_type: 'Any',
  page: 1,
  page_size: 20,
  resume_text: ''
};
const COUNTRIES = ['Worldwide','India','United States','United Kingdom','Canada','Australia','Germany','United Arab Emirates','Singapore','Other country'];
const EXPERIENCE = ['Entry level / Fresher','Internship','Junior (1–3 years)','Mid level (3–5 years)','Senior (5+ years)','Any experience'];
const TYPES = ['Any','Full-time','Part-time','Contract','Internship'];

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('job_token') || '');
  const [member, setMember] = useState(null);
  const [authMode, setAuthMode] = useState('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [filters, setFilters] = useState(DEFAULTS);
  const [locationText, setLocationText] = useState(DEFAULTS.locations.join(', '));
  const [jobs, setJobs] = useState([]);
  const [saved, setSaved] = useState([]);
  const [savedName, setSavedName] = useState('My fresher job search');
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [warnings, setWarnings] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [resumeText, setResumeText] = useState('');

  const setField = (key, value) => setFilters(current => ({ ...current, [key]: value, page: 1 }));

  async function request(path, options = {}) {
    const response = await fetch(API + path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {})
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Request failed. Check the API and try again.');
    return data;
  }

  async function loadSaved(currentToken = token) {
    if (!currentToken) return;
    try {
      const response = await fetch(API + '/api/saved-searches', { headers: { Authorization: `Bearer ${currentToken}` } });
      if (response.ok) setSaved(await response.json());
    } catch { /* Saved searches are optional while the API is offline. */ }
  }

  useEffect(() => {
    if (!token) return;
    fetch(API + '/api/members/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { setMember(data); loadSaved(token); })
      .catch(() => { localStorage.removeItem('job_token'); setToken(''); setMember(null); });
  // Restore session once on load; token changes are handled by submitAuth.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitAuth(e) {
    e.preventDefault(); setError(''); setNotice(''); setAuthLoading(true);
    try {
      const data = await request('/api/members/' + authMode, { method: 'POST', body: JSON.stringify({ email, password }) });
      localStorage.setItem('job_token', data.access_token);
      setToken(data.access_token); setMember(data.member); await loadSaved(data.access_token);
      setNotice(authMode === 'register' ? 'Your account is ready. Welcome!' : 'You are signed in.');
    } catch (err) { setError(err.message); }
    finally { setAuthLoading(false); }
  }

  async function searchJobs(nextPage = 1) {
    setLoading(true); setError(''); setNotice(''); setWarnings([]);
    const locations = locationText.split(',').map(x => x.trim()).filter(Boolean);
    const payload = { ...filters, locations, page: nextPage, resume_text: resumeText };
    try {
      const data = await request('/api/global-jobs/search', { method: 'POST', body: JSON.stringify(payload) });
      setJobs(data.jobs || []); setPage(data.page || nextPage); setHasMore(Boolean(data.has_more)); setWarnings(data.warnings || []);
      if (!(data.jobs || []).length) setNotice('No matching jobs from the connected sources. Try Worldwide + Remote, widen your filters, or add an API source.');
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  async function saveCurrentSearch() {
    setError(''); setNotice('');
    try {
      const locations = locationText.split(',').map(x => x.trim()).filter(Boolean);
      await request('/api/saved-searches', { method: 'POST', body: JSON.stringify({ name: savedName, filters: { ...filters, locations, resume_text: resumeText, page: 1 } }) });
      await loadSaved(); setNotice('Search saved to your private account.');
    } catch (err) { setError(err.message); }
  }

  async function deleteSaved(id) {
    try { await request('/api/saved-searches/' + id, { method: 'DELETE' }); await loadSaved(); }
    catch (err) { setError(err.message); }
  }

  function restoreSearch(item) {
    const next = { ...DEFAULTS, ...item.filters };
    setFilters(next); setLocationText((next.locations || []).join(', ')); setResumeText(next.resume_text || '');
    setNotice('Saved filters restored. Click Find jobs to run the search.');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function logout() {
    localStorage.removeItem('job_token'); setToken(''); setMember(null); setSaved([]); setJobs([]);
    setNotice('You have signed out.');
  }

  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand" href="#"><span className="brand-icon">✳</span><span>Pathfinder<span className="brand-muted">.jobs</span></span></a>
        <div className="top-actions"><span className="global-pill"><span className="live-dot"/> Worldwide search</span>{member ? <><span className="member-email">{member.email}</span><button className="button button-quiet button-small" onClick={logout}>Sign out</button></> : <span className="member-email">Free member accounts</span>}</div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line"/> YOUR NEXT CHAPTER STARTS HERE</div>
            <h1>Find work that<br/><span>moves you forward.</span></h1>
            <p>Search jobs across countries, match roles to your skills, and keep every opportunity in one place.</p>
            <div className="hero-points"><span>✓ Free job discovery</span><span>✓ Resume matching</span><span>✓ Personal saved searches</span></div>
          </div>
          <div className="hero-art" aria-hidden="true"><div className="orb orb-one"/><div className="orb orb-two"/><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="planet">✳</div><div className="float-card float-card-top"><span className="mini-icon">↗</span><span><b>Go global</b><small>Opportunities everywhere</small></span></div><div className="float-card float-card-bottom"><span className="match-ring">92</span><span><b>Better matches</b><small>Skills meet opportunity</small></span></div></div>
        </section>

        {!member && <section className="auth-banner">
          <div className="auth-intro"><span className="auth-symbol">◎</span><div><b>Your own job-search workspace</b><p>Create a free account to save searches and keep your profile private.</p></div></div>
          <form className="auth-form" onSubmit={submitAuth}>
            <div className="auth-tabs"><button type="button" className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>Create account</button><button type="button" className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>Sign in</button></div>
            <div className="auth-fields"><input aria-label="Email" type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} required/><input aria-label="Password" type="password" placeholder="Password (8+ characters)" value={password} onChange={e => setPassword(e.target.value)} minLength={8} required/><button className="button button-dark" disabled={authLoading}>{authLoading ? 'Please wait…' : authMode === 'register' ? 'Join for free ↗' : 'Sign in ↗'}</button></div>
          </form>
        </section>}

        <section className="search-section" id="search">
          <div className="section-heading"><div><div className="eyebrow">SMART JOB DISCOVERY</div><h2>Build your search</h2><p>Set your preferences once. Search results link back to the original job posting.</p></div><div className="step-tag"><span>01</span> Search preferences</div></div>
          <div className="search-panel">
            <div className="field field-keyword"><label htmlFor="keyword">Job title or skills</label><div className="input-with-icon"><span>⌕</span><input id="keyword" value={filters.keyword} onChange={e => setField('keyword', e.target.value)} placeholder="Software Developer, Python…"/></div></div>
            <div className="field"><label htmlFor="country">Country</label><select id="country" value={filters.country} onChange={e => setField('country', e.target.value)}>{COUNTRIES.map(c => <option key={c}>{c}</option>)}</select></div>
            <div className="field field-location"><label htmlFor="locations">City or region <span className="label-note">comma separated</span></label><input id="locations" value={locationText} onChange={e => { setLocationText(e.target.value); setFilters(f => ({ ...f, page: 1 })); }} placeholder="Hyderabad, Bangalore, Chennai"/></div>
            <div className="field"><label htmlFor="experience">Experience level</label><select id="experience" value={filters.experience} onChange={e => setField('experience', e.target.value)}>{EXPERIENCE.map(x => <option key={x}>{x}</option>)}</select></div>
            <div className="field"><label htmlFor="workplace">Workplace</label><select id="workplace" value={filters.workplace} onChange={e => setField('workplace', e.target.value)}>{['Any','Remote','Hybrid','On-site'].map(x => <option key={x}>{x}</option>)}</select></div>
            <div className="field"><label htmlFor="type">Employment type</label><select id="type" value={filters.employment_type} onChange={e => setField('employment_type', e.target.value)}>{TYPES.map(x => <option key={x}>{x}</option>)}</select></div>
            <div className="field field-resume"><label htmlFor="resume">Resume text <span className="label-note">optional, for match scoring</span></label><textarea id="resume" rows="3" value={resumeText} onChange={e => setResumeText(e.target.value)} placeholder="Paste resume text or skills here, e.g. Python, SQL, React, CSE graduate…"/></div>
            <div className="search-actions"><span className="privacy-note"><span>♧</span> Resume text is used only for this search.</span><button className="button button-primary" onClick={() => searchJobs(1)} disabled={loading || !filters.keyword.trim()}>{loading ? <><span className="spinner"/> Searching…</> : <>Find matching jobs <span>↗</span></>}</button></div>
          </div>
        </section>

        {error && <div className="message message-error" role="alert"><b>Something needs attention</b><span>{error}</span></div>}
        {notice && <div className="message message-success" role="status"><span>✓</span>{notice}</div>}
        {warnings.map((warning, i) => <div className="message message-warning" key={i}>{warning}</div>)}

        <section className="results-section">
          <div className="results-heading"><div><div className="eyebrow">YOUR OPPORTUNITY FEED</div><h2>{jobs.length ? 'Matching opportunities' : 'Ready when you are'}</h2><p>{jobs.length ? 'Open the original listing to review details and apply.' : 'Run a search to see jobs from the connected sources.'}</p></div><div className="result-tools"><span className="source-tag"><span className="source-dot"/> Live source search</span></div></div>
          {jobs.length > 0 && <div className="save-search-bar"><div><b>Want to run this search again?</b><span>Save these filters to your member account.</span></div><input value={savedName} onChange={e => setSavedName(e.target.value)} aria-label="Saved search name"/><button className="button button-outline" onClick={saveCurrentSearch} disabled={!member}>＋ Save search</button>{!member && <small>Create an account above to save.</small>}</div>}
          {loading && <div className="loading-state"><span className="spinner spinner-dark"/><b>Looking across connected job sources…</b><span>Matching your location and experience preferences.</span></div>}
          {!loading && jobs.length > 0 && <div className="job-list">{jobs.map((job, i) => <article className="job-card" key={job.id || job.apply_url || i}>
            <div className="company-avatar">{(job.company || 'J').trim().slice(0,1).toUpperCase()}</div><div className="job-main"><div className="job-topline"><h3>{job.title}</h3>{job.match_score > 0 && <span className="match-badge">{job.match_score}% resume match</span>}</div><div className="company-name">{job.company}</div><div className="job-meta"><span>⌖ {job.location || 'Location not specified'}</span><span>◷ {job.employment_type || 'Type not specified'}</span><span>◉ {job.seniority || 'Experience not specified'}</span></div><p className="job-description">{(job.summary || '').replace(/<[^>]*>/g, ' ').slice(0, 230)}{(job.summary || '').length > 230 ? '…' : ''}</p><div className="job-foot"><span className="source-label">Source: {job.source}</span><span className="salary-label">{job.salary && job.salary !== 'Not disclosed' ? job.salary : 'Salary not disclosed'}</span></div></div><div className="job-apply">{job.apply_url && <a className="button button-dark" href={job.apply_url} target="_blank" rel="noopener noreferrer">View & apply ↗</a>}{job.source_url && <a className="source-link" href={job.source_url} target="_blank" rel="noopener noreferrer">About source ↗</a>}</div>
          </article>)}</div>}
          {!loading && jobs.length > 0 && <div className="pagination"><span>Page {page} · {jobs.length} listings shown</span><div><button className="button button-outline" disabled={page <= 1 || loading} onClick={() => searchJobs(page - 1)}>← Previous</button><button className="button button-outline" disabled={!hasMore || loading} onClick={() => searchJobs(page + 1)}>Next page →</button></div></div>}
          {!loading && jobs.length === 0 && <div className="empty-state"><div className="empty-icon">⌕</div><b>Your next opportunity is out there.</b><span>Choose your filters and search to discover roles from connected job sources.</span><button className="button button-outline" onClick={() => { setFilters(DEFAULTS); setLocationText(DEFAULTS.locations.join(', ')); setResumeText(''); }}>Reset to suggested search</button></div>}
        </section>

        <section className="saved-section"><div className="saved-header"><div><div className="eyebrow">YOUR PERSONAL SHORTCUTS</div><h2>Saved searches</h2><p>Private to your account. Pick up where you left off.</p></div><span className="saved-count">{saved.length} saved</span></div>{!member ? <div className="saved-empty">Sign in or create a free account to save and revisit your searches.</div> : saved.length === 0 ? <div className="saved-empty">No saved searches yet. Run a search, then select “Save search”.</div> : <div className="saved-grid">{saved.map(item => <article className="saved-card" key={item.id}><div className="saved-card-icon">↗</div><div className="saved-card-content"><b>{item.name}</b><span>{item.filters.keyword} · {item.filters.country}</span><small>{(item.filters.locations || []).join(', ') || 'Any location'} · {item.filters.experience}</small></div><button className="button button-outline button-small" onClick={() => restoreSearch(item)}>Restore</button><button className="delete-button" title="Delete saved search" aria-label={'Delete ' + item.name} onClick={() => deleteSaved(item.id)}>×</button></article>)}</div>}</section>
      </main>
      <footer><a className="brand footer-brand" href="#"><span className="brand-icon">✳</span><span>Pathfinder<span className="brand-muted">.jobs</span></span></a><span>Built to make the job search feel more human.</span><span>Listings belong to their original publishers.</span></footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
