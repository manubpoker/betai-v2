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
    const message = `Research value bets for "${event.event_name}" (${event.sport}).`
    const currentOdds = odds.map(o => ({
      selection: o.selection_name,
      back_odds: o.back_odds,
      lay_odds: o.lay_odds
    }))

    const context = {
      event_id: event.id,
      event_name: event.event_name,
      sport: event.sport,
      competition: event.competition,
      is_live: event.is_live,
      start_time: event.start_time,
      current_odds_from_page: currentOdds,
      note: "IMPORTANT: Use current_odds_from_page as the authoritative odds source."
    }
    setChatInitialMessage(message)
    setChatEventContext(context)
    setIsChatOpen(true)
  }

  // Format last updated time
  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Never'
    const now = new Date()
    const diff = Math.round((now - lastUpdated) / 60000)
    if (diff < 1) return 'Just now'
    if (diff === 1) return '1 minute ago'
    return `${diff} minutes ago`
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

  // Pagination component
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
          className="px-3 py-1 rounded bg-gray-700 text-white hover:bg-gray-600"
        >
          1
        </button>
      )
      if (startPage > 2) {
        pages.push(<span key="ellipsis1" className="px-2 text-gray-500">...</span>)
      }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => setCurrentPage(i)}
          className={`px-3 py-1 rounded ${
            i === currentPage
              ? 'bg-betfair-gold text-dark-navy font-bold'
              : 'bg-gray-700 text-white hover:bg-gray-600'
          }`}
        >
          {i}
        </button>
      )
    }

    // Last page
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push(<span key="ellipsis2" className="px-2 text-gray-500">...</span>)
      }
      pages.push(
        <button
          key={totalPages}
          onClick={() => setCurrentPage(totalPages)}
          className="px-3 py-1 rounded bg-gray-700 text-white hover:bg-gray-600"
        >
          {totalPages}
        </button>
      )
    }

    return (
      <div className="flex items-center justify-center gap-2 mt-6 mb-4">
        <button
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="px-3 py-1 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          &lt;
        </button>
        {pages}
        <button
          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages}
          className="px-3 py-1 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          &gt;
        </button>
      </div>
    )
  }

  return (
    <div className="flex gap-6">
      {/* Sports Sidebar */}
      <div className="w-48 flex-shrink-0">
        <SportsSidebar
          sports={sports}
          selected={selectedSport}
          onSelect={setSelectedSport}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Exchange - {selectedSport || 'All Sports'}
            </h1>
            <div className="text-sm text-gray-400 mt-1">
              {events.length} events {totalPages > 1 && `(Page ${currentPage} of ${totalPages})`}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              Updated: <span className="text-betfair-gold">{formatLastUpdated()}</span>
              {scrapeStatus?.freshness?.is_fresh && (
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-900 text-green-300">
                  Live
                </span>
              )}
            </div>
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="px-4 py-2 rounded font-medium text-sm transition-colors bg-gray-700 text-white hover:bg-gray-600"
            >
              Bet History
            </button>
            <button
              onClick={handleRefreshOdds}
              disabled={isRefreshing}
              className={`px-4 py-2 rounded font-medium text-sm transition-colors ${
                isRefreshing
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  : 'bg-betfair-gold text-dark-navy hover:bg-betfair-gold/80'
              }`}
            >
              {isRefreshing ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Refreshing...
                </span>
              ) : (
                'Refresh Odds'
              )}
            </button>
          </div>
        </div>
        {refreshError && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded text-red-200 text-sm">
            {refreshError}
          </div>
        )}

        {/* Pagination - Top */}
        <Pagination />

        {/* Odds Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-400 loading-pulse">Loading events...</div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No events available for {selectedSport}</p>
            <p className="text-sm mt-2">Data is scraped from Betfair in real-time</p>
            <button
              onClick={handleRefreshOdds}
              className="mt-4 px-4 py-2 bg-betfair-gold text-dark-navy rounded hover:bg-betfair-gold/80"
            >
              Trigger Scrape
            </button>
          </div>
        ) : (
          <OddsGrid
            events={paginatedEvents}
            onSelectOdds={addToBetSlip}
            betSlip={betSlip}
            onMatchIntelligence={handleMatchIntelligence}
          />
        )}

        {/* Pagination - Bottom */}
        <Pagination />
      </div>

      {/* Bet Slip */}
      <div className="w-80 flex-shrink-0">
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
    </div>
  )
}
