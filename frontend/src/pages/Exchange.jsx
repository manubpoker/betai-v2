import { useState, useEffect, useCallback } from 'react'
import SportsSidebar from '../components/SportsSidebar'
import OddsGrid from '../components/OddsGrid'
import BetSlip from '../components/BetSlip'
import AIChatPanel from '../components/AIChatPanel'
import BetHistory from '../components/BetHistory'
import { API_BASE } from '../config'

const EVENTS_PER_PAGE = 20
const AUTO_REFRESH_INTERVAL = 60000 // 60 seconds

export default function Exchange({ balance, onBalanceChange }) {
  const [sports, setSports] = useState([])
  const [selectedSport, setSelectedSport] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [betSlip, setBetSlip] = useState([])

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  // Scrape status state
  const [scrapeStatus, setScrapeStatus] = useState(null)

  // AI Chat state for Match Intelligence
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatInitialMessage, setChatInitialMessage] = useState(null)
  const [chatEventContext, setChatEventContext] = useState(null)

  // Bet History modal state
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)

  // Deep Research state
  const [deepResearchEvent, setDeepResearchEvent] = useState(null)
  const [deepResearchLoading, setDeepResearchLoading] = useState(false)
  const [deepResearchResult, setDeepResearchResult] = useState(null)
  const [deepResearchError, setDeepResearchError] = useState(null)

  // Fetch sports list
  useEffect(() => {
    async function fetchSports() {
      try {
        const res = await fetch(`${API_BASE}/api/sports`)
        const data = await res.json()
        setSports(data)
        if (data.length > 0 && !selectedSport) {
          setSelectedSport(data[0].name || data[0].sport)
        }
      } catch (err) {
        console.error('Error fetching sports:', err)
      }
    }
    fetchSports()
  }, [])

  // Fetch events function - memoized for reuse
  const fetchEvents = useCallback(async (silent = false) => {
    if (!selectedSport) return

    if (!silent) setLoading(true)
    try {
      const url = selectedSport
        ? `${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}&data_type=exchange`
        : `${API_BASE}/api/events?data_type=exchange`
      const res = await fetch(url)
      const data = await res.json()
      setEvents(data)

      // Calculate pagination
      setTotalPages(Math.max(1, Math.ceil(data.length / EVENTS_PER_PAGE)))

      // Set last updated time
      if (data.length > 0) {
        const newest = data.reduce((a, b) =>
          new Date(a.scraped_at) > new Date(b.scraped_at) ? a : b
        )
        setLastUpdated(new Date(newest.scraped_at))
      }
    } catch (err) {
      console.error('Error fetching events:', err)
    } finally {
      if (!silent) setLoading(false)
    }
  }, [selectedSport])

  // Fetch scrape status
  const fetchScrapeStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/status`)
      const data = await res.json()
      setScrapeStatus(data)

      // If data is fresh and we have new events, auto-refresh
      if (data.freshness && data.freshness.age_seconds < 120) {
        // Data was updated within last 2 minutes, refresh silently
        fetchEvents(true)
      }
    } catch (err) {
      console.error('Error fetching scrape status:', err)
    }
  }, [fetchEvents])

  // Fetch events when sport changes
  useEffect(() => {
    setCurrentPage(1) // Reset to page 1 when sport changes
    fetchEvents()
  }, [selectedSport, fetchEvents])

  // Auto-refresh events periodically
  useEffect(() => {
    const interval = setInterval(() => {
      fetchScrapeStatus()
    }, AUTO_REFRESH_INTERVAL)

    // Initial fetch
    fetchScrapeStatus()

    return () => clearInterval(interval)
  }, [fetchScrapeStatus])

  // Get paginated events
  const paginatedEvents = events.slice(
    (currentPage - 1) * EVENTS_PER_PAGE,
    currentPage * EVENTS_PER_PAGE
  )

  // Add selection to bet slip
  const addToBetSlip = (event, selection, odds, type) => {
    const newBet = {
      id: `${event.id}-${selection}-${type}`,
      eventId: event.id,
      eventName: event.event_name,
      selection,
      odds,
      type,
      stake: '',
    }

    if (!betSlip.find(b => b.id === newBet.id)) {
      setBetSlip([...betSlip, newBet])
    }
  }

  // Remove from bet slip
  const removeFromBetSlip = (id) => {
    setBetSlip(betSlip.filter(b => b.id !== id))
  }

  // Update stake in bet slip
  const updateStake = (id, stake) => {
    setBetSlip(betSlip.map(b =>
      b.id === id ? { ...b, stake } : b
    ))
  }

  // Clear bet slip
  const clearBetSlip = () => {
    setBetSlip([])
  }

  // Handle Match Intelligence
  const handleMatchIntelligence = async (event, odds = []) => {
    const currentOdds = odds.map(o => ({
      selection: o.selection_name,
      back_odds: o.back_odds,
      lay_odds: o.lay_odds
    }))

    // Build a detailed research message with all available context
    const today = new Date().toISOString().split('T')[0]
    const statusText = event.is_live === 1 ? 'LIVE NOW' : `Scheduled: ${event.start_time || 'TBD'}`
    const oddsText = currentOdds.length > 0
      ? currentOdds.map(o => `${o.selection}: Back ${o.back_odds?.toFixed(2) || '-'}, Lay ${o.lay_odds?.toFixed(2) || '-'}`).join('; ')
      : 'No odds available'

    const message = `Research value bets for this match:

