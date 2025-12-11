import { useState } from 'react'

// Parse event name to separate date/time/status prefix from actual name
function parseEventName(rawName) {
  if (!rawName) return { name: '', dateTime: null }

  // Patterns to match time/status prefixes like "Starting In 7'mi", "17:30", "Today 17:30", etc.
  const dateTimePatterns = [
    /^(Starting\s+In\s+[\d']+mi?)\s*(.+)$/i,      // "Starting In 7'mi" or "Starting In 7mi"
    /^(In-Play)\s*(.+)$/i,                         // "In-Play"
    /^(Today|Tomorrow)\s+(\d{1,2}:\d{2})\s*(.+)$/, // "Today 17:30" - captures day and time separately
    /^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{1,2}:\d{2})\s*(.+)$/, // "Dec 11 17:30"
    /^(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{1,2}:\d{2})\s*(.+)$/, // "11 Dec 17:30"
    /^(\d{1,2}:\d{2})\s*(.+)$/,                    // "17:30"
  ]

  for (const pattern of dateTimePatterns) {
    const match = rawName.match(pattern)
    if (match) {
      // Handle "Today/Tomorrow HH:MM" pattern separately (has 3 groups)
      if (match.length === 4) {
        return { dateTime: `${match[1]} ${match[2]}`, name: match[3].trim() }
      }
      return { dateTime: match[1].trim(), name: match[2].trim() }
    }
  }

  return { name: rawName, dateTime: null }
}

export default function OddsGrid({ events, onSelectOdds, betSlip, onMatchIntelligence }) {
  const [collapsedComps, setCollapsedComps] = useState({})

  const toggleCompetition = (comp) => {
    setCollapsedComps(prev => ({ ...prev, [comp]: !prev[comp] }))
  }

  const isInBetSlip = (eventId, selection, type) => {
    return betSlip.some(b => b.eventId === eventId && b.selection === selection && b.type === type)
  }

  // Group events by competition
  const groupedEvents = events.reduce((acc, event) => {
    const comp = event.competition || 'Other Events'
    if (!acc[comp]) acc[comp] = []
    acc[comp].push(event)
    return acc
  }, {})

  // Sort competitions alphabetically, "Other Events" last
  const sortedCompetitions = Object.keys(groupedEvents).sort((a, b) => {
    if (a === 'Other Events') return 1
    if (b === 'Other Events') return -1
    return a.localeCompare(b)
  })

  return (
    <div className="space-y-4">
      {sortedCompetitions.map((competition) => {
        const compEvents = groupedEvents[competition]
        const isCollapsed = collapsedComps[competition]

        return (
          <div key={competition} className="bg-gray-800 rounded-lg overflow-hidden">
            {/* Competition header - clickable to collapse */}
            <button
              onClick={() => toggleCompetition(competition)}
              className="w-full bg-gray-700 px-4 py-2 border-b border-gray-600 flex items-center justify-between hover:bg-gray-600 transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <h3 className="font-medium text-white">{competition}</h3>
              </div>
              <span className="text-sm text-gray-400">
                {compEvents.length} event{compEvents.length !== 1 ? 's' : ''}
              </span>
            </button>

            {!isCollapsed && (
              <>
                {/* Column headers */}
                <div className="bg-gray-700/50 px-4 py-2 grid grid-cols-12 gap-2 text-sm text-gray-400">
                  <div className="col-span-4">Event</div>
                  <div className="col-span-8">
                    <div className="grid grid-cols-3 gap-2">
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="text-center">
                          <div className="flex justify-center gap-1 text-xs">
                            <span className="text-back-blue w-12">Back</span>
                            <span className="text-lay-pink w-12">Lay</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Events list */}
                <div className="divide-y divide-gray-700">
                  {compEvents.map((event) => {
                    const odds = event.odds || []
                    const paddedOdds = [...odds.slice(0, 3)]
                    while (paddedOdds.length < 3) paddedOdds.push(null)

                    const parsed = parseEventName(event.event_name)
                    const displayName = parsed.name || event.event_name
                    const displayTime = event.start_time || parsed.dateTime

                    return (
                      <div key={event.id} className="px-4 py-3">
                        <div className="grid grid-cols-12 gap-2 items-center">
                          {/* Event info */}
                          <div className="col-span-4">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white">{displayName}</span>
                              {event.is_live === 1 && <span className="live-indicator">LIVE</span>}
                            </div>
                            {displayTime && <div className="text-sm text-gray-400">{displayTime}</div>}
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

                          {/* Odds */}
                          <div className="col-span-8">
                            {odds.length > 0 ? (
                              <div className="grid grid-cols-3 gap-2">
                                {paddedOdds.map((odd, i) => (
                                  <div key={i} className="flex flex-col">
                                    <div className="text-xs text-gray-400 text-center truncate mb-1 h-4">
                                      {odd?.selection_name || '-'}
                                    </div>
                                    <div className="flex gap-1 justify-center">
                                      <button
                                        onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.back_odds, 'back')}
                                        className={`w-12 py-1.5 rounded font-mono text-xs font-medium transition-colors ${
                                          odd && isInBetSlip(event.id, odd.selection_name, 'back')
                                            ? 'bg-back-blue/50 ring-2 ring-back-blue'
                                            : 'bg-back-blue hover:bg-back-blue/80'
                                        } text-dark-navy`}
                                        disabled={!odd?.back_odds}
                                      >
                                        {odd?.back_odds?.toFixed(2) || '-'}
                                      </button>
                                      <button
                                        onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.lay_odds || (odd.back_odds * 1.02), 'lay')}
                                        className={`w-12 py-1.5 rounded font-mono text-xs font-medium transition-colors ${
                                          odd && isInBetSlip(event.id, odd.selection_name, 'lay')
                                            ? 'bg-lay-pink/50 ring-2 ring-lay-pink'
                                            : 'bg-lay-pink hover:bg-lay-pink/80'
                                        } text-dark-navy`}
                                        disabled={!odd?.back_odds}
                                      >
                                        {odd?.lay_odds?.toFixed(2) || (odd?.back_odds ? (odd.back_odds * 1.02).toFixed(2) : '-')}
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-center text-gray-400 text-sm py-2">No odds available</div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
