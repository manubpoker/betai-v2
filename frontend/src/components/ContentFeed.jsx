import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../config'

// Content type icons and styling
const contentTypes = {
  article: {
    icon: '📰',
    label: 'Articles',
    bg: 'bg-gradient-to-r from-blue-600 to-blue-700'
  },
  social: {
    icon: '💬',
    label: 'Social',
    bg: 'bg-gradient-to-r from-orange-500 to-red-600'
  }
}

// Source icons
const sourceIcons = {
  'BBC Sport': '🔵',
  'Sky Sports': '🔴',
  'ESPN FC': '🟢',
  'The Guardian': '🟡',
  'Reddit r/soccer': '🔶',
  'Reddit r/SoccerBetting': '💰'
}

export default function ContentFeed({ isOpen, onClose }) {
  const [content, setContent] = useState([])
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [filter, setFilter] = useState('all')
  const [lastUpdated, setLastUpdated] = useState(null)

  // Fetch content from API
  const fetchContent = useCallback(async () => {
    setLoading(true)
    try {
      const typeParam = filter !== 'all' ? `&type=${filter}` : ''
      const res = await fetch(`${API_BASE}/api/content?limit=50${typeParam}`)
      const data = await res.json()
      setContent(data.content || [])
      if (data.content?.length > 0) {
        setLastUpdated(data.content[0].scraped_at)
      }
    } catch (err) {
      console.error('Error fetching content:', err)
    } finally {
      setLoading(false)
    }
  }, [filter])

  // Trigger content scrape
  const triggerScrape = async () => {
    setScraping(true)
    try {
      const res = await fetch(`${API_BASE}/api/content/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workers: 3 })
      })
      const data = await res.json()
      if (data.success) {
        // Refresh content after scrape
        await fetchContent()
      }
    } catch (err) {
      console.error('Error triggering scrape:', err)
    } finally {
      setScraping(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchContent()
    }
  }, [isOpen, fetchContent])

  // Format relative time
  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    const diff = Date.now() - new Date(timestamp).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  // Format numbers
  const formatNumber = (num) => {
    if (!num) return '0'
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  // Parse related teams
  const parseTeams = (teamsJson) => {
    try {
      return JSON.parse(teamsJson || '[]')
    } catch {
      return []
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-4 md:inset-8 bg-[#0a0a0a] rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-[#111] px-6 py-4 flex items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">📡</span>
              </div>
              <span className="text-white font-bold text-xl">Content Feed</span>
            </div>
            {lastUpdated && (
              <span className="text-white/40 text-sm hidden md:block">
                Updated {formatTime(lastUpdated)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={triggerScrape}
              disabled={scraping}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                scraping
                  ? 'bg-white/10 text-white/50 cursor-not-allowed'
                  : 'bg-gradient-to-r from-orange-500 to-red-600 text-white hover:opacity-90'
              }`}
            >
              {scraping ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Scraping...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Fetch Latest
                </>
              )}
            </button>
            <button
              onClick={fetchContent}
              disabled={loading}
              className="text-white/60 hover:text-white p-2 transition-colors"
              title="Refresh feed"
            >
              <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button onClick={onClose} className="text-white/60 hover:text-white p-2 transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="bg-[#111] px-6 py-3 border-b border-white/5 overflow-x-auto">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                filter === 'all'
                  ? 'bg-white text-black'
                  : 'bg-white/10 text-white/70 hover:bg-white/20'
              }`}
            >
              🔥 All
            </button>
            {Object.entries(contentTypes).map(([key, value]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  filter === key
                    ? 'bg-white text-black'
                    : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}
              >
                {value.icon} {value.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content Feed */}
        <div className="flex-1 overflow-y-auto">
          {loading && content.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="flex items-center gap-3 text-white/60">
                <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Loading content...</span>
              </div>
            </div>
          ) : content.length === 0 ? (
            <div className="text-center text-white/40 py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-white/5 rounded-full flex items-center justify-center">
                <span className="text-3xl">📡</span>
              </div>
              <p className="text-lg font-medium text-white/60">No content yet</p>
              <p className="text-sm mt-2">Click "Fetch Latest" to scrape fresh football content</p>
              <button
                onClick={triggerScrape}
                disabled={scraping}
                className="mt-4 px-6 py-3 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                {scraping ? 'Scraping...' : 'Fetch Content Now'}
              </button>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto py-4 px-4 space-y-4">
              {content.map((item) => (
                <ContentCard
                  key={item.id}
                  item={item}
                  formatTime={formatTime}
                  formatNumber={formatNumber}
                  parseTeams={parseTeams}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-[#111] px-6 py-3 border-t border-white/10">
          <div className="flex items-center justify-between text-xs text-white/40">
            <span>Sources: BBC Sport, Sky Sports, ESPN FC, The Guardian, Reddit</span>
            <span>{content.length} items</span>
          </div>
        </div>
      </div>
    </>
  )
}

// Content Card Component
function ContentCard({ item, formatTime, formatNumber, parseTeams }) {
  const typeConfig = contentTypes[item.content_type] || contentTypes.article
  const sourceIcon = sourceIcons[item.source] || '📰'
  const teams = parseTeams(item.related_teams)

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-[#161616] rounded-xl border border-white/5 overflow-hidden hover:border-white/20 transition-all hover:bg-[#1a1a1a]"
    >
      {/* Card Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className="text-lg">{sourceIcon}</span>
          <span className="text-white/80 text-sm font-medium">{item.source}</span>
          {item.content_type === 'social' && (
            <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full">
              Social
            </span>
          )}
        </div>
        <span className="text-white/40 text-xs">{formatTime(item.scraped_at)}</span>
      </div>

      {/* Card Content */}
      <div className="p-4">
        <h3 className="text-white font-medium leading-tight mb-2">{item.title}</h3>

        {item.summary && (
          <p className="text-white/50 text-sm line-clamp-2 mb-3">{item.summary}</p>
        )}

        {/* Engagement stats for social */}
        {item.content_type === 'social' && (item.engagement_score > 0 || item.comments_count > 0) && (
          <div className="flex items-center gap-4 text-xs text-white/50 mb-3">
            {item.engagement_score > 0 && (
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z"/>
                </svg>
                {formatNumber(item.engagement_score)}
              </span>
            )}
            {item.comments_count > 0 && (
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                {formatNumber(item.comments_count)}
              </span>
            )}
          </div>
        )}

        {/* Related teams/competition */}
        {(teams.length > 0 || item.related_competition) && (
          <div className="flex flex-wrap items-center gap-2">
            {item.related_competition && (
              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                {item.related_competition}
              </span>
            )}
            {teams.slice(0, 3).map((team, i) => (
              <span key={i} className="px-2 py-1 bg-white/10 text-white/60 text-xs rounded">
                {team}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Read more indicator */}
      <div className="px-4 py-2 bg-white/5 flex items-center justify-between">
        <span className="text-white/40 text-xs">
          {item.content_type === 'article' ? 'Read article' : 'View post'} →
        </span>
        <svg className="w-4 h-4 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </div>
    </a>
  )
}