**Match:** ${event.event_name}
**Sport:** ${event.sport}
**Competition:** ${event.competition || 'Unknown'}
**Status:** ${statusText}
**Today's Date:** ${today}
**Current Odds:** ${oddsText}

Analyze recent form, head-to-head, team news, and identify any value betting opportunities.`

    const context = {
      event_id: event.id,
      event_name: event.event_name,
      sport: event.sport,
      competition: event.competition,
      is_live: event.is_live,
      start_time: event.start_time,
      research_date: today,
      current_odds_from_page: currentOdds,
      note: "IMPORTANT: Use current_odds_from_page as the authoritative odds source. Research date is " + today + "."
    }
    setChatInitialMessage(message)
    setChatEventContext(context)
    setIsChatOpen(true)
  }

  // Handle Deep Research with Gemini
  const handleDeepResearch = async (event) => {
    // Confirm with user due to cost
    const confirmed = window.confirm(
      `Run Gemini Deep Research on "${event.event_name}"?\n\nThis will cost approximately £2 and may take up to 5 minutes.\n\nProceed?`
    )

    if (!confirmed) return

    setDeepResearchEvent(event)
    setDeepResearchLoading(true)
    setDeepResearchResult(null)
    setDeepResearchError(null)

    try {
      const res = await fetch(`${API_BASE}/api/ai/deep-research/${event.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await res.json()

      if (data.success) {
        setDeepResearchResult(data)
      } else {
        setDeepResearchError(data.error || 'Research failed')
      }
    } catch (err) {
      console.error('Deep research error:', err)
      setDeepResearchError('Failed to connect to server')
    } finally {
      setDeepResearchLoading(false)
    }
  }

  // Close deep research modal
  const closeDeepResearch = () => {
    setDeepResearchEvent(null)
    setDeepResearchLoading(false)
    setDeepResearchResult(null)
    setDeepResearchError(null)
  }

  // Format last updated time
  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Never'
    const now = new Date()
    const diff = Math.round((now - lastUpdated) / 60000)
    if (diff < 1) return 'Just now'
    if (diff === 1) return '1 min ago'
    return `${diff} mins ago`
  }

  // Scraping state
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState(null)

  // Refresh odds by triggering an exchange scrape only
  const handleRefreshOdds = async () => {
    setIsRefreshing(true)
    setRefreshError(null)
    try {
      const res = await fetch(`${API_BASE}/api/scrape/trigger?data_type=exchange`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        await fetchEvents()
        await fetchScrapeStatus()
      } else {
        setRefreshError(data.error || 'Scrape failed')
      }
    } catch (err) {
      setRefreshError('Failed to connect to server')
      console.error('Refresh error:', err)
    } finally {
      setIsRefreshing(false)
    }
  }

  // Pagination component - Betfair style
  const Pagination = () => {
    if (totalPages <= 1) return null

    const pages = []
    const maxVisiblePages = 7

    // Calculate visible page range
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2))
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1)

    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1)
    }

    // First page
    if (startPage > 1) {
      pages.push(
        <button
          key={1}
          onClick={() => setCurrentPage(1)}
          className="px-3 py-1 text-sm border border-gray-300 bg-white hover:bg-gray-50 text-betfair-black"
        >
          1
        </button>
      )
      if (startPage > 2) {
        pages.push(<span key="ellipsis1" className="px-2 text-gray-400">...</span>)
      }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => setCurrentPage(i)}
          className={`px-3 py-1 text-sm border ${
            i === currentPage
              ? 'bg-betfair-yellow border-betfair-yellow text-betfair-black font-bold'
              : 'border-gray-300 bg-white hover:bg-gray-50 text-betfair-black'
          }`}
        >
          {i}
        </button>
      )
    }

    // Last page
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push(<span key="ellipsis2" className="px-2 text-gray-400">...</span>)
      }
      pages.push(
        <button
          key={totalPages}
          onClick={() => setCurrentPage(totalPages)}
          className="px-3 py-1 text-sm border border-gray-300 bg-white hover:bg-gray-50 text-betfair-black"
        >
          {totalPages}
        </button>
      )
    }

    return (
      <div className="flex items-center justify-center gap-1 py-3">
        <button
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="px-3 py-1 text-sm border border-gray-300 bg-white hover:bg-gray-50 text-betfair-black disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Prev
        </button>
        {pages}
        <button
          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages}
          className="px-3 py-1 text-sm border border-gray-300 bg-white hover:bg-gray-50 text-betfair-black disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    )
  }

  return (
    <div className="flex gap-4">
      {/* Sports Sidebar */}
      <div className="w-52 flex-shrink-0">
        <SportsSidebar
          sports={sports}
          selected={selectedSport}
          onSelect={setSelectedSport}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {/* Market Header */}
        <div className="bf-card mb-4">
          <div className="bg-betfair-dark px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-white">
                {selectedSport || 'All Sports'}
              </h1>
              <span className="text-sm text-white/70">
                {events.length} markets
              </span>
              {scrapeStatus?.freshness?.is_fresh && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500 text-white">
                  LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-white/70">
                Updated: {formatLastUpdated()}
              </span>
              <button
                onClick={() => setIsHistoryOpen(true)}
                className="px-3 py-1.5 text-sm font-medium bg-white/10 text-white rounded hover:bg-white/20 transition-colors"
              >
                My Bets
              </button>
              <button
                onClick={handleRefreshOdds}
                disabled={isRefreshing}
                className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                  isRefreshing
                    ? 'bg-gray-500 text-white cursor-not-allowed'
                    : 'bg-betfair-yellow text-betfair-black hover:brightness-95'
                }`}
              >
                {isRefreshing ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Refreshing
                  </span>
                ) : (
                  'Refresh'
                )}
              </button>
            </div>
          </div>
        </div>

        {refreshError && (
          <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
            {refreshError}
          </div>
        )}

        {/* Pagination - Top */}
        {totalPages > 1 && <Pagination />}

        {/* Odds Grid */}
        {loading ? (
          <div className="bf-card flex items-center justify-center h-64">
            <div className="text-betfair-gray loading-pulse">Loading markets...</div>
          </div>
        ) : events.length === 0 ? (
          <div className="bf-card text-center py-12">
            <p className="text-betfair-gray">No markets available for {selectedSport}</p>
            <p className="text-sm text-gray-400 mt-2">Data is scraped from Betfair Exchange</p>
            <button
              onClick={handleRefreshOdds}
              className="mt-4 bf-btn-primary"
            >
              Refresh Data
            </button>
          </div>
        ) : (
          <OddsGrid
            events={paginatedEvents}
            onSelectOdds={addToBetSlip}
            betSlip={betSlip}
            onMatchIntelligence={handleMatchIntelligence}
            onDeepResearch={handleDeepResearch}
          />
        )}

        {/* Pagination - Bottom */}
        {totalPages > 1 && <Pagination />}
      </div>

      {/* Bet Slip */}
      <div className="w-72 flex-shrink-0">
        <BetSlip
          bets={betSlip}
          onRemove={removeFromBetSlip}
          onUpdateStake={updateStake}
          onClear={clearBetSlip}
          balance={balance}
          onBalanceChange={onBalanceChange}
        />
      </div>

      {/* AI Chat Panel for Match Intelligence */}
      <AIChatPanel
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false)
          setChatInitialMessage(null)
          setChatEventContext(null)
        }}
        initialMessage={chatInitialMessage}
        eventContext={chatEventContext}
      />

      {/* Bet History Modal */}
      <BetHistory
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
      />

      {/* Deep Research Modal */}
      {deepResearchEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="bg-betfair-dark px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Deep Research</h2>
                <p className="text-sm text-white/70">{deepResearchEvent.event_name}</p>
              </div>
              <button
                onClick={closeDeepResearch}
                className="text-white/70 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {deepResearchLoading && (
                <div className="flex flex-col items-center justify-center py-12">
                  <svg className="animate-spin h-12 w-12 text-amber-600 mb-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-lg font-medium text-betfair-black">Gemini Deep Research in progress...</p>
                  <p className="text-sm text-betfair-gray mt-2">This may take up to 5 minutes. Please wait.</p>
                  <p className="text-xs text-amber-600 mt-4">Analyzing team form, injuries, head-to-head, weather, and more...</p>
                </div>
              )}

              {deepResearchError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                  <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-lg font-medium text-red-800">Research Failed</h3>
                  <p className="text-sm text-red-600 mt-2">{deepResearchError}</p>
                  <button
                    onClick={closeDeepResearch}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Close
                  </button>
                </div>
              )}

              {deepResearchResult && (
                <div className="space-y-6">
                  {/* Success indicator */}
                  <div className="flex items-center gap-3 pb-4 border-b border-gray-200">
                    <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="font-medium text-betfair-black">Research Complete</p>
                      <p className="text-xs text-betfair-gray">Powered by Gemini Deep Research</p>
                    </div>
                  </div>

                  {/* Research content */}
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-betfair-black leading-relaxed">
                      {deepResearchResult.research}
                    </div>
                  </div>

                  {/* Sources if available */}
                  {deepResearchResult.sources && deepResearchResult.sources.length > 0 && (
                    <div className="mt-6 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-semibold text-betfair-gray mb-2">Sources</h4>
                      <ul className="text-xs text-betfair-gray space-y-1">
                        {deepResearchResult.sources.map((source, i) => (
                          <li key={i}>
                            <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-ai-accent hover:underline">
                              {source.title || source.url}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {!deepResearchLoading && (
              <div className="border-t border-gray-200 px-6 py-4 flex justify-end">
                <button
                  onClick={closeDeepResearch}
                  className="px-4 py-2 bg-betfair-yellow text-betfair-black font-medium rounded hover:brightness-95"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
