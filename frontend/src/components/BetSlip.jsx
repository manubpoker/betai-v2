import { useState } from 'react'
import { API_BASE } from '../config'

export default function BetSlip({ bets, onRemove, onUpdateStake, onClear, balance, onBalanceChange }) {
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

  // Calculate total required (considering liability for lay bets)
  const totalRequired = bets.reduce((sum, bet) => {
    const stake = parseFloat(bet.stake) || 0
    if (bet.type === 'back') {
      return sum + stake
    } else {
      return sum + (stake * (bet.odds - 1)) // liability
    }
  }, 0)

  // Place bets
  const placeBets = async () => {
    if (bets.length === 0 || bets.some(b => !b.stake || parseFloat(b.stake) <= 0)) {
      setMessage({ type: 'error', text: 'Please enter stake for all selections' })
      return
    }

    // Check balance before placing
    if (balance !== null && totalRequired > balance) {
      setMessage({ type: 'error', text: `Insufficient balance. Required: £${totalRequired.toFixed(2)}` })
      return
    }

    setPlacing(true)
    setMessage(null)

    try {
      for (const bet of bets) {
        const res = await fetch(`${API_BASE}/api/bets`, {
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

        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.error || 'Failed to place bet')
        }
      }

      setMessage({ type: 'success', text: 'Bets placed successfully!' })
      // Fetch updated balance
      try {
        const balRes = await fetch(`${API_BASE}/api/balance`)
        const balData = await balRes.json()
        if (onBalanceChange) onBalanceChange(balData.balance)
      } catch (e) { /* ignore */ }
      onClear()
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to place bets. Please try again.' })
    } finally {
      setPlacing(false)
    }
  }

  return (
    <div className="bf-card sticky top-4">
      {/* Header - Betfair yellow */}
      <div className="betslip-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>Bet Slip</span>
          {bets.length > 0 && (
            <span className="bg-betfair-black text-white text-xs px-1.5 py-0.5 rounded">
              {bets.length}
            </span>
          )}
        </div>
        {bets.length > 0 && (
          <button
            onClick={onClear}
            className="text-sm text-betfair-black/70 hover:text-betfair-black font-medium"
          >
            Clear
          </button>
        )}
      </div>

      {/* Bets */}
      <div className="p-3">
        {bets.length === 0 ? (
          <div className="text-center py-6">
            <div className="text-betfair-gray text-sm">
              Click on odds to add selections
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {bets.map((bet) => (
              <div key={bet.id} className="bg-gray-50 rounded border border-gray-200 p-3">
                {/* Bet header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 mr-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                        bet.type === 'back'
                          ? 'bg-back-blue-deep text-betfair-black'
                          : 'bg-lay-pink-deep text-betfair-black'
                      }`}>
                        {bet.type.toUpperCase()}
                      </span>
                      <span className="font-mono text-betfair-yellow font-bold bg-betfair-black px-2 py-0.5 rounded text-sm">
                        {bet.odds.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-betfair-black font-medium text-sm mt-1">{bet.selection}</p>
                    <p className="text-betfair-gray text-xs">{bet.eventName}</p>
                  </div>
                  <button
                    onClick={() => onRemove(bet.id)}
                    className="text-gray-400 hover:text-error p-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Stake input */}
                <div className="flex items-center gap-2">
                  <span className="text-betfair-gray text-sm">£</span>
                  <input
                    type="number"
                    placeholder="Stake"
                    value={bet.stake}
                    onChange={(e) => onUpdateStake(bet.id, e.target.value)}
                    className="bf-input text-sm"
                  />
                </div>

                {/* Return calculation */}
                {bet.stake && parseFloat(bet.stake) > 0 && (
                  <div className="mt-2 text-xs">
                    {bet.type === 'back' ? (
                      <div className="flex justify-between text-betfair-gray">
                        <span>Potential return:</span>
                        <span className="text-success font-bold">
                          £{calculateReturn(bet).toFixed(2)}
                        </span>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex justify-between text-betfair-gray">
                          <span>Liability:</span>
                          <span className="text-error font-bold">
                            £{calculateLiability(bet).toFixed(2)}
                          </span>
                        </div>
                        <div className="flex justify-between text-betfair-gray">
                          <span>Potential profit:</span>
                          <span className="text-success font-bold">
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
          <div className="mt-4 pt-3 border-t border-gray-200">
            <div className="flex justify-between text-sm text-betfair-gray mb-1">
              <span>Total stake:</span>
              <span className="font-bold text-betfair-black">£{totalStake.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm text-betfair-gray mb-3">
              <span>Potential return:</span>
              <span className="font-bold text-success">£{totalReturn.toFixed(2)}</span>
            </div>

            {message && (
              <div className={`mb-3 p-2 rounded text-xs font-medium ${
                message.type === 'success'
                  ? 'bg-green-100 text-green-700 border border-green-200'
                  : 'bg-red-100 text-red-700 border border-red-200'
              }`}>
                {message.text}
              </div>
            )}

            <button
              onClick={placeBets}
              disabled={placing}
              className="w-full bf-btn-primary py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {placing ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Placing...
                </span>
              ) : (
                'Place Bets'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
