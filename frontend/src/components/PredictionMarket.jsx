import { useState, useEffect } from 'react'
import { API_BASE } from '../config'

export default function PredictionMarket({ isOpen, onClose, balance, onBalanceChange }) {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedPrediction, setSelectedPrediction] = useState(null)
  const [stake, setStake] = useState('')
  const [placingBet, setPlacingBet] = useState(false)
  const [betResult, setBetResult] = useState(null)

  // Fetch football matches
  const fetchMatches = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/events?sport=football&data_type=exchange`)
      const data = await res.json()
      setMatches(data)
    } catch (err) {
      console.error('Error fetching matches:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchMatches()
      setSelectedPrediction(null)
      setStake('')
      setBetResult(null)
    }
  }, [isOpen])

  // Parse event name to extract clean match name
  const parseEventName = (rawName) => {
    if (!rawName) return rawName
    const patterns = [
      /^(Starting\s+In\s+[\d']+mi?)\s*(.+)$/i,
      /^(In-Play)\s*(.+)$/i,
      /^(Today|Tomorrow)\s+(\d{1,2}:\d{2})\s*(.+)$/,
      /^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{1,2}:\d{2})\s*(.+)$/,
      /^(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{1,2}:\d{2})\s*(.+)$/,
      /^(\d{1,2}:\d{2})\s*(.+)$/,
    ]
    for (const pattern of patterns) {
      const match = rawName.match(pattern)
      if (match) {
        return match.length === 4 ? match[3].trim() : match[2].trim()
      }
    }
    return rawName
  }

  // Select a prediction (team to win or draw)
  const selectPrediction = (match, selection, odds) => {
    setSelectedPrediction({
      matchId: match.id,
      matchName: parseEventName(match.event_name),
      selection,
      odds,
      competition: match.competition
    })
    setStake('')
    setBetResult(null)
  }

  // Place the prediction bet
  const placePrediction = async () => {
    if (!selectedPrediction || !stake || parseFloat(stake) <= 0) return

    setPlacingBet(true)
    try {
      const res = await fetch(`${API_BASE}/api/bets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: selectedPrediction.matchId,
          selection_name: selectedPrediction.selection,
          odds: selectedPrediction.odds,
          stake: parseFloat(stake),
          bet_type: 'back'
        })
      })
      const data = await res.json()
      if (data.success) {
        setBetResult({ success: true, message: 'Prediction placed!' })
        if (onBalanceChange) {
          onBalanceChange(data.new_balance)
        }
        setSelectedPrediction(null)
        setStake('')
      } else {
        setBetResult({ success: false, message: data.error || 'Failed to place prediction' })
      }
    } catch (err) {
      console.error('Error placing prediction:', err)
      setBetResult({ success: false, message: 'Network error' })
    } finally {
      setPlacingBet(false)
    }
  }

  // Calculate potential return
  const potentialReturn = selectedPrediction && stake
    ? (parseFloat(stake) * selectedPrediction.odds).toFixed(2)
    : '0.00'

  if (!isOpen) return null

  // Group matches by competition
  const groupedMatches = matches.reduce((acc, match) => {
    const comp = match.competition || 'Other Matches'
    if (!acc[comp]) acc[comp] = []
    acc[comp].push(match)
    return acc
  }, {})

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel - full width modal */}
      <div className="fixed inset-x-4 inset-y-4 md:inset-x-20 md:inset-y-10 bg-white rounded-lg shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <div>
              <h2 className="font-bold text-white text-lg">Prediction Markets</h2>
              <p className="text-green-100 text-sm">Football Matches</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="bg-white/20 px-3 py-1.5 rounded text-white text-sm">
              Balance: <span className="font-bold">£{balance?.toFixed(2) || '0.00'}</span>
            </div>
            <button
              onClick={fetchMatches}
              className="text-white/70 hover:text-white p-2 transition-colors"
              title="Refresh matches"
            >
              <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={onClose}
              className="text-white/70 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Matches List */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="flex items-center gap-3 text-betfair-gray">
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="text-lg">Loading football matches...</span>
                </div>
              </div>
            ) : matches.length === 0 ? (
              <div className="text-center text-betfair-gray py-16">
                <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-lg font-medium">No football matches available</p>
                <p className="text-sm mt-1">Check back later for upcoming matches</p>
              </div>
            ) : (
              <div className="space-y-4">
                {Object.entries(groupedMatches).map(([competition, compMatches]) => (
                  <div key={competition} className="bg-white rounded-lg shadow-sm overflow-hidden">
                    {/* Competition Header */}
                    <div className="bg-betfair-dark px-4 py-2.5 flex items-center gap-2">
                      <svg className="w-4 h-4 text-betfair-yellow" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 14a6 6 0 110-12 6 6 0 010 12z"/>
                      </svg>
                      <span className="text-white font-semibold text-sm">{competition}</span>
                      <span className="text-white/50 text-xs ml-auto">{compMatches.length} matches</span>
                    </div>

                    {/* Matches */}
                    <div className="divide-y divide-gray-100">
                      {compMatches.map((match) => {
                        const odds = match.odds || []
                        const matchName = parseEventName(match.event_name)

                        return (
                          <div key={match.id} className="p-4 hover:bg-gray-50 transition-colors">
                            {/* Match Info */}
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-betfair-black">{matchName}</span>
                                {match.is_live === 1 && (
                                  <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded font-medium animate-pulse">
                                    LIVE
                                  </span>
                                )}
                              </div>
                              {match.start_time && (
                                <span className="text-xs text-betfair-gray">{match.start_time}</span>
                              )}
                            </div>

                            {/* Prediction Buttons */}
                            {odds.length > 0 ? (
                              <div className="grid grid-cols-3 gap-2">
                                {odds.slice(0, 3).map((odd) => {
                                  const isSelected = selectedPrediction?.matchId === match.id &&
                                                    selectedPrediction?.selection === odd.selection_name
                                  return (
                                    <button
                                      key={odd.selection_name}
                                      onClick={() => selectPrediction(match, odd.selection_name, odd.back_odds)}
                                      className={`p-3 rounded-lg border-2 transition-all ${
                                        isSelected
                                          ? 'border-green-500 bg-green-50 ring-2 ring-green-200'
                                          : 'border-gray-200 hover:border-green-300 hover:bg-green-50/50'
                                      }`}
                                    >
                                      <div className="text-xs text-betfair-gray mb-1 truncate">
                                        {odd.selection_name}
                                      </div>
                                      <div className={`text-lg font-bold font-mono ${
                                        isSelected ? 'text-green-600' : 'text-betfair-black'
                                      }`}>
                                        {odd.back_odds?.toFixed(2) || '-'}
                                      </div>
                                    </button>
                                  )
                                })}
                              </div>
                            ) : (
                              <div className="text-center text-betfair-gray text-sm py-2">
                                No odds available
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bet Slip Sidebar */}
          <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
            <div className="bg-betfair-yellow px-4 py-3">
              <h3 className="font-bold text-betfair-black">Your Prediction</h3>
            </div>

            <div className="flex-1 p-4">
              {selectedPrediction ? (
                <div className="space-y-4">
                  {/* Selected Match */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-betfair-gray mb-1">{selectedPrediction.competition}</p>
                    <p className="font-medium text-betfair-black text-sm">{selectedPrediction.matchName}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-green-600 font-semibold">{selectedPrediction.selection}</span>
                      <span className="bg-betfair-yellow px-2 py-0.5 rounded font-mono font-bold text-sm">
                        @{selectedPrediction.odds.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Stake Input */}
                  <div>
                    <label className="block text-sm font-medium text-betfair-gray mb-2">
                      Stake Amount (£)
                    </label>
                    <input
                      type="number"
                      value={stake}
                      onChange={(e) => setStake(e.target.value)}
                      placeholder="Enter stake"
                      min="0.01"
                      step="0.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-lg font-mono"
                    />
                  </div>

                  {/* Quick Stakes */}
                  <div className="grid grid-cols-4 gap-2">
                    {[5, 10, 25, 50].map((amount) => (
                      <button
                        key={amount}
                        onClick={() => setStake(amount.toString())}
                        className="py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded transition-colors font-medium"
                      >
                        £{amount}
                      </button>
                    ))}
                  </div>

                  {/* Potential Return */}
                  <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-green-700">Potential Return</span>
                      <span className="text-xl font-bold text-green-600">£{potentialReturn}</span>
                    </div>
                    {stake && (
                      <div className="text-xs text-green-600 mt-1">
                        Profit: £{(parseFloat(potentialReturn) - parseFloat(stake)).toFixed(2)}
                      </div>
                    )}
                  </div>

                  {/* Place Button */}
                  <button
                    onClick={placePrediction}
                    disabled={!stake || parseFloat(stake) <= 0 || placingBet}
                    className={`w-full py-3 rounded-lg font-bold text-white transition-colors ${
                      !stake || parseFloat(stake) <= 0 || placingBet
                        ? 'bg-gray-300 cursor-not-allowed'
                        : 'bg-green-600 hover:bg-green-700'
                    }`}
                  >
                    {placingBet ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Placing...
                      </span>
                    ) : (
                      'Place Prediction'
                    )}
                  </button>

                  {/* Result Message */}
                  {betResult && (
                    <div className={`p-3 rounded-lg text-sm ${
                      betResult.success
                        ? 'bg-green-100 text-green-700 border border-green-200'
                        : 'bg-red-100 text-red-700 border border-red-200'
                    }`}>
                      {betResult.message}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-betfair-gray py-8">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                  </svg>
                  <p className="font-medium">Select a prediction</p>
                  <p className="text-sm mt-1">Click on any outcome to make your prediction</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
              <p className="text-xs text-betfair-gray text-center">
                Predictions are for entertainment purposes only.
                <br />Please gamble responsibly.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
