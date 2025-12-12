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

export default function OddsGrid({ events, onSelectOdds, betSlip, onMatchIntelligence, onDeepResearch }) {
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
    <div className="space-y-3">
      {sortedCompetitions.map((competition) => {
        const compEvents = groupedEvents[competition]
        const isCollapsed = collapsedComps[competition]

        return (
          <div key={competition} className="bf-card overflow-hidden">
            {/* Competition header - Betfair dark style */}
            <button
              onClick={() => toggleCompetition(competition)}
              className="w-full competition-header"
            >
              <div className="flex items-center gap-2">
                <svg
                  className={`w-4 h-4 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span>{competition}</span>
              </div>
              <span className="text-white/60 text-xs font-normal">
                {compEvents.length} {compEvents.length === 1 ? 'market' : 'markets'}
              </span>
            </button>

            {!isCollapsed && (
              <div>
                {/* Column headers - Betfair style */}
                <div className="bg-header-bg border-b border-gray-200">
                  <div className="grid grid-cols-12 gap-0">
                    <div className="col-span-5 px-3 py-2 text-xs font-semibold text-betfair-gray uppercase">
                      Event
                    </div>
                    <div className="col-span-7">
                      <div className="grid grid-cols-6 text-center">
                        <div className="col-span-3 bg-back-blue/30 py-2 border-l border-white">
                          <span className="text-xs font-semibold text-betfair-gray uppercase">Back</span>
                        </div>
                        <div className="col-span-3 bg-lay-pink/30 py-2 border-l border-white">
                          <span className="text-xs font-semibold text-betfair-gray uppercase">Lay</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Events list */}
                <div>
                  {compEvents.map((event, eventIndex) => {
                    const odds = event.odds || []
                    const paddedOdds = [...odds.slice(0, 3)]
                    while (paddedOdds.length < 3) paddedOdds.push(null)

                    const parsed = parseEventName(event.event_name)
                    const displayName = parsed.name || event.event_name
                    const displayTime = event.start_time || parsed.dateTime

                    return (
                      <div
                        key={event.id}
                        className={`event-row border-b border-gray-200 ${eventIndex % 2 === 0 ? 'bg-row-even' : 'bg-row-odd'}`}
                      >
                        <div className="grid grid-cols-12 gap-0 items-center">
                          {/* Event info */}
                          <div className="col-span-5 px-3 py-2">
                            <div className="flex items-start gap-2">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-betfair-black text-sm truncate">
                                    {displayName}
                                  </span>
                                  {event.is_live === 1 && (
                                    <span className="live-indicator">In-Play</span>
                                  )}
                                </div>
                                {displayTime && (
                                  <div className="text-xs text-betfair-gray mt-0.5">{displayTime}</div>
                                )}
                                <div className="flex items-center gap-3 mt-1">
                                  <button
                                    onClick={() => onMatchIntelligence && onMatchIntelligence(event, odds)}
                                    className="text-xs text-ai-accent hover:underline flex items-center gap-1"
                                  >
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                    </svg>
                                    AI Analysis
                                  </button>
                                  <button
                                    onClick={() => onDeepResearch && onDeepResearch(event)}
                                    className="text-xs text-amber-600 hover:underline flex items-center gap-1"
                                    title="Gemini Deep Research (~£2 cost)"
                                  >
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    Deep Analysis (£2)
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Odds columns - Betfair style with 3 back + 3 lay */}
                          <div className="col-span-7">
                            {odds.length > 0 ? (
                              <div className="divide-y divide-gray-100">
                                {paddedOdds.map((odd, i) => (
                                  <div key={i} className="grid grid-cols-6 items-center">
                                    {/* Selection name */}
                                    <div className="col-span-2 px-2 py-1.5 text-xs text-betfair-gray truncate border-l border-gray-200">
                                      {odd?.selection_name || '-'}
                                    </div>

                                    {/* Back odds - deeper blue for best price */}
                                    <button
                                      onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.back_odds, 'back')}
                                      className={`py-1.5 text-center border-l border-white transition-all ${
                                        odd && isInBetSlip(event.id, odd.selection_name, 'back')
                                          ? 'back-cell-deep ring-2 ring-inset ring-betfair-black'
                                          : 'back-cell-deep'
                                      }`}
                                      disabled={!odd?.back_odds}
                                    >
                                      <div className="font-mono text-sm font-bold text-betfair-black">
                                        {odd?.back_odds?.toFixed(2) || '-'}
                                      </div>
                                    </button>
                                    <div className="back-cell py-1.5 text-center border-l border-white">
                                      <div className="font-mono text-xs text-betfair-gray">
                                        {odd?.back_odds ? (odd.back_odds * 1.01).toFixed(2) : '-'}
                                      </div>
                                    </div>

                                    {/* Lay odds - deeper pink for best price */}
                                    <div className="lay-cell py-1.5 text-center border-l border-white">
                                      <div className="font-mono text-xs text-betfair-gray">
                                        {odd?.lay_odds ? (odd.lay_odds * 0.99).toFixed(2) : (odd?.back_odds ? (odd.back_odds * 1.01).toFixed(2) : '-')}
                                      </div>
                                    </div>
                                    <button
                                      onClick={() => odd && onSelectOdds(event, odd.selection_name, odd.lay_odds || (odd.back_odds * 1.02), 'lay')}
                                      className={`py-1.5 text-center border-l border-white transition-all ${
                                        odd && isInBetSlip(event.id, odd.selection_name, 'lay')
                                          ? 'lay-cell-deep ring-2 ring-inset ring-betfair-black'
                                          : 'lay-cell-deep'
                                      }`}
                                      disabled={!odd?.back_odds}
                                    >
                                      <div className="font-mono text-sm font-bold text-betfair-black">
                                        {odd?.lay_odds?.toFixed(2) || (odd?.back_odds ? (odd.back_odds * 1.02).toFixed(2) : '-')}
                                      </div>
                                    </button>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-center text-betfair-gray text-xs py-4 col-span-6">
                                No odds available
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
