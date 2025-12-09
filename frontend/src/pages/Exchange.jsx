import { useState, useEffect } from 'react'
import SportsSidebar from '../components/SportsSidebar'
import OddsGrid from '../components/OddsGrid'
import BetSlip from '../components/BetSlip'

const API_BASE = ''

export default function Exchange() {
  const [sports, setSports] = useState([])
  const [selectedSport, setSelectedSport] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [betSlip, setBetSlip] = useState([])

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

  // Fetch events when sport changes
  useEffect(() => {
    async function fetchEvents() {
      if (!selectedSport) return

      setLoading(true)
      try {
        const url = selectedSport
          ? `${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}`
          : `${API_BASE}/api/events`
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

  // Format last updated time
  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Never'
    const now = new Date()
    const diff = Math.round((now - lastUpdated) / 60000)
    if (diff < 1) return 'Just now'
    if (diff === 1) return '1 minute ago'
    return `${diff} minutes ago`
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
          <div className="text-sm text-gray-400">
            Last updated: <span className="text-betfair-gold">{formatLastUpdated()}</span>
          </div>
        </div>

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
    </div>
  )
}
