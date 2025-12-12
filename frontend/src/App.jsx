import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Exchange from './pages/Exchange'
import AIChatPanel from './components/AIChatPanel'
import AIBetFeed from './components/AIBetFeed'
import { API_BASE } from './config'

function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [betFeedOpen, setBetFeedOpen] = useState(false)
  const [betFeedRefresh, setBetFeedRefresh] = useState(0)
  const [balance, setBalance] = useState(1000.00)

  // Fetch balance on mount
  useEffect(() => {
    async function fetchBalance() {
      try {
        const res = await fetch(`${API_BASE}/api/balance`)
        const data = await res.json()
        setBalance(data.balance)
      } catch (err) {
        console.error('Error fetching balance:', err)
      }
    }
    fetchBalance()
  }, [])

  return (
    <Router>
      <div className="min-h-screen bg-betfair-light">
        {/* Top Yellow Header Bar */}
        <header className="bg-betfair-yellow">
          <div className="max-w-[1400px] mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              {/* Logo */}
              <div className="flex items-center">
                <img
                  src="/images/betfair-logo.png"
                  alt="Betfair"
                  className="h-8"
                  onError={(e) => {
                    e.target.style.display = 'none'
                    e.target.nextSibling.style.display = 'flex'
                  }}
                />
                <div className="hidden items-center">
                  <svg className="h-6 w-6 mr-1" viewBox="0 0 24 24" fill="#333">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                  </svg>
                  <span className="text-2xl font-bold text-betfair-black">betfair</span>
                </div>
                <span className="ml-2 text-xs bg-ai-accent text-white px-2 py-0.5 rounded font-medium">AI</span>
              </div>

              {/* Right section - Balance & Account */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 bg-white/20 px-3 py-1.5 rounded">
                  <span className="text-betfair-black text-sm font-medium">Balance:</span>
                  <span className="text-betfair-black font-bold">£{balance.toFixed(2)}</span>
                </div>
                <button className="bg-betfair-black text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-betfair-dark transition-colors">
                  Deposit
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Secondary Navigation Bar */}
        <nav className="bg-betfair-black">
          <div className="max-w-[1400px] mx-auto px-4">
            <div className="flex items-center justify-between h-12">
              {/* Main Navigation */}
              <div className="flex items-center gap-1">
                <span className="px-4 py-2 text-betfair-yellow font-semibold border-b-2 border-betfair-yellow">
                  Exchange
                </span>
                <button
                  onClick={() => setBetFeedOpen(true)}
                  className="px-4 py-2 text-white/80 hover:text-white font-medium flex items-center gap-2 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  AI Picks
                </button>
              </div>

              {/* AI Status Indicator */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setChatOpen(true)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-ai-accent/20 text-ai-accent rounded hover:bg-ai-accent/30 transition-colors text-sm font-medium"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  AI Assistant
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="max-w-[1400px] mx-auto px-4 py-4">
          <Routes>
            <Route path="/" element={<Exchange balance={balance} onBalanceChange={setBalance} />} />
            <Route path="*" element={<Exchange balance={balance} onBalanceChange={setBalance} />} />
          </Routes>
        </main>

        {/* AI Chat Panel */}
        <AIChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />

        {/* AI Bet Feed Panel */}
        <AIBetFeed
          isOpen={betFeedOpen}
          onClose={() => setBetFeedOpen(false)}
          onRefresh={betFeedRefresh}
          onBalanceChange={setBalance}
        />
      </div>
    </Router>
  )
}

export default App
