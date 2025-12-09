import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:3001'

export default function OddsGrid({ events, onSelectOdds, betSlip }) {
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

          {/* Column headers */}
          <div className="bg-gray-700/50 px-4 py-2 grid grid-cols-12 gap-2 text-sm text-gray-400">
            <div className="col-span-6">Event</div>
            <div className="col-span-3 text-center">
              <span className="text-back-blue">Back</span>
            </div>
            <div className="col-span-3 text-center">
              <span className="text-lay-pink">Lay</span>
            </div>
          </div>

          {/* Events */}
          <div className="divide-y divide-gray-700">
            {compEvents.map((event) => {
              const odds = eventOdds[event.id] || []

              return (
                <div key={event.id} className="px-4 py-3">
                  {/* Event row */}
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-6">
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
                    </div>

                    {/* Odds columns */}
                    <div className="col-span-6 grid grid-cols-2 gap-2">
                      {odds.length > 0 ? (
                        <>
                          {/* Back odds */}
                          <div className="flex gap-1">
                            {odds.slice(0, 3).map((odd, i) => (
                              <button
                                key={`back-${i}`}
                                onClick={() => onSelectOdds(event, odd.selection_name, odd.back_odds, 'back')}
                                className={`flex-1 py-2 rounded font-mono text-sm font-medium transition-colors ${
                                  isInBetSlip(event.id, odd.selection_name, 'back')
                                    ? 'bg-back-blue/50 ring-2 ring-back-blue'
                                    : 'bg-back-blue hover:bg-back-blue/80'
                                } text-dark-navy`}
                                disabled={!odd.back_odds}
                              >
                                {odd.back_odds?.toFixed(2) || '-'}
                              </button>
                            ))}
                          </div>

                          {/* Lay odds */}
                          <div className="flex gap-1">
                            {odds.slice(0, 3).map((odd, i) => (
                              <button
                                key={`lay-${i}`}
                                onClick={() => onSelectOdds(event, odd.selection_name, odd.lay_odds || odd.back_odds * 1.02, 'lay')}
                                className={`flex-1 py-2 rounded font-mono text-sm font-medium transition-colors ${
                                  isInBetSlip(event.id, odd.selection_name, 'lay')
                                    ? 'bg-lay-pink/50 ring-2 ring-lay-pink'
                                    : 'bg-lay-pink hover:bg-lay-pink/80'
                                } text-dark-navy`}
                                disabled={!odd.back_odds}
                              >
                                {odd.lay_odds?.toFixed(2) || (odd.back_odds ? (odd.back_odds * 1.02).toFixed(2) : '-')}
                              </button>
                            ))}
                          </div>
                        </>
                      ) : (
                        <div className="col-span-2 text-center text-gray-400 text-sm">
                          {loadingOdds[event.id] ? 'Loading...' : 'No odds available'}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Selection names */}
                  {odds.length > 0 && (
                    <div className="mt-1 grid grid-cols-12 gap-2">
                      <div className="col-span-6" />
                      <div className="col-span-6 grid grid-cols-2 gap-2">
                        <div className="flex gap-1">
                          {odds.slice(0, 3).map((odd, i) => (
                            <div key={i} className="flex-1 text-center text-xs text-gray-400 truncate">
                              {odd.selection_name}
                            </div>
                          ))}
                        </div>
                        <div className="flex gap-1">
                          {odds.slice(0, 3).map((odd, i) => (
                            <div key={i} className="flex-1 text-center text-xs text-gray-400 truncate">
                              {odd.selection_name}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
