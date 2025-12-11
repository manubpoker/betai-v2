import { useState, useEffect } from 'react'
import { API_BASE } from '../config'

export default function AIBetFeed({ isOpen, onClose, onRefresh, onBalanceChange }) {
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [generatedAt, setGeneratedAt] = useState(null)
  const [placingBet, setPlacingBet] = useState(null) // track which bet is being placed
  const [betStatus, setBetStatus] = useState({}) // track success/error per recommendation
  const [expandedReason, setExpandedReason] = useState(null) // track which reason is expanded

  // Fetch recommendations
  const fetchRecommendations = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/ai/bet-feed`)
      const data = await res.json()
      setRecommendations(data.recommendations || [])
      setGeneratedAt(data.generated_at)
    } catch (err) {
      console.error('Error fetching bet feed:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchRecommendations()
      setBetStatus({}) // Clear bet status when panel opens
    }
  }, [isOpen, onRefresh])

  // Place a bet from recommendation
  const placeBet = async (rec, index) => {
    setPlacingBet(index)
    try {
      const res = await fetch(`${API_BASE}/api/bets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: rec.event_id,
          selection_name: rec.side,
          odds: rec.odds,
          stake: rec.stake,
          bet_type: 'back'
        })
      })
      const data = await res.json()
      if (data.success) {
        setBetStatus(prev => ({ ...prev, [index]: 'success' }))
        // Notify parent to update balance
        if (onBalanceChange) {
          onBalanceChange(data.new_balance)
        }
      } else {
        setBetStatus(prev => ({ ...prev, [index]: data.error || 'Failed' }))
      }
    } catch (err) {
      console.error('Error placing bet:', err)
      setBetStatus(prev => ({ ...prev, [index]: 'Error placing bet' }))
    } finally {
      setPlacingBet(null)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel - slides in from left */}
      <div className="fixed top-0 left-0 h-full w-96 bg-gray-800 shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="bg-ai-accent px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h2 className="font-bold text-white">AI Bet Feed</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchRecommendations}
              className="text-white/70 hover:text-white p-1"
              title="Refresh recommendations"
            >
              <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={onClose}
              className="text-white/70 hover:text-white"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Subtitle */}
        <div className="px-4 py-2 bg-gray-900 border-b border-gray-700 text-xs text-gray-400">
          <span className="text-ai-accent">Powered by Opus 4.5</span> • Back bets only
          {generatedAt && (
            <span className="ml-2">
              • Updated: {new Date(generatedAt).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Recommendations List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="flex items-center gap-2 text-gray-400">
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Generating recommendations...</span>
              </div>
            </div>
          ) : recommendations.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <p>No recommendations available</p>
              <p className="text-sm mt-1">Refresh odds to get new picks</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recommendations.map((rec, index) => (
                <div
                  key={index}
                  className="bg-gray-700 rounded-lg p-3 border-l-4 border-ai-accent hover:bg-gray-650 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-white text-sm font-medium">
                        {rec.text}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-600 text-gray-300">
                          {rec.sport}
                        </span>
                        <span className="text-xs text-betfair-gold font-mono">
                          @{rec.odds?.toFixed(2)}
                        </span>
                        {rec.reason && (
                          <button
                            onClick={() => setExpandedReason(expandedReason === index ? null : index)}
                            className="text-xs text-ai-accent hover:text-ai-accent/80 hover:underline"
                          >
                            why?
                          </button>
                        )}
                      </div>
                      {/* Expanded reason */}
                      {expandedReason === index && rec.reason && (
                        <div className="mt-2 text-xs text-gray-300 bg-gray-800 rounded px-2 py-1.5 italic">
                          💡 {rec.reason}
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0">
                      {betStatus[index] === 'success' ? (
                        <span className="text-xs px-3 py-1.5 rounded bg-success/20 text-success font-medium">
                          Placed!
                        </span>
                      ) : betStatus[index] ? (
                        <span className="text-xs px-2 py-1 rounded bg-error/20 text-error">
                          {betStatus[index]}
                        </span>
                      ) : (
                        <button
                          onClick={() => placeBet(rec, index)}
                          disabled={placingBet === index}
                          className={`text-xs px-3 py-1.5 rounded font-medium transition-colors ${
                            placingBet === index
                              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                              : 'bg-back-blue text-dark-navy hover:bg-back-blue/80'
                          }`}
                        >
                          {placingBet === index ? (
                            <span className="flex items-center gap-1">
                              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                              Placing...
                            </span>
                          ) : (
                            'Place Bet'
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-gray-900 border-t border-gray-700">
          <p className="text-xs text-gray-500 text-center">
            AI recommendations are for entertainment only.
            <br />Gamble responsibly.
          </p>
        </div>
      </div>
    </>
  )
}
