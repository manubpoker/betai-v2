import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { API_BASE } from '../config'

// Store chat state outside component to persist across open/close
let persistedMessages = []
let persistedConversationId = null

export default function AIChatPanel({ isOpen, onClose, initialMessage = null, eventContext = null }) {
  const [messages, setMessages] = useState(persistedMessages)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [status, setStatus] = useState({ loading: true, connected: false, model: null })
  const [conversationId, setConversationId] = useState(persistedConversationId)
  const [processedInitialMessage, setProcessedInitialMessage] = useState(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const messagesEndRef = useRef(null)

  // Persist messages to module-level state when they change
  useEffect(() => {
    persistedMessages = messages
  }, [messages])

  // Persist conversation ID
  useEffect(() => {
    persistedConversationId = conversationId
  }, [conversationId])

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
        className={`fixed top-0 right-0 h-full bg-white shadow-xl z-50 transition-all duration-300
                   chat-panel ${isOpen ? 'chat-panel-open' : 'chat-panel-closed pointer-events-none'}
                   ${isFullscreen ? 'w-full' : 'w-[600px]'}`}
      >
        {/* Header */}
        <div className="bg-ai-accent px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-white">AI Assistant</h2>
            {status.loading ? (
              <p className="text-sm text-white/70">Checking connection...</p>
            ) : status.connected ? (
              <p className="text-sm text-white/70">
                {status.model}
              </p>
            ) : (
              <p className="text-sm text-red-200">
                Unavailable
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Fullscreen toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="text-white/70 hover:text-white p-1"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                </svg>
              )}
            </button>
            {/* Close button */}
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

        {/* Status Banner */}
        {!status.loading && !status.connected && (
          <div className="bg-red-100 border-l-4 border-red-500 px-4 py-3">
            <p className="text-red-700 text-sm font-medium">AI Service Unavailable</p>
            <p className="text-red-600 text-xs mt-1">
              {status.error || 'Please set ANTHROPIC_API_KEY'}
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 h-[calc(100%-180px)] bg-gray-50">
          <div className={`mx-auto ${isFullscreen ? 'max-w-4xl' : ''}`}>
            {messages.length === 0 && !sending ? (
              <div className="text-center text-betfair-gray py-8">
                <div className="w-12 h-12 mx-auto mb-4 bg-ai-accent/10 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-ai-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <p className="font-medium text-betfair-black">BetAI Assistant</p>
                <p className="text-sm mt-2">
                  Ask about betting odds, strategies, or match analysis.
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
                          ? 'bg-red-100 text-red-700 border border-red-200'
                          : 'bg-white text-betfair-black border border-gray-200 shadow-sm'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mt-2 prose-headings:mb-1 prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-pre:bg-gray-100 prose-pre:p-2">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                    )}
                    {msg.model && (
                      <p className="text-xs text-betfair-gray mt-2 pt-2 border-t border-gray-100">
                        via {msg.model}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              {/* Searching indicator while AI is working */}
              {sending && (
                <div className="mr-8">
                  <div className="rounded-lg p-3 bg-white text-betfair-black border border-gray-200 shadow-sm">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin text-ai-accent" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <span className="text-betfair-gray text-sm">Analyzing...</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      Searching data and generating insights...
                    </p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
          </div>
        </div>

        {/* Input */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-white border-t border-gray-200">
          <div className={`flex gap-2 mx-auto ${isFullscreen ? 'max-w-4xl' : ''}`}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={status.connected ? "Ask anything..." : "AI unavailable"}
              disabled={!status.connected || sending}
              className="flex-1 bf-input disabled:opacity-50 disabled:bg-gray-100"
            />
            <button
              onClick={sendMessage}
              disabled={!status.connected || sending || !input.trim()}
              className="px-4 py-2 bg-ai-accent text-white rounded
                       hover:bg-ai-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
