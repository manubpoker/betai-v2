import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { useState } from 'react'
import Exchange from './pages/Exchange'
import Sportsbook from './pages/Sportsbook'
import Casino from './pages/Casino'
import Poker from './pages/Poker'
import AIChatPanel from './components/AIChatPanel'

function App() {
  const [chatOpen, setChatOpen] = useState(false)

  const navItems = [
    { path: '/', label: 'Exchange' },
    { path: '/sportsbook', label: 'Sportsbook' },
    { path: '/casino', label: 'Casino' },
    { path: '/poker', label: 'Poker' },
  ]

  return (
    <Router>
      <div className="min-h-screen bg-dark-navy">
        {/* Header */}
        <header className="bg-dark-navy border-b border-gray-700">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              {/* Logo */}
              <div className="flex items-center">
                <span className="text-2xl font-bold text-betfair-gold">BetAI</span>
                <span className="ml-2 text-xs bg-ai-accent px-2 py-0.5 rounded">v2</span>
              </div>

              {/* Navigation */}
              <nav className="flex space-x-1">
                {navItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `px-4 py-2 rounded-lg font-medium transition-colors ${
                        isActive
                          ? 'bg-betfair-gold text-dark-navy'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>

              {/* Right section */}
              <div className="flex items-center space-x-4">
                <span className="text-gray-400 text-sm">Real Data from Betfair</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Exchange />} />
            <Route path="/sportsbook" element={<Sportsbook />} />
            <Route path="/casino" element={<Casino />} />
            <Route path="/poker" element={<Poker />} />
          </Routes>
        </main>

        {/* AI Chat Floating Button */}
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-ai-accent rounded-full shadow-lg
                     flex items-center justify-center hover:bg-ai-accent/80 transition-colors
                     z-40"
          title="Chat with AI Assistant"
        >
          <svg
            className="w-6 h-6 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </button>

        {/* AI Chat Panel */}
        <AIChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />
      </div>
    </Router>
  )
}

export default App
