import { useState, useEffect } from 'react'

const API_BASE = ''

export default function OddsGrid({ events, onSelectOdds, betSlip, onMatchIntelligence }) {
  const [eventOdds, setEventOdds] = useState({})
  const [loadingOdds, setLoadingOdds] = useState({})

  // Fetch odds for each event
  useEffect(() => {
    async function fetchOdds(eventId) {
      if (eventOdds[eventId] || loadingOdds[eventId]) return

      setLoadingOdds(prev => ({ ...prev, [eventId]: true }))
      try {
        const res = await fetch(`${API_BASE}/api/events/${eventId}`)
        const data = await res.json()
        setEventOdds(prev => ({ ...prev, [eventId]: data.odds || [] }))
      } catch (err) {
        console.error(`Error fetching odds for event ${eventId}:`, err)
      } finally {
        setLoadingOdds(prev => ({ ...prev, [eventId]: false }))
      }
    }

    events.forEach(event => {
      fetchOdds(event.id)
    })
  }, [events])

  // Check if selection is in bet slip
  const isInBetSlip = (eventId, selection, type) => {
    return betSlip.some(b =>
      b.eventId === eventId && b.selection === selection && b.type === type
    )
  }

  // Group events by competition
  const groupedEvents = events.reduce((acc, event) => {
    const comp = event.competition || 'Other'
    if (!acc[comp]) acc[comp] = []
    acc[comp].push(event)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {Object.entries(groupedEvents).map(([competition, compEvents]) => (
        <div key={competition} className="bg-gray-800 rounded-lg overflow-hidden">
          {/* Competition header */}
          <div className="bg-gray-700 px-4 py-2 border-b border-gray-600">
            <h3 className="font-medium text-white">{competition}</h3>
          </div>

          {/* Column headers - Betfair Exchange style */}
          <div className="bg-gray-700/50 px-4 py-2 grid grid-cols-12 gap-2 text-sm text-gray-400">
            <div className="col-span-4">Event</div>
            <div className="col-span-8">
              <div className="grid grid-cols-3 gap-2">
                {/* Each selection column has Back/Lay sub-headers */}
                <div className="text-center">
                  <div className="flex justify-center gap-1 text-xs">
                    <span className="text-back-blue w-12">Back</span>
                    <span className="text-lay-pink w-12">Lay</span>
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex justify-center gap-1 text-xs">
                    <span className="text-back-blue w-12">Back</span>
                    <span className="text-lay-pink w-12">Lay</span>
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex justify-center gap-1 text-xs">
                    <span className="text-back-blue w-12">Back</span>
                    <span className="text-lay-pink w-12">Lay</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Events */}
          <div className="divide-y divide-gray-700">
            {compEvents.map((event) => {
              const odds = eventOdds[event.id] || []
              // Pad to 3 selections for consistent layout
              const paddedOdds = [...odds.slice(0, 3)]
              while (paddedOdds.length < 3) {
                paddedOdds.push(null)
              }

              return (
                <div key={event.id} className="px-4 py-3">
                  {/* Event row */}
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-4">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">
                          {event.event_name}
                        </span>
                        {event.is_live === 1 && (
                          <span className="live-indicator">LIVE</span>
                        )}
                      </div>
                      {event.start_time && (
                        <span className="text-sm text-gray-400">
                          {event.start_time}
                        </span>
                      )}
                      {/* Match Intelligence link */}
                      <button
                        onClick={() => onMatchIntelligence && onMatchIntelligence(event, odds)}
                        className="text-xs text-ai-accent hover:text-ai-accent/80 hover:underline mt-1 flex items-center gap-1"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        Match Intelligence
                      </button>
                    </div>

                    {/* Odds columns - each selection has Back/Lay pair side by side */}
                    <div className="col-span-8">
                      {odds.length > 0 ? (
                        <div className="grid grid-cols-3 gap-2">
                          {paddedOdds.map((odd, i) => (
                            <div key={i} className="flex flex-col">
                              {/* Selection name above Back/Lay buttons */}
                              <div className="text-xs text-gray-400 text-center truncate mb-1 h-4">
                                {odd?.selection_name || '-'}
                              </div>
                              {/* Back/Lay button pair */}
                              <div className="flex gap-1 justify-center">
                                {/* Back button (blue) */}
                                <button
                                  onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.back_odds, 'back')}
                                  className={`w-12 py-1.5 rounded font-mono text-xs font-medium transition-colors ${
                                    odd && isInBetSlip(event.id, odd.selection_name, 'back')
                                      ? 'bg-back-blue/50 ring-2 ring-back-blue'
                                      : 'bg-back-blue hover:bg-back-blue/80'
                                  } text-dark-navy`}
                                  disabled={!odd?.back_odds}
                                  title={odd ? `Back ${odd.selection_name} @ ${odd.back_odds}` : ''}
                                >
                                  {odd?.back_odds?.toFixed(2) || '-'}
                                </button>
                                {/* Lay button (pink) - higher odds than back */}
                                <button
                                  onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.lay_odds || (odd.back_odds * 1.02), 'lay')}
                                  className={`w-12 py-1.5 rounded font-mono text-xs font-medium transition-colors ${
                                    odd && isInBetSlip(event.id, odd.selection_name, 'lay')
                                      ? 'bg-lay-pink/50 ring-2 ring-lay-pink'
                                      : 'bg-lay-pink hover:bg-lay-pink/80'
                                  } text-dark-navy`}
                                  disabled={!odd?.back_odds}
                                  title={odd ? `Lay ${odd.selection_name} @ ${odd.lay_odds || (odd.back_odds * 1.02).toFixed(2)}` : ''}
                                >
                                  {odd?.lay_odds?.toFixed(2) || (odd?.back_odds ? (odd.back_odds * 1.02).toFixed(2) : '-')}
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center text-gray-400 text-sm py-2">
                          {loadingOdds[event.id] ? 'Loading...' : 'No odds available'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
