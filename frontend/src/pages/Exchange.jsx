import { useState, useEffect } from 'react'
import SportsSidebar from '../components/SportsSidebar'
import OddsGrid from '../components/OddsGrid'
import BetSlip from '../components/BetSlip'
import AIChatPanel from '../components/AIChatPanel'
import BetHistory from '../components/BetHistory'
import { API_BASE } from '../config'

export default function Exchange() {
  const [sports, setSports] = useState([])
  const [selectedSport, setSelectedSport] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [betSlip, setBetSlip] = useState([])

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

  // Fetch events when sport changes - EXCHANGE DATA ONLY
  useEffect(() => {
    async function fetchEvents() {
      if (!selectedSport) return

      setLoading(true)
      try {
        // Request exchange data only (with back/lay odds)
        const url = selectedSport
          ? `${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}&data_type=exchange`
          : `${API_BASE}/api/events?data_type=exchange`
        const res = await fetch(url)
        const data = await res.json()
        setEvents(data)

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
        setLoading(false)
      }
    }
    fetchEvents()
  }, [selectedSport])

  // Add selection to bet slip
  const addToBetSlip = (event, selection, odds, type) => {
    const newBet = {
      id: `${event.id}-${selection}-${type}`,
      eventId: event.id,
      eventName: event.event_name,
      selection,
      odds,
      type, // 'back' or 'lay'
      stake: '',
    }

    // Check if already in slip
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

  // Handle Match Intelligence - opens AI chat with pre-populated research query
  // Receives odds directly from OddsGrid component (page data supersedes DB)
  const handleMatchIntelligence = async (event, odds = []) => {
    // Simplified message for display
    const message = `Research value bets for "${event.event_name}" (${event.sport}).`

    // Use odds passed from OddsGrid (page data supersedes DB)
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
      // Include current odds from page - this supersedes DB data
      current_odds_from_page: currentOdds,
      note: "IMPORTANT: Use current_odds_from_page as the authoritative odds source. This data comes directly from the page and is more current than the database."
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
      // Trigger exchange scrape only
      const res = await fetch(`${API_BASE}/api/scrape/trigger?data_type=exchange`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        // Re-fetch exchange events after scrape completes
        const eventsRes = await fetch(
          selectedSport
            ? `${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}&data_type=exchange`
            : `${API_BASE}/api/events?data_type=exchange`
        )
        const eventsData = await eventsRes.json()
        setEvents(eventsData)
        if (eventsData.length > 0) {
          const newest = eventsData.reduce((a, b) =>
            new Date(a.scraped_at) > new Date(b.scraped_at) ? a : b
          )
          setLastUpdated(new Date(newest.scraped_at))
        }
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
          <h1 className="text-2xl font-bold text-white">
            Exchange - {selectedSport || 'All Sports'}
          </h1>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              Last updated: <span className="text-betfair-gold">{formatLastUpdated()}</span>
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

        {/* Odds Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-400 loading-pulse">Loading events...</div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No events available for {selectedSport}</p>
            <p className="text-sm mt-2">Data is scraped from Betfair in real-time</p>
          </div>
        ) : (
          <OddsGrid
            events={events}
            onSelectOdds={addToBetSlip}
            betSlip={betSlip}
            onMatchIntelligence={handleMatchIntelligence}
          />
        )}
      </div>

      {/* Bet Slip */}
      <div className="w-80 flex-shrink-0">
        <BetSlip
          bets={betSlip}
          onRemove={removeFromBetSlip}
          onUpdateStake={updateStake}
          onClear={clearBetSlip}
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
