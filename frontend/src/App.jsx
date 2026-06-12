import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Sparkles, 
  BookOpen, 
  Filter, 
  Globe, 
  Calendar, 
  Briefcase, 
  Server, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight,
  ChevronRight,
  Database
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Pre-defined fallback suggestions to help the user test the RAG easily
const SUGGESTIONS = [
  "audit financier banque mondiale",
  "TDR consultant juridique mali",
  "cadre politique de reinstallation mauritanie",
  "recrutement expert formation entrepreneuriat"
];

function App() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('ask'); // 'search' | 'ask' | 'agent-ask'
  const [isLoading, setIsLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(null);
  
  // Response states
  const [searchResponse, setSearchResponse] = useState(null);
  const [askResponse, setAskResponse] = useState(null);
  const [agentResponse, setAgentResponse] = useState(null);
  
  // Selected Filter States
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [selectedYears, setSelectedYears] = useState([]);
  
  // Unique filter values derived from active results
  const [availableFilters, setAvailableFilters] = useState({
    domains: [],
    countries: [],
    years: []
  });

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_URL}/health`);
        const data = await res.json();
        setApiOnline(data.status === 'ok');
      } catch (err) {
        setApiOnline(false);
      }
    };
    checkHealth();
  }, []);

  // Utility to extract Country, Domain, and Year from source document filename or content
  const extractMetadata = (filename, content = '') => {
    const name = filename.toLowerCase();
    const text = content.toLowerCase();
    
    // 1. Extract Year
    let year = "Non spécifié";
    const yearMatch = filename.match(/\b(20\d{2})\b/) || content.match(/\b(20\d{2})\b/);
    if (yearMatch) {
      year = yearMatch[1];
    } else if (name.includes("2025") || text.includes("2025")) {
      year = "2025";
    } else if (name.includes("2024") || text.includes("2024")) {
      year = "2024";
    } else if (name.includes("2023") || name.includes("23") || text.includes("2023")) {
      year = "2023";
    } else if (name.includes("2022") || name.includes("22") || text.includes("2022")) {
      year = "2022";
    } else if (name.includes("2019") || text.includes("2019")) {
      year = "2019";
    } else if (name.includes("2016") || text.includes("2016")) {
      year = "2016";
    }

    // 2. Extract Country
    let country = "Afrique / Int.";
    if (name.includes("mali") || text.includes("mali")) {
      country = "Mali";
    } else if (name.includes("mauritanie") || text.includes("mauritanie") || name.includes("onmp")) {
      country = "Mauritanie";
    } else if (name.includes("rca") || name.includes("centrafrique") || text.includes("centrafrique")) {
      country = "RCA";
    } else if (name.includes("belgique") || name.includes("be_") || text.includes("belgique")) {
      country = "Belgique";
    } else if (name.includes("tunisie") || name.includes("esct") || name.includes("fshst") || text.includes("tunisie")) {
      country = "Tunisie";
    } else if (name.includes("maroc") || name.includes("rabat") || text.includes("maroc")) {
      country = "Maroc";
    } else if (name.includes("china") || text.includes("chine")) {
      country = "Chine";
    }

    // 3. Extract Domain
    let domain = "Général";
    if (name.includes("audit") || name.includes("auditeur") || name.includes("financier") || name.includes("comptable") || name.includes("finance") || text.includes("audit") || text.includes("financier")) {
      domain = "Audit & Finance";
    } else if (name.includes("juridique") || name.includes("loi") || name.includes("contrat") || name.includes("droit") || text.includes("juridique") || text.includes("convention")) {
      domain = "Juridique";
    } else if (name.includes("evaluation") || name.includes("eval") || name.includes("rapport") || name.includes("constatations") || text.includes("evaluation")) {
      domain = "Évaluation & Suivi";
    } else if (name.includes("erp") || name.includes("siade") || name.includes("si_") || name.includes("tech") || name.includes("communication") || text.includes("logiciel") || text.includes("technologie")) {
      domain = "Technique & IT";
    } else if (name.includes("local") || name.includes("environnement") || name.includes("social") || name.includes("reinstallation") || name.includes("sauvegarde") || text.includes("environnemental") || text.includes("social")) {
      domain = "Social & Environnemental";
    } else if (name.includes("entrepreneuriat") || name.includes("formation") || name.includes("expert") || name.includes("consultant") || text.includes("formation") || text.includes("consultant")) {
      domain = "Conseil & Formation";
    }

    return { year, country, domain };
  };

  const handleSuggestionClick = (suggestionText) => {
    setQuery(suggestionText);
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setSearchResponse(null);
    setAskResponse(null);
    setAgentResponse(null);
    
    // Clear filters
    setSelectedDomains([]);
    setSelectedCountries([]);
    setSelectedYears([]);

    try {
      if (mode === 'search') {
        const res = await fetch(`${API_URL}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, limit: 8 })
        });
        const data = await res.json();
        
        // Enrich data with metadata
        const enrichedResults = (data.results || []).map(r => ({
          ...r,
          metadata: extractMetadata(r.source, r.parent_content)
        }));
        
        setSearchResponse({ ...data, results: enrichedResults });
        updateFilterCheckboxes(enrichedResults);
      } 
      else if (mode === 'ask') {
        const res = await fetch(`${API_URL}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, limit: 6 })
        });
        const data = await res.json();
        
        // Enrich sources with metadata
        const enrichedSources = (data.sources || []).map(s => ({
          ...s,
          // Since /ask response is slightly different, retrieve parent_content if matches
          metadata: extractMetadata(s.source, '')
        }));
        
        setAskResponse({ ...data, sources: enrichedSources });
        updateFilterCheckboxes(enrichedSources);
      } 
      else if (mode === 'agent-ask') {
        const res = await fetch(`${API_URL}/agent-ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const data = await res.json();
        
        setAgentResponse(data);
      }
    } catch (err) {
      console.error("Erreur de requête API:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const updateFilterCheckboxes = (items) => {
    const domains = [...new Set(items.map(item => item.metadata.domain))].filter(Boolean);
    const countries = [...new Set(items.map(item => item.metadata.country))].filter(Boolean);
    const years = [...new Set(items.map(item => item.metadata.year))].filter(Boolean);
    
    setAvailableFilters({ domains, countries, years });
  };

  const toggleFilter = (type, value) => {
    if (type === 'domain') {
      setSelectedDomains(prev => 
        prev.includes(value) ? prev.filter(v => v !== value) : [...prev, value]
      );
    } else if (type === 'country') {
      setSelectedCountries(prev => 
        prev.includes(value) ? prev.filter(v => v !== value) : [...prev, value]
      );
    } else if (type === 'year') {
      setSelectedYears(prev => 
        prev.includes(value) ? prev.filter(v => v !== value) : [...prev, value]
      );
    }
  };

  // Filter application helper
  const getFilteredItems = (items = []) => {
    return items.filter(item => {
      const matchDomain = selectedDomains.length === 0 || selectedDomains.includes(item.metadata.domain);
      const matchCountry = selectedCountries.length === 0 || selectedCountries.includes(item.metadata.country);
      const matchYear = selectedYears.length === 0 || selectedYears.includes(item.metadata.year);
      return matchDomain && matchCountry && matchYear;
    });
  };

  // Determine active display elements
  const showWelcome = !isLoading && !searchResponse && !askResponse && !agentResponse;
  
  // Filtered lists
  const filteredSearchResults = searchResponse ? getFilteredItems(searchResponse.results) : [];
  const filteredAskSources = askResponse ? getFilteredItems(askResponse.sources) : [];

  return (
    <div className="app-container">
      {/* EY Corporate Header */}
      <header className="app-header">
        <div className="header-logo">
          <div className="ey-logo-badge">EY</div>
          <div className="header-title">
            <h1>Agentic RAG - Termes de Référence</h1>
            <p>EY Global Government & Public Sector Services</p>
          </div>
        </div>
        
        <div className="api-status">
          <Server size={14} />
          <span>API Backend :</span>
          <span className={`status-dot ${apiOnline ? 'online' : ''}`}></span>
          <span>{apiOnline === null ? 'Vérification...' : apiOnline ? 'Connecté' : 'Hors ligne'}</span>
        </div>
      </header>

      {/* Dashboard Layout */}
      <div className="dashboard-layout">
        {/* Sidebar Filters */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3><Filter size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Filtres Documents</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--ey-medium-grey)', marginBottom: '1rem' }}>
              Filtrez dynamiquement les sources trouvées par le RAG.
            </p>
          </div>

          {/* Domain Filter */}
          <div className="sidebar-section">
            <h3><Briefcase size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Domaine</h3>
            <div className="filter-group">
              {availableFilters.domains.length === 0 ? (
                <span style={{ fontSize: '0.85rem', color: 'var(--ey-medium-grey)', fontStyle: 'italic' }}>Aucun domaine détecté</span>
              ) : (
                availableFilters.domains.map(domain => (
                  <label key={domain} className="filter-checkbox-label">
                    <input 
                      type="checkbox" 
                      className="filter-checkbox"
                      checked={selectedDomains.includes(domain)}
                      onChange={() => toggleFilter('domain', domain)}
                    />
                    {domain}
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Country Filter */}
          <div className="sidebar-section">
            <h3><Globe size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Pays</h3>
            <div className="filter-group">
              {availableFilters.countries.length === 0 ? (
                <span style={{ fontSize: '0.85rem', color: 'var(--ey-medium-grey)', fontStyle: 'italic' }}>Aucun pays détecté</span>
              ) : (
                availableFilters.countries.map(country => (
                  <label key={country} className="filter-checkbox-label">
                    <input 
                      type="checkbox" 
                      className="filter-checkbox"
                      checked={selectedCountries.includes(country)}
                      onChange={() => toggleFilter('country', country)}
                    />
                    {country}
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Date / Year Filter */}
          <div className="sidebar-section">
            <h3><Calendar size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Année</h3>
            <div className="filter-group">
              {availableFilters.years.length === 0 ? (
                <span style={{ fontSize: '0.85rem', color: 'var(--ey-medium-grey)', fontStyle: 'italic' }}>Aucune année détectée</span>
              ) : (
                availableFilters.years.map(year => (
                  <label key={year} className="filter-checkbox-label">
                    <input 
                      type="checkbox" 
                      className="filter-checkbox"
                      checked={selectedYears.includes(year)}
                      onChange={() => toggleFilter('year', year)}
                    />
                    {year}
                  </label>
                ))
              )}
            </div>
          </div>

          <div style={{ marginTop: 'auto', fontSize: '0.75rem', color: 'var(--ey-medium-grey)', borderTop: '1px solid var(--ey-border-color)', paddingTop: '1rem' }}>
            <span>Architecture RAG Parent/Child • Qdrant Vector DB • Ollama Llama 3.2</span>
          </div>
        </aside>

        {/* Main Workspace */}
        <main className="main-content">
          {/* Query Bar Container */}
          <div className="query-container">
            {/* Mode Selectors */}
            <div className="mode-selector">
              <button 
                className={`mode-btn ${mode === 'ask' ? 'active' : ''}`}
                onClick={() => setMode('ask')}
              >
                <BookOpen size={14} />
                <span>RAG Simple</span>
              </button>
              
              <button 
                className={`mode-btn ${mode === 'agent-ask' ? 'active' : ''}`}
                onClick={() => setMode('agent-ask')}
              >
                <Sparkles size={14} />
                <span>RAG Agentic</span>
                <span className="mode-badge agent">LangGraph</span>
              </button>

              <button 
                className={`mode-btn ${mode === 'search' ? 'active' : ''}`}
                onClick={() => setMode('search')}
              >
                <Database size={14} />
                <span>Moteur Vectoriel</span>
              </button>
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="search-input-wrapper">
              <input 
                type="text" 
                className="search-input"
                placeholder={
                  mode === 'agent-ask' 
                    ? "Posez une question complexe à l'agent (réécriture de requête)..." 
                    : mode === 'ask' 
                    ? "Posez votre question sur les Termes de Référence..." 
                    : "Recherchez directement des passages et chunks de documents..."
                }
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isLoading}
              />
              <button 
                type="submit" 
                className="submit-btn" 
                disabled={isLoading || !query.trim()}
              >
                <span>Analyser</span>
                <ArrowRight size={16} />
              </button>
            </form>
          </div>

          {/* Results Display Area */}
          <div className="results-workspace">
            
            {/* Welcome State */}
            {showWelcome && (
              <div className="welcome-screen">
                <div className="welcome-icon-wrapper">
                  <Database size={48} color="var(--ey-black)" />
                </div>
                <h2>Analyseur de Termes de Référence</h2>
                <p>
                  Interrogez intelligemment les appels d'offres et TdR au format PDF grâce à notre système RAG avec indexation Parent/Child.
                </p>
                
                <div style={{ width: '100%', borderBottom: '1px solid var(--ey-border-color)', margin: '1rem 0' }}></div>
                
                <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>Suggestions de recherche :</p>
                <div className="suggestion-chips">
                  {SUGGESTIONS.map((s, idx) => (
                    <button 
                      key={idx} 
                      className="suggestion-chip"
                      onClick={() => handleSuggestionClick(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="loading-card">
                <div className="spinner"></div>
                <p style={{ fontWeight: 600 }}>Analyse documentaire en cours...</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--ey-medium-grey)' }}>
                  {mode === 'agent-ask' 
                    ? "L'agent réécrit la requête et formule une réponse structurée..." 
                    : "Interrogation de la base vectorielle et synthèse de contexte..."}
                </p>
              </div>
            )}

            {/* Mode Simple Ask / RAG Response */}
            {!isLoading && askResponse && (
              <>
                <div className="answer-card">
                  <div className="answer-header">
                    <span className="answer-title"><BookOpen size={16} color="var(--ey-black)" /> Synthèse Documentaire</span>
                  </div>
                  <div className="answer-body">{askResponse.answer}</div>
                </div>

                <div className="section-title">
                  <Database size={16} />
                  <span>Sources et passages clés consultés ({filteredAskSources.length} affichés)</span>
                </div>

                {filteredAskSources.length === 0 ? (
                  <div className="empty-results">
                    Aucun document ne correspond aux filtres sélectionnés. Désactivez certains filtres pour voir les sources.
                  </div>
                ) : (
                  <div className="chunks-grid">
                    {filteredAskSources.map((source, index) => (
                      <div key={index} className="chunk-card">
                        <div className="chunk-header">
                          <span className="chunk-source">
                            <ChevronRight size={14} />
                            {source.source}
                          </span>
                          <div className="chunk-badges">
                            <span className="badge badge-domain">{source.metadata.domain}</span>
                            <span className="badge badge-country">{source.metadata.country}</span>
                            <span className="badge badge-year">{source.metadata.year}</span>
                          </div>
                          <div className="chunk-score-wrapper">
                            <div className="score-bar-bg">
                              <div className="score-bar-fill" style={{ width: `${Math.min(100, source.score * 100)}%` }}></div>
                            </div>
                            <span className="score-value">Score : {(source.score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <div className="chunk-body">
                          <div className="chunk-id">ID du document parent : {source.parent_id}</div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--ey-medium-grey)', fontStyle: 'italic' }}>
                            Contexte extrait du document parent lié au vecteur sélectionné.
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Mode Agentic Ask Response */}
            {!isLoading && agentResponse && (
              <>
                <div className="answer-card" style={{ borderLeftColor: 'var(--ey-black)' }}>
                  <div className="answer-header">
                    <span className="answer-title" style={{ color: 'var(--ey-black)' }}>
                      <Sparkles size={16} color="var(--ey-yellow)" style={{ fill: 'var(--ey-yellow)' }} /> 
                      Analyse Agentic RAG (LangGraph)
                    </span>
                  </div>
                  <div className="answer-body">{agentResponse.answer}</div>
                </div>

                <div className="query-rewrite-info">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <CheckCircle2 size={14} color="var(--ey-black)" />
                    <span>
                      Requête initiale analysée. L'agent a consulté un total de <strong>{agentResponse.sources_count} documents parents</strong> pertinents dans la base Qdrant.
                    </span>
                  </span>
                </div>
              </>
            )}

            {/* Mode Direct Vector Search Response */}
            {!isLoading && searchResponse && (
              <>
                <div className="section-title">
                  <Database size={16} />
                  <span>Morceaux de documents (Chunks) pertinents ({filteredSearchResults.length} affichés)</span>
                </div>

                {filteredSearchResults.length === 0 ? (
                  <div className="empty-results">
                    Aucun chunk ne correspond aux filtres sélectionnés.
                  </div>
                ) : (
                  <div className="chunks-grid">
                    {filteredSearchResults.map((result, index) => (
                      <div key={index} className="chunk-card">
                        <div className="chunk-header">
                          <span className="chunk-source">
                            <ChevronRight size={14} />
                            {result.source}
                          </span>
                          <div className="chunk-badges">
                            <span className="badge badge-domain">{result.metadata.domain}</span>
                            <span className="badge badge-country">{result.metadata.country}</span>
                            <span className="badge badge-year">{result.metadata.year}</span>
                          </div>
                          <div className="chunk-score-wrapper">
                            <div className="score-bar-bg">
                              <div className="score-bar-fill" style={{ width: `${Math.min(100, result.score * 100)}%` }}></div>
                            </div>
                            <span className="score-value">Score : {(result.score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <div className="chunk-body">
                          <div className="chunk-id">Parent ID : {result.parent_id}</div>
                          <div className="chunk-content">{result.parent_content}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
