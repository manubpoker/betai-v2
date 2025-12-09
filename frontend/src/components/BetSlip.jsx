import { useState } from 'react'

const API_BASE = ''

export default function BetSlip({ bets, onRemove, onUpdateStake, onClear }) {
  const [placing, setPlacing] = useState(false)
  const [message, setMessage] = useState(null)

  // Calculate potential return for a bet
  const calculateReturn = (bet) => {
    const stake = parseFloat(bet.stake) || 0
    if (bet.type === 'back') {
      return stake * bet.odds
    } else {
      // Lay bet - profit is the stake
      return stake
    }
  }

  // Calculate liability for lay bet
  const calculateLiability = (bet) => {
    const stake = parseFloat(bet.stake) || 0
    if (bet.type === 'lay') {
      return stake * (bet.odds - 1)
    }
    return 0
  }

  // Total stake
  const totalStake = bets.reduce((sum, bet) => sum + (parseFloat(bet.stake) || 0), 0)

  // Total potential return
  const totalReturn = bets.reduce((sum, bet) => sum + calculateReturn(bet), 0)

  // Place bets
  const placeBets = async () => {
    if (bets.length === 0 || bets.some(b => !b.stake || parseFloat(b.stake) <= 0)) {
      setMessage({ type: 'error', text: 'Please enter stake for all selections' })
      return
    }

    setPlacing(true)
    setMessage(null)

    try {
      for (const bet of bets) {
        await fetch(`${API_BASE}/api/bets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_id: bet.eventId,
            selection_name: bet.selection,
            bet_type: bet.type,
            odds: bet.odds,
            stake: parseFloat(bet.stake),
          }),
        })
      }

      setMessage({ type: 'success', text: 'Bets placed successfully!' })
      onClear()
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to place bets. Please try again.' })
    } finally {
      setPlacing(false)
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden sticky top-4">
      {/* Header */}
      <div className="bg-betfair-gold px-4 py-3 flex items-center justify-between">
        <h2 className="font-bold text-dark-navy">Bet Slip</h2>
        {bets.length > 0 && (
          <button
            onClick={onClear}
            className="text-sm text-dark-navy/70 hover:text-dark-navy"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Bets */}
      <div className="p-4">
        {bets.length === 0 ? (
          <p className="text-gray-400 text-center py-4">
            Click on odds to add selections
          </p>
        ) : (
          <div className="space-y-4">
            {bets.map((bet) => (
              <div key={bet.id} className="bg-gray-700 rounded-lg p-3">
                {/* Bet header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 mr-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        bet.type === 'back'
                          ? 'bg-back-blue text-dark-navy'
                          : 'bg-lay-pink text-dark-navy'
                      }`}>
                        {bet.type.toUpperCase()}
                      </span>
                      <span className="font-mono text-betfair-gold font-medium">
                        {bet.odds.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-white text-sm mt-1">{bet.selection}</p>
                    <p className="text-gray-400 text-xs">{bet.eventName}</p>
                  </div>
                  <button
                    onClick={() => onRemove(bet.id)}
                    className="text-gray-400 hover:text-error"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Stake input */}
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">£</span>
                  <input
                    type="number"
                    placeholder="Stake"
                    value={bet.stake}
                    onChange={(e) => onUpdateStake(bet.id, e.target.value)}
                    className="flex-1 bg-gray-600 border border-gray-500 rounded px-3 py-2
                             text-white placeholder-gray-400 focus:outline-none focus:border-betfair-gold"
                  />
                </div>

                {/* Return calculation */}
                {bet.stake && parseFloat(bet.stake) > 0 && (
                  <div className="mt-2 text-sm">
                    {bet.type === 'back' ? (
                      <div className="flex justify-between text-gray-300">
                        <span>Potential return:</span>
                        <span className="text-success font-medium">
                          £{calculateReturn(bet).toFixed(2)}
                        </span>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex justify-between text-gray-300">
                          <span>Liability:</span>
                          <span className="text-error font-medium">
                            £{calculateLiability(bet).toFixed(2)}
                          </span>
                        </div>
                        <div className="flex justify-between text-gray-300">
                          <span>Potential profit:</span>
                          <span className="text-success font-medium">
                            £{calculateReturn(bet).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Totals and place bet */}
        {bets.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex justify-between text-gray-300 mb-2">
              <span>Total stake:</span>
              <span className="font-medium">£{totalStake.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-300 mb-4">
              <span>Potential return:</span>
              <span className="font-medium text-success">£{totalReturn.toFixed(2)}</span>
            </div>

            {message && (
              <div className={`mb-4 p-3 rounded text-sm ${
                message.type === 'success'
                  ? 'bg-success/20 text-success'
                  : 'bg-error/20 text-error'
              }`}>
                {message.text}
              </div>
            )}

            <button
              onClick={placeBets}
              disabled={placing}
              className="w-full py-3 bg-betfair-gold text-dark-navy font-bold rounded-lg
                       hover:bg-betfair-gold/80 transition-colors disabled:opacity-50"
            >
              {placing ? 'Placing...' : 'Place Bets'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
