import { useState, useEffect, useRef } from 'react'
import { API_BASE } from '../config'
import ReactMarkdown from 'react-markdown'

export default function SaferGamingAgent({ isOpen, onClose }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [activity, setActivity] = useState(null)
  const [showTools, setShowTools] = useState(false)
  const [settingLimit, setSettingLimit] = useState(null)
  const [limitValue, setLimitValue] = useState('')
  const [limitPeriod, setLimitPeriod] = useState('daily')
  const messagesEndRef = useRef(null)

  // Fetch player activity on mount
  useEffect(() => {
    if (isOpen) {
      fetchActivity()
      // Send initial greeting
      if (messages.length === 0) {
        sendMessage("Hi, I'd like to review my gambling activity and learn about safer gaming tools.")
      }
    }
  }, [isOpen])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchActivity = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/safer-gaming/activity`)
      const data = await res.json()
      setActivity(data)
    } catch (err) {
      console.error('Error fetching activity:', err)
    }
  }

  const sendMessage = async (messageText) => {
    const text = messageText || input.trim()
    if (!text || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/api/safer-gaming/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId
        })
      })
      const data = await res.json()

      if (data.response) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
        if (data.conversation_id) {
          setConversationId(data.conversation_id)
        }
      } else if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }])
      }
    } catch (err) {
      console.error('Error sending message:', err)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error connecting to the service.' }])
    } finally {
      setLoading(false)
    }
  }

  const setLimit = async (type) => {
    if (!limitValue) return

    try {
      const res = await fetch(`${API_BASE}/api/safer-gaming/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          setting_type: type,
          value: parseFloat(limitValue),
          period: limitPeriod,
          enabled: true
        })
      })
      const data = await res.json()

      if (data.success) {
        setSettingLimit(null)
        setLimitValue('')
        fetchActivity()
        sendMessage(`I've set a ${limitPeriod} ${type.replace('_', ' ')} of £${limitValue}. Can you confirm this is now active?`)
      }
    } catch (err) {
      console.error('Error setting limit:', err)
    }
  }

  const setTimeoutPeriod = async (hours) => {
    try {
      const res = await fetch(`${API_BASE}/api/safer-gaming/timeout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration_hours: hours })
      })
      const data = await res.json()

      if (data.success) {
        const duration = hours >= 24 ? `${hours / 24} day${hours > 24 ? 's' : ''}` : `${hours} hours`
        sendMessage(`I've taken a timeout for ${duration}. Please confirm when this will end.`)
      }
    } catch (err) {
      console.error('Error setting timeout:', err)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-gray-900 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-teal-600 px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Safer Gaming Agent</h1>
            <p className="text-white/70 text-sm">Your responsible gambling assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowTools(!showTools)}
            className="px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Tools
          </button>
          <button
            onClick={onClose}
            className="p-2 text-white/70 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Activity Summary Bar */}
          {activity && (
            <div className="bg-gray-800 px-6 py-3 flex items-center gap-6 text-sm border-b border-gray-700">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Balance:</span>
                <span className={`font-bold ${activity.current_balance >= activity.starting_balance ? 'text-green-400' : 'text-red-400'}`}>
                  £{activity.current_balance?.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Total Bets:</span>
                <span className="text-white font-medium">{activity.total_bets}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Net P/L:</span>
                <span className={`font-bold ${activity.net_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {activity.net_profit_loss >= 0 ? '+' : ''}£{activity.net_profit_loss?.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Win Rate:</span>
                <span className="text-white font-medium">{activity.win_rate?.toFixed(1)}%</span>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-2xl px-5 py-3 ${
                    msg.role === 'user'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-2xl px-5 py-3 flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 bg-gray-800 border-t border-gray-700">
            <div className="max-w-4xl mx-auto flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about your gambling activity or safer gaming tools..."
                className="flex-1 bg-gray-700 text-white rounded-xl px-5 py-3 focus:outline-none focus:ring-2 focus:ring-green-500 placeholder-gray-400"
                disabled={loading}
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Tools Sidebar */}
        {showTools && (
          <div className="w-80 bg-gray-800 border-l border-gray-700 overflow-y-auto">
            <div className="p-4 space-y-4">
              <h3 className="text-white font-bold text-lg mb-4">Safer Gaming Tools</h3>

              {/* Deposit Limit */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-white font-medium flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Deposit Limit
                </h4>
                {settingLimit === 'deposit_limit' ? (
                  <div className="space-y-2">
                    <input
                      type="number"
                      value={limitValue}
                      onChange={(e) => setLimitValue(e.target.value)}
                      placeholder="Amount (£)"
                      className="w-full bg-gray-600 text-white rounded px-3 py-2 text-sm"
                    />
                    <select
                      value={limitPeriod}
                      onChange={(e) => setLimitPeriod(e.target.value)}
                      className="w-full bg-gray-600 text-white rounded px-3 py-2 text-sm"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setLimit('deposit_limit')}
                        className="flex-1 bg-green-600 text-white rounded py-2 text-sm hover:bg-green-700"
                      >
                        Set
                      </button>
                      <button
                        onClick={() => setSettingLimit(null)}
                        className="flex-1 bg-gray-600 text-white rounded py-2 text-sm hover:bg-gray-500"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-gray-400 text-sm mb-2">Limit how much you can deposit</p>
                    {activity?.limits?.deposit_limit ? (
                      <p className="text-green-400 text-sm mb-2">
                        Active: £{activity.limits.deposit_limit} / {activity.limits.deposit_limit_period}
                      </p>
                    ) : null}
                    <button
                      onClick={() => setSettingLimit('deposit_limit')}
                      className="w-full bg-gray-600 text-white rounded py-2 text-sm hover:bg-gray-500"
                    >
                      Set Limit
                    </button>
                  </>
                )}
              </div>

              {/* Loss Limit */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-white font-medium flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                  </svg>
                  Loss Limit
                </h4>
                {settingLimit === 'loss_limit' ? (
                  <div className="space-y-2">
                    <input
                      type="number"
                      value={limitValue}
                      onChange={(e) => setLimitValue(e.target.value)}
                      placeholder="Amount (£)"
                      className="w-full bg-gray-600 text-white rounded px-3 py-2 text-sm"
                    />
                    <select
                      value={limitPeriod}
                      onChange={(e) => setLimitPeriod(e.target.value)}
                      className="w-full bg-gray-600 text-white rounded px-3 py-2 text-sm"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setLimit('loss_limit')}
                        className="flex-1 bg-green-600 text-white rounded py-2 text-sm hover:bg-green-700"
                      >
                        Set
                      </button>
                      <button
                        onClick={() => setSettingLimit(null)}
                        className="flex-1 bg-gray-600 text-white rounded py-2 text-sm hover:bg-gray-500"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-gray-400 text-sm mb-2">Limit how much you can lose</p>
                    {activity?.limits?.loss_limit ? (
                      <p className="text-red-400 text-sm mb-2">
                        Active: £{activity.limits.loss_limit} / {activity.limits.loss_limit_period}
                      </p>
                    ) : null}
                    <button
                      onClick={() => setSettingLimit('loss_limit')}
                      className="w-full bg-gray-600 text-white rounded py-2 text-sm hover:bg-gray-500"
                    >
                      Set Limit
                    </button>
                  </>
                )}
              </div>

              {/* Timeout */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-white font-medium flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Take a Break
                </h4>
                <p className="text-gray-400 text-sm mb-3">Block access to your account</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setTimeoutPeriod(24)}
                    className="bg-gray-600 text-white rounded py-2 text-sm hover:bg-yellow-600"
                  >
                    24 Hours
                  </button>
                  <button
                    onClick={() => setTimeoutPeriod(48)}
                    className="bg-gray-600 text-white rounded py-2 text-sm hover:bg-yellow-600"
                  >
                    48 Hours
                  </button>
                  <button
                    onClick={() => setTimeoutPeriod(168)}
                    className="bg-gray-600 text-white rounded py-2 text-sm hover:bg-yellow-600"
                  >
                    7 Days
                  </button>
                  <button
                    onClick={() => setTimeoutPeriod(720)}
                    className="bg-gray-600 text-white rounded py-2 text-sm hover:bg-yellow-600"
                  >
                    30 Days
                  </button>
                </div>
              </div>

              {/* Reality Check */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-white font-medium flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                  Reality Check
                </h4>
                <p className="text-gray-400 text-sm mb-3">Get reminders during sessions</p>
                <button
                  onClick={() => sendMessage("I'd like to set up reality check reminders. What options do I have?")}
                  className="w-full bg-gray-600 text-white rounded py-2 text-sm hover:bg-blue-600"
                >
                  Configure
                </button>
              </div>

              {/* Help & Support */}
              <div className="bg-red-900/30 rounded-lg p-4 border border-red-800">
                <h4 className="text-white font-medium flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                  Need Help?
                </h4>
                <p className="text-gray-300 text-sm mb-3">Support is available 24/7</p>
                <div className="space-y-2 text-sm">
                  <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" className="block text-blue-400 hover:underline">
                    BeGambleAware.org
                  </a>
                  <p className="text-gray-400">GamCare: 0808 8020 133</p>
                  <p className="text-gray-400">US: 1-800-522-4700</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
