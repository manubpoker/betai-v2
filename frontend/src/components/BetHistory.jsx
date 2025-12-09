import { useState, useEffect } from 'react'

const API_BASE = ''

export default function BetHistory({ isOpen, onClose }) {
  const [bets, setBets] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, pending, won, lost

  // Fetch bet history
  useEffect(() => {
    if (!isOpen) return

    async function fetchData() {
      setLoading(true)
      try {
        const [betsRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/bets/history`),
          fetch(`${API_BASE}/api/bets/stats`)
        ])
        const betsData = await betsRes.json()
        const statsData = await statsRes.json()
        setBets(betsData.bets || [])
        setStats(statsData)
      } catch (err) {
        console.error('Error fetching bet history:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [isOpen])

  // Filter bets
  const filteredBets = bets.filter(bet => {
    if (filter === 'all') return true
    if (filter === 'pending') return bet.result === null || bet.result === 'pending'
    if (filter === 'won') return bet.result === 'won'
    if (filter === 'lost') return bet.result === 'lost'
    return true
  })

  // Format date
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-4 md:inset-x-20 md:inset-y-10 bg-gray-800 rounded-lg z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-betfair-gold px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-dark-navy">Bet History</h2>
          <button
            onClick={onClose}
            className="text-dark-navy/70 hover:text-dark-navy"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Stats Summary */}
        {stats && (
          <div className="px-6 py-4 bg-gray-900 border-b border-gray-700">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center">
                <p className="text-gray-400 text-xs">Total Bets</p>
                <p className="text-white text-lg font-bold">{stats.total_bets}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-xs">Won</p>
                <p className="text-success text-lg font-bold">{stats.won}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-xs">Lost</p>
                <p className="text-error text-lg font-bold">{stats.lost}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-xs">Pending</p>
                <p className="text-betfair-gold text-lg font-bold">{stats.pending}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-xs">Net P/L</p>
                <p className={`text-lg font-bold ${stats.net_profit_loss >= 0 ? 'text-success' : 'text-error'}`}>
                  {stats.net_profit_loss >= 0 ? '+' : ''}£{stats.net_profit_loss?.toFixed(2) || '0.00'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="px-6 py-3 border-b border-gray-700 flex gap-2">
          {['all', 'pending', 'won', 'lost'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-betfair-gold text-dark-navy'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Bets List */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : filteredBets.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-gray-400 text-center">
                <p>No bets found</p>
                <p className="text-sm mt-1">Place some bets to see them here</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredBets.map(bet => (
                <div
                  key={bet.id}
                  className={`bg-gray-700 rounded-lg p-4 border-l-4 ${
                    bet.result === 'won'
                      ? 'border-success'
                      : bet.result === 'lost'
                        ? 'border-error'
                        : 'border-betfair-gold'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                          bet.bet_type === 'back'
                            ? 'bg-back-blue text-dark-navy'
                            : 'bg-lay-pink text-dark-navy'
                        }`}>
                          {bet.bet_type?.toUpperCase()}
                        </span>
                        <span className="font-mono text-betfair-gold font-medium">
                          @{bet.odds?.toFixed(2)}
                        </span>
                        {bet.result && bet.result !== 'pending' && (
                          <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                            bet.result === 'won'
                              ? 'bg-success/20 text-success'
                              : 'bg-error/20 text-error'
                          }`}>
                            {bet.result.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <p className="text-white font-medium">{bet.selection_name}</p>
                      <p className="text-gray-400 text-sm">{bet.event_name}</p>
                      <p className="text-gray-500 text-xs mt-1">{formatDate(bet.placed_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-400 text-xs">Stake</p>
                      <p className="text-white font-medium">£{bet.stake?.toFixed(2)}</p>
                      {bet.profit_loss !== null && bet.profit_loss !== undefined && (
                        <>
                          <p className="text-gray-400 text-xs mt-2">P/L</p>
                          <p className={`font-medium ${bet.profit_loss >= 0 ? 'text-success' : 'text-error'}`}>
                            {bet.profit_loss >= 0 ? '+' : ''}£{bet.profit_loss.toFixed(2)}
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
