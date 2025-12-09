import { useState, useEffect } from 'react'
import { API_BASE } from '../config'

export default function Sportsbook() {
  const [sports, setSports] = useState([])
  const [selectedSport, setSelectedSport] = useState(null)
  const [competitions, setCompetitions] = useState([])
  const [selectedCompetition, setSelectedCompetition] = useState(null)
  const [events, setEvents] = useState([])
  const [eventOdds, setEventOdds] = useState({})
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

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
        // Use exchange data but display as sportsbook (back odds only)
        const res = await fetch(`${API_BASE}/api/events?sport=${encodeURIComponent(selectedSport)}&data_type=exchange`)
        const data = await res.json()
        setEvents(data)

        // Extract unique competitions
        const comps = [...new Set(data.map(e => e.competition).filter(Boolean))]
        setCompetitions(comps)

        // Fetch odds for each event
        const oddsMap = {}
        for (const event of data) {
          try {
            const oddsRes = await fetch(`${API_BASE}/api/events/${event.id}`)
            const oddsData = await oddsRes.json()
            oddsMap[event.id] = oddsData.odds || []
          } catch (err) {
            console.error(`Error fetching odds for event ${event.id}:`, err)
          }
        }
        setEventOdds(oddsMap)
      } catch (err) {
        console.error('Error fetching events:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchEvents()
  }, [selectedSport])

  // Filter events by competition if selected
  const filteredEvents = selectedCompetition
    ? events.filter(e => e.competition === selectedCompetition)
    : events

  // Group events by competition
  const eventsByCompetition = filteredEvents.reduce((acc, event) => {
    const comp = event.competition || 'Other'
    if (!acc[comp]) acc[comp] = []
    acc[comp].push(event)
    return acc
  }, {})

  return (
    <div className="flex min-h-[calc(100vh-88px)]">
      {/* Left Sidebar - Sports & Competitions */}
      <div className={`${sidebarCollapsed ? 'w-12' : 'w-64'} bg-gray-900 border-r border-gray-700 transition-all duration-300 flex-shrink-0`}>
        {/* Collapse Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="w-full p-3 border-b border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800 flex items-center justify-center"
        >
          {sidebarCollapsed ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          )}
        </button>

        {!sidebarCollapsed && (
          <>
            {/* Sports List */}
            <div className="p-3 border-b border-gray-700">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Sports</h3>
              <div className="space-y-1">
                {sports.map((sport) => (
                  <button
                    key={sport.name || sport.sport}
                    onClick={() => {
                      setSelectedSport(sport.name || sport.sport)
                      setSelectedCompetition(null)
                    }}
                    className={`w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between transition-colors ${
                      selectedSport === (sport.name || sport.sport)
                        ? 'bg-betfair-gold text-dark-navy font-medium'
                        : 'text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    <span>{sport.name || sport.sport}</span>
                    <span className={`text-xs ${selectedSport === (sport.name || sport.sport) ? 'text-dark-navy/70' : 'text-gray-500'}`}>
                      {sport.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Competitions List */}
            {competitions.length > 0 && (
              <div className="p-3">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Competitions</h3>
                <div className="space-y-1 max-h-[400px] overflow-y-auto">
                  <button
                    onClick={() => setSelectedCompetition(null)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      !selectedCompetition
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    All Competitions
                  </button>
                  {competitions.map((comp) => (
                    <button
                      key={comp}
                      onClick={() => setSelectedCompetition(comp)}
                      className={`w-full text-left px-3 py-2 rounded text-sm transition-colors truncate ${
                        selectedCompetition === comp
                          ? 'bg-gray-700 text-white'
                          : 'text-gray-300 hover:bg-gray-800'
                      }`}
                      title={comp}
                    >
                      {comp}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 bg-dark-navy">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
          <h1 className="text-xl font-bold text-white">
            {selectedSport || 'All Sports'}
            {selectedCompetition && (
              <span className="text-gray-400 font-normal ml-2">/ {selectedCompetition}</span>
            )}
          </h1>
          <p className="text-sm text-gray-400 mt-1">Fixed odds betting - Back only</p>
        </div>

        {/* Events */}
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="flex items-center gap-3 text-gray-400">
                <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Loading events...</span>
              </div>
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>No events available</p>
              <p className="text-sm mt-1">Try selecting a different sport or competition</p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(eventsByCompetition).map(([competition, compEvents]) => (
                <div key={competition} className="bg-gray-800 rounded-lg overflow-hidden">
                  {/* Competition Header */}
                  <div className="bg-gray-700 px-4 py-2 flex items-center gap-2">
                    <svg className="w-4 h-4 text-betfair-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                    </svg>
                    <span className="font-medium text-white text-sm">{competition}</span>
                    <span className="text-gray-400 text-xs">({compEvents.length} events)</span>
                  </div>

                  {/* Column Headers */}
                  <div className="bg-gray-750 px-4 py-2 grid grid-cols-12 gap-2 text-xs text-gray-400 font-medium border-b border-gray-700">
                    <div className="col-span-5">Event</div>
                    <div className="col-span-2 text-center">1</div>
                    <div className="col-span-2 text-center">X</div>
                    <div className="col-span-2 text-center">2</div>
                    <div className="col-span-1"></div>
                  </div>

                  {/* Events */}
                  {compEvents.map((event) => {
                    const odds = eventOdds[event.id] || []
                    const homeOdds = odds[0]?.back_odds
                    const drawOdds = odds[1]?.back_odds
                    const awayOdds = odds[2]?.back_odds

                    return (
                      <div
                        key={event.id}
                        className="px-4 py-3 border-b border-gray-700 last:border-b-0 hover:bg-gray-750 transition-colors grid grid-cols-12 gap-2 items-center"
                      >
                        {/* Event Info */}
                        <div className="col-span-5">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-white text-sm">{event.event_name}</span>
                            {event.is_live === 1 && (
                              <span className="px-1.5 py-0.5 bg-red-500 text-white text-[10px] font-bold rounded animate-pulse">
                                LIVE
                              </span>
                            )}
                          </div>
                          {event.start_time && (
                            <div className="text-xs text-gray-400 mt-0.5">{event.start_time}</div>
                          )}
                        </div>

                        {/* Home Odds */}
                        <div className="col-span-2">
                          <button
                            className={`w-full py-2 rounded font-mono text-sm font-medium transition-all ${
                              homeOdds
                                ? 'bg-betfair-gold text-dark-navy hover:bg-betfair-gold/80'
                                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            }`}
                            disabled={!homeOdds}
                          >
                            {homeOdds?.toFixed(2) || '-'}
                          </button>
                        </div>

                        {/* Draw Odds */}
                        <div className="col-span-2">
                          <button
                            className={`w-full py-2 rounded font-mono text-sm font-medium transition-all ${
                              drawOdds
                                ? 'bg-betfair-gold text-dark-navy hover:bg-betfair-gold/80'
                                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            }`}
                            disabled={!drawOdds}
                          >
                            {drawOdds?.toFixed(2) || '-'}
                          </button>
                        </div>

                        {/* Away Odds */}
                        <div className="col-span-2">
                          <button
                            className={`w-full py-2 rounded font-mono text-sm font-medium transition-all ${
                              awayOdds
                                ? 'bg-betfair-gold text-dark-navy hover:bg-betfair-gold/80'
                                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            }`}
                            disabled={!awayOdds}
                          >
                            {awayOdds?.toFixed(2) || '-'}
                          </button>
                        </div>

                        {/* More Markets */}
                        <div className="col-span-1 flex justify-end">
                          <button
                            className="text-gray-400 hover:text-white p-1"
                            title="More markets"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
