import { useState, useEffect } from 'react'

const API_BASE = ''

export default function Sportsbook() {
  const [sports, setSports] = useState([])
  const [selectedSport, setSelectedSport] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  // Fetch sports list
  useEffect(() => {
    async function fetchSports() {
      try {
        const res = await fetch(`${API_BASE}/api/sports`)
        const data = await res.json()
        setSports(data)
        if (data.length > 0) {
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
        const res = await fetch(`${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}`)
        const data = await res.json()
        setEvents(data)
      } catch (err) {
        console.error('Error fetching events:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchEvents()
  }, [selectedSport])

  return (
    <div>
      {/* Sport tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {sports.map((sport) => (
          <button
            key={sport.name || sport.sport}
            onClick={() => setSelectedSport(sport.name || sport.sport)}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              selectedSport === (sport.name || sport.sport)
                ? 'bg-betfair-gold text-dark-navy'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {sport.name || sport.sport} ({sport.count})
          </button>
        ))}
      </div>

      {/* Events */}
      <h1 className="text-2xl font-bold text-white mb-4">
        Sportsbook - {selectedSport || 'All Sports'}
      </h1>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400 loading-pulse">Loading...</div>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p>No events available</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {events.map((event) => (
            <div
              key={event.id}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-white">{event.event_name}</h3>
                    {event.is_live === 1 && (
                      <span className="live-indicator">LIVE</span>
                    )}
                  </div>
                  {event.competition && (
                    <p className="text-sm text-gray-400">{event.competition}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  {/* Single price display for sportsbook */}
                  <button className="px-4 py-2 bg-betfair-gold text-dark-navy font-mono font-medium rounded hover:bg-betfair-gold/80 transition-colors">
                    View Odds
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
