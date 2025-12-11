import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { API_BASE } from '../config'

export default function AIChatPanel({ isOpen, onClose, initialMessage = null, eventContext = null }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [status, setStatus] = useState({ loading: true, connected: false, model: null })
  const [conversationId, setConversationId] = useState(null)
  const [processedInitialMessage, setProcessedInitialMessage] = useState(null)
  const messagesEndRef = useRef(null)

  // Check AI status on mount (not just when opened) to maintain permanent connection
  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await fetch(`${API_BASE}/api/verify/ai-status`)
        const data = await res.json()
        setStatus({
          loading: false,
          connected: data.status === 'connected',
          model: data.model,
          error: data.error,
        })
      } catch (err) {
        setStatus({
          loading: false,
          connected: false,
          model: null,
          error: 'Failed to connect to backend',
        })
      }
    }
    // Check immediately on mount
    checkStatus()

    // Re-check periodically to maintain connection status
    const interval = setInterval(checkStatus, 30000) // Every 30 seconds
    return () => clearInterval(interval)
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-send initial message when panel opens with one
  useEffect(() => {
    if (isOpen && initialMessage && status.connected && initialMessage !== processedInitialMessage) {
      setProcessedInitialMessage(initialMessage)
      // Start a new conversation for Match Intelligence
      setMessages([])
      setConversationId(null)
      // Auto-send the message
      sendMessageWithContext(initialMessage, eventContext)
    }
  }, [isOpen, initialMessage, status.connected])

  // Send message with optional event context
  const sendMessageWithContext = async (messageText, context = null) => {
    if (!messageText.trim() || sending) return

    setSending(true)

    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: messageText }])

    try {
      const res = await fetch(`${API_BASE}/api/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          conversation_id: null, // New conversation for Match Intelligence
          context: context, // Event context for the AI
        }),
      })

      const data = await res.json()

      if (res.ok) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          model: data.model,
          source: data.response_source,
        }])
        setConversationId(data.conversation_id)
      } else {
        setMessages(prev => [...prev, {
          role: 'error',
          content: data.error || 'AI service unavailable. Please check API key.',
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'error',
        content: 'Failed to connect to AI service. Please try again.',
      }])
    } finally {
      setSending(false)
    }
  }

  // Send message
  const sendMessage = async () => {
    if (!input.trim() || sending) return

    const userMessage = input.trim()
    setInput('')
    setSending(true)

    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      const res = await fetch(`${API_BASE}/api/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: conversationId,
        }),
      })

      const data = await res.json()

      if (res.ok) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          model: data.model,
          source: data.response_source,
        }])
        setConversationId(data.conversation_id)
      } else {
        // API error - NO FALLBACK, show error
        setMessages(prev => [...prev, {
          role: 'error',
          content: data.error || 'AI service unavailable. Please check API key.',
        }])
      }
    } catch (err) {
      // Network error - NO FALLBACK, show error
      setMessages(prev => [...prev, {
        role: 'error',
        content: 'Failed to connect to AI service. Please try again.',
      }])
    } finally {
      setSending(false)
    }
  }

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-96 bg-gray-800 shadow-xl z-50
                   chat-panel ${isOpen ? 'chat-panel-open' : 'chat-panel-closed pointer-events-none'}`}
      >
        {/* Header */}
        <div className="bg-ai-accent px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-white">AI Assistant</h2>
            {status.loading ? (
              <p className="text-sm text-white/70">Checking connection...</p>
            ) : status.connected ? (
              <p className="text-sm text-white/70">
                Connected to {status.model}
              </p>
            ) : (
              <p className="text-sm text-error">
                AI Unavailable
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Status Banner */}
        {!status.loading && !status.connected && (
          <div className="bg-error/20 border-l-4 border-error px-4 py-3">
            <p className="text-error text-sm font-medium">AI Service Unavailable</p>
            <p className="text-error/70 text-xs mt-1">
              {status.error || 'Please set ANTHROPIC_API_KEY'}
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 h-[calc(100%-180px)]">
          {messages.length === 0 && !sending ? (
            <div className="text-center text-gray-400 py-8">
              <div className="text-4xl mb-4">🤖</div>
              <p className="font-medium">Hello! I'm BetAI</p>
              <p className="text-sm mt-2">
                Ask me about betting odds, strategies, or any questions about sports betting.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`${
                    msg.role === 'user'
                      ? 'ml-8'
                      : msg.role === 'error'
                        ? 'mr-8'
                        : 'mr-8'
                  }`}
                >
                  <div
                    className={`rounded-lg p-3 ${
                      msg.role === 'user'
                        ? 'bg-ai-accent text-white'
                        : msg.role === 'error'
                          ? 'bg-error/20 text-error'
                          : 'bg-gray-700 text-white'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mt-2 prose-headings:mb-1 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded prose-pre:bg-gray-900 prose-pre:p-2">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                    {msg.model && (
                      <p className="text-xs text-gray-400 mt-2">
                        via {msg.model}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              {/* Searching indicator while AI is working */}
              {sending && (
                <div className="mr-8">
                  <div className="rounded-lg p-3 bg-gray-700 text-white">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin text-ai-accent" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <span className="text-gray-300">Searching and analyzing...</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      Querying database, researching teams, calculating odds...
                    </p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gray-800 border-t border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={status.connected ? "Ask me anything..." : "AI unavailable"}
              disabled={!status.connected || sending}
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2
                       text-white placeholder-gray-400 focus:outline-none focus:border-ai-accent
                       disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={!status.connected || sending || !input.trim()}
              className="px-4 py-2 bg-ai-accent text-white rounded-lg
                       hover:bg-ai-accent/80 transition-colors disabled:opacity-50"
            >
              {sending ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
