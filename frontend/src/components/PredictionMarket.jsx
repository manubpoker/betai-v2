import { useState, useEffect } from 'react'
import { API_BASE } from '../config'

export default function PredictionMarket({ isOpen, onClose, balance, onBalanceChange }) {
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedMarket, setSelectedMarket] = useState(null)
  const [selectedOutcome, setSelectedOutcome] = useState(null) // 'yes' or 'no'
  const [shares, setShares] = useState('')
  const [placingTrade, setPlacingTrade] = useState(false)
  const [tradeResult, setTradeResult] = useState(null)
  const [filter, setFilter] = useState('all') // 'all', 'football', 'trending'

  // Generate prediction markets from football events
  const generateMarketsFromEvents = (events) => {
    const markets = []

    events.forEach((event, index) => {
      const odds = event.odds || []
      if (odds.length < 2) return

      const matchName = parseEventName(event.event_name)
      const teams = matchName.split(' v ') || matchName.split(' vs ')

      // Market 1: Match Winner
      if (odds[0] && odds[0].back_odds) {
        const homeProb = Math.min(0.95, Math.max(0.05, 1 / odds[0].back_odds))
        markets.push({
          id: `${event.id}-winner`,
          eventId: event.id,
          question: `Will ${odds[0].selection_name} win?`,
          category: 'Football',
          competition: event.competition,
          matchName: matchName,
          endTime: event.start_time,
          isLive: event.is_live === 1,
          yesPrice: homeProb,
          noPrice: 1 - homeProb,
          volume: Math.floor(Math.random() * 50000) + 10000,
          liquidity: Math.floor(Math.random() * 100000) + 50000,
          iconType: 'football'
        })
      }

      // Market 2: Over 2.5 Goals (simulated)
      markets.push({
        id: `${event.id}-goals`,
        eventId: event.id,
        question: `Over 2.5 goals in ${matchName}?`,
        category: 'Football',
        competition: event.competition,
        matchName: matchName,
        endTime: event.start_time,
        isLive: event.is_live === 1,
        yesPrice: 0.45 + Math.random() * 0.2,
        noPrice: 0.35 + Math.random() * 0.2,
        volume: Math.floor(Math.random() * 30000) + 5000,
        liquidity: Math.floor(Math.random() * 80000) + 30000,
        iconType: 'goals'
      })

      // Market 3: Both Teams to Score
      markets.push({
        id: `${event.id}-btts`,
        eventId: event.id,
        question: `Both teams to score in ${matchName}?`,
        category: 'Football',
        competition: event.competition,
        matchName: matchName,
        endTime: event.start_time,
        isLive: event.is_live === 1,
        yesPrice: 0.50 + Math.random() * 0.15,
        noPrice: 0.35 + Math.random() * 0.15,
        volume: Math.floor(Math.random() * 25000) + 3000,
        liquidity: Math.floor(Math.random() * 60000) + 20000,
        iconType: 'btts'
      })
    })

    return markets
  }

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

  // Fetch markets
  const fetchMarkets = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/events?sport=football&data_type=exchange`)
      const events = await res.json()
      const generatedMarkets = generateMarketsFromEvents(events)
      setMarkets(generatedMarkets)
    } catch (err) {
      console.error('Error fetching markets:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchMarkets()
      setSelectedMarket(null)
      setSelectedOutcome(null)
      setShares('')
      setTradeResult(null)
    }
  }, [isOpen])

  // Select a market and outcome
  const selectMarket = (market, outcome) => {
    setSelectedMarket(market)
    setSelectedOutcome(outcome)
    setShares('')
    setTradeResult(null)
  }

  // Calculate cost and potential payout
  const sharePrice = selectedMarket && selectedOutcome
    ? (selectedOutcome === 'yes' ? selectedMarket.yesPrice : selectedMarket.noPrice)
    : 0
  const cost = shares ? (parseFloat(shares) * sharePrice).toFixed(2) : '0.00'
  const potentialPayout = shares ? parseFloat(shares).toFixed(2) : '0.00'
  const potentialProfit = shares ? (parseFloat(shares) - parseFloat(cost)).toFixed(2) : '0.00'

  // Place trade
  const placeTrade = async () => {
    if (!selectedMarket || !selectedOutcome || !shares || parseFloat(shares) <= 0) return

    setPlacingTrade(true)
    try {
      const res = await fetch(`${API_BASE}/api/bets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: selectedMarket.eventId,
          selection_name: `${selectedMarket.question} - ${selectedOutcome.toUpperCase()}`,
          odds: 1 / sharePrice,
          stake: parseFloat(cost),
          bet_type: 'back'
        })
      })
      const data = await res.json()
      if (data.success) {
        setTradeResult({ success: true, message: `Bought ${shares} shares at $${sharePrice.toFixed(2)}` })
        if (onBalanceChange) {
          onBalanceChange(data.new_balance)
        }
        setSelectedMarket(null)
        setSelectedOutcome(null)
        setShares('')
      } else {
        setTradeResult({ success: false, message: data.error || 'Trade failed' })
      }
    } catch (err) {
      console.error('Error placing trade:', err)
      setTradeResult({ success: false, message: 'Network error' })
    } finally {
      setPlacingTrade(false)
    }
  }

  // Filter markets
  const filteredMarkets = markets.filter(m => {
    if (filter === 'all') return true
    if (filter === 'trending') return m.volume > 20000
    return true
  })

  // Group by competition
  const groupedMarkets = filteredMarkets.reduce((acc, market) => {
    const comp = market.competition || 'Other'
    if (!acc[comp]) acc[comp] = []
    acc[comp].push(market)
    return acc
  }, {})

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-4 md:inset-8 bg-[#0d0d0d] rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-[#1a1a1a] px-6 py-4 flex items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <span className="text-white font-bold text-xl">Prediction Markets</span>
            </div>
            <div className="hidden md:flex items-center gap-2 ml-4">
              {['all', 'trending'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    filter === f
                      ? 'bg-white text-black'
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
                >
                  {f === 'all' ? '⚽ All Football' : '🔥 Trending'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="bg-white/10 px-4 py-2 rounded-lg">
              <span className="text-white/60 text-sm">Balance</span>
              <span className="text-white font-bold ml-2">${balance?.toFixed(2) || '0.00'}</span>
            </div>
            <button onClick={onClose} className="text-white/60 hover:text-white p-2 transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Markets Grid */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="flex items-center gap-3 text-white/60">
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Loading markets...</span>
                </div>
              </div>
            ) : markets.length === 0 ? (
              <div className="text-center text-white/60 py-16">
                <p className="text-lg">No markets available</p>
                <p className="text-sm mt-1">Check back later for new prediction markets</p>
              </div>
            ) : (
              <div className="space-y-8">
                {Object.entries(groupedMarkets).map(([competition, compMarkets]) => (
                  <div key={competition}>
                    <h3 className="text-white/40 text-xs font-semibold uppercase tracking-wider mb-4 flex items-center gap-2">
                      <span>⚽</span> {competition}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {compMarkets.map((market) => (
                        <div
                          key={market.id}
                          className="bg-[#1a1a1a] rounded-xl p-4 border border-white/5 hover:border-white/20 transition-all"
                        >
                          {/* Market Header */}
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              {market.isLive && (
                                <span className="inline-block px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full mb-2">
                                  🔴 LIVE
                                </span>
                              )}
                              <h4 className="text-white font-medium text-sm leading-tight">
                                {market.question}
                              </h4>
                              <p className="text-white/40 text-xs mt-1">{market.matchName}</p>
                            </div>
                          </div>

                          {/* Yes/No Buttons */}
                          <div className="grid grid-cols-2 gap-2 mb-3">
                            <button
                              onClick={() => selectMarket(market, 'yes')}
                              className={`p-3 rounded-lg transition-all ${
                                selectedMarket?.id === market.id && selectedOutcome === 'yes'
                                  ? 'bg-green-500/30 border-2 border-green-500'
                                  : 'bg-green-500/10 border border-green-500/30 hover:bg-green-500/20'
                              }`}
                            >
                              <div className="text-green-400 text-xs font-medium mb-1">Yes</div>
                              <div className="text-white font-bold text-lg">
                                {(market.yesPrice * 100).toFixed(0)}¢
                              </div>
                            </button>
                            <button
                              onClick={() => selectMarket(market, 'no')}
                              className={`p-3 rounded-lg transition-all ${
                                selectedMarket?.id === market.id && selectedOutcome === 'no'
                                  ? 'bg-red-500/30 border-2 border-red-500'
                                  : 'bg-red-500/10 border border-red-500/30 hover:bg-red-500/20'
                              }`}
                            >
                              <div className="text-red-400 text-xs font-medium mb-1">No</div>
                              <div className="text-white font-bold text-lg">
                                {(market.noPrice * 100).toFixed(0)}¢
                              </div>
                            </button>
                          </div>

                          {/* Volume */}
                          <div className="flex items-center justify-between text-xs text-white/40">
                            <span>${(market.volume / 1000).toFixed(0)}k Vol</span>
                            <span>{market.endTime || 'TBD'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Trade Panel */}
          <div className="w-80 bg-[#1a1a1a] border-l border-white/10 flex flex-col">
            <div className="p-4 border-b border-white/10">
              <h3 className="text-white font-semibold">Trade</h3>
            </div>

            <div className="flex-1 p-4 overflow-y-auto">
              {selectedMarket ? (
                <div className="space-y-4">
                  {/* Selected Market */}
                  <div className="bg-white/5 rounded-lg p-3">
                    <p className="text-white text-sm font-medium">{selectedMarket.question}</p>
                    <p className="text-white/40 text-xs mt-1">{selectedMarket.competition}</p>
                  </div>

                  {/* Outcome Selection */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setSelectedOutcome('yes')}
                      className={`p-2 rounded-lg text-sm font-medium transition-all ${
                        selectedOutcome === 'yes'
                          ? 'bg-green-500 text-white'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                      }`}
                    >
                      Buy Yes
                    </button>
                    <button
                      onClick={() => setSelectedOutcome('no')}
                      className={`p-2 rounded-lg text-sm font-medium transition-all ${
                        selectedOutcome === 'no'
                          ? 'bg-red-500 text-white'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                      }`}
                    >
                      Buy No
                    </button>
                  </div>

                  {selectedOutcome && (
                    <>
                      {/* Price Display */}
                      <div className="bg-white/5 rounded-lg p-3 text-center">
                        <p className="text-white/40 text-xs">Price per share</p>
                        <p className={`text-2xl font-bold ${
                          selectedOutcome === 'yes' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          ${sharePrice.toFixed(2)}
                        </p>
                        <p className="text-white/40 text-xs mt-1">
                          {(sharePrice * 100).toFixed(0)}% implied probability
                        </p>
                      </div>

                      {/* Shares Input */}
                      <div>
                        <label className="block text-white/60 text-sm mb-2">Shares</label>
                        <input
                          type="number"
                          value={shares}
                          onChange={(e) => setShares(e.target.value)}
                          placeholder="0"
                          min="1"
                          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-lg font-mono focus:outline-none focus:border-white/30"
                        />
                      </div>

                      {/* Quick Amounts */}
                      <div className="grid grid-cols-4 gap-2">
                        {[10, 25, 50, 100].map((amount) => (
                          <button
                            key={amount}
                            onClick={() => setShares(amount.toString())}
                            className="py-2 text-xs bg-white/10 hover:bg-white/20 rounded-lg text-white/70 transition-colors"
                          >
                            {amount}
                          </button>
                        ))}
                      </div>

                      {/* Cost Summary */}
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between text-white/60">
                          <span>Cost</span>
                          <span className="text-white">${cost}</span>
                        </div>
                        <div className="flex justify-between text-white/60">
                          <span>Potential Payout</span>
                          <span className="text-white">${potentialPayout}</span>
                        </div>
                        <div className="flex justify-between font-medium">
                          <span className="text-white/60">Potential Profit</span>
                          <span className="text-green-400">+${potentialProfit}</span>
                        </div>
                      </div>

                      {/* Trade Button */}
                      <button
                        onClick={placeTrade}
                        disabled={!shares || parseFloat(shares) <= 0 || placingTrade}
                        className={`w-full py-3 rounded-lg font-bold transition-colors ${
                          !shares || parseFloat(shares) <= 0 || placingTrade
                            ? 'bg-white/10 text-white/30 cursor-not-allowed'
                            : selectedOutcome === 'yes'
                              ? 'bg-green-500 hover:bg-green-600 text-white'
                              : 'bg-red-500 hover:bg-red-600 text-white'
                        }`}
                      >
                        {placingTrade ? (
                          <span className="flex items-center justify-center gap-2">
                            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Processing...
                          </span>
                        ) : (
                          `Buy ${selectedOutcome === 'yes' ? 'Yes' : 'No'} Shares`
                        )}
                      </button>
                    </>
                  )}

                  {/* Trade Result */}
                  {tradeResult && (
                    <div className={`p-3 rounded-lg text-sm ${
                      tradeResult.success
                        ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                        : 'bg-red-500/20 text-red-400 border border-red-500/30'
                    }`}>
                      {tradeResult.message}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-white/40 py-12">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  <p className="font-medium">Select a market</p>
                  <p className="text-sm mt-1">Click Yes or No on any market to trade</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/10">
              <p className="text-xs text-white/30 text-center">
                Shares pay $1 if correct, $0 if wrong.
                <br />Trade responsibly.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
