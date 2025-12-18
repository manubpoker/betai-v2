import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../config'

// Content type icons and styling
const contentTypes = {
  tweet: {
    icon: '𝕏',
    label: 'X/Twitter',
    bg: 'bg-black',
    accent: 'text-white'
  },
  article: {
    icon: '📰',
    label: 'Article',
    bg: 'bg-gradient-to-r from-blue-600 to-blue-700',
    accent: 'text-blue-400'
  },
  video: {
    icon: '▶️',
    label: 'Video',
    bg: 'bg-gradient-to-r from-red-600 to-red-700',
    accent: 'text-red-400'
  },
  meme: {
    icon: '😂',
    label: 'Meme',
    bg: 'bg-gradient-to-r from-purple-600 to-pink-600',
    accent: 'text-purple-400'
  },
  stats: {
    icon: '📊',
    label: 'Stats',
    bg: 'bg-gradient-to-r from-green-600 to-emerald-600',
    accent: 'text-green-400'
  },
  news: {
    icon: '⚡',
    label: 'Breaking',
    bg: 'bg-gradient-to-r from-amber-500 to-orange-600',
    accent: 'text-amber-400'
  }
}

// Sample content generators based on match data
const generateTweet = (match, teams) => {
  const tweets = [
    { author: 'FabrizioRomano', handle: '@FabrizioRomano', verified: true, content: `🚨 BREAKING: ${teams[0]} vs ${teams[1]} - Big match coming up! Here we go! 🔴⚪ #${teams[0].replace(/\s/g, '')}`, likes: Math.floor(Math.random() * 50000) + 10000, retweets: Math.floor(Math.random() * 10000) + 2000 },
    { author: 'ESPN FC', handle: '@ESPNFC', verified: true, content: `${teams[0]} are unbeaten in their last 5 home games against ${teams[1]}. Will that streak continue? 🤔⚽`, likes: Math.floor(Math.random() * 20000) + 5000, retweets: Math.floor(Math.random() * 5000) + 1000 },
    { author: 'Football Daily', handle: '@footballdaily', verified: true, content: `The atmosphere at ${teams[0]}'s stadium is going to be ELECTRIC tonight 🔥🏟️ #${match.competition?.replace(/\s/g, '')}`, likes: Math.floor(Math.random() * 15000) + 3000, retweets: Math.floor(Math.random() * 3000) + 500 },
    { author: 'Squawka', handle: '@Squawka', verified: true, content: `📈 ${teams[0]} have scored in 90% of their home matches this season.\n\n${teams[1]} have kept just 2 clean sheets away from home.\n\nGoals incoming? 👀`, likes: Math.floor(Math.random() * 8000) + 2000, retweets: Math.floor(Math.random() * 2000) + 400 },
    { author: 'The Athletic UK', handle: '@TheAthleticUK', verified: true, content: `🗣️ "${teams[1]} are a top side but we're ready for them" - ${teams[0]} manager speaks ahead of tonight's clash`, likes: Math.floor(Math.random() * 12000) + 4000, retweets: Math.floor(Math.random() * 3000) + 800 },
  ]
  return tweets[Math.floor(Math.random() * tweets.length)]
}

const generateArticle = (match, teams) => {
  const articles = [
    { source: 'Sky Sports', title: `${teams[0]} vs ${teams[1]}: Match Preview, Team News & Predicted Lineups`, excerpt: `Everything you need to know ahead of today's ${match.competition} clash between ${teams[0]} and ${teams[1]}...`, readTime: '5 min read', image: 'preview' },
    { source: 'BBC Sport', title: `${match.competition}: ${teams[0]} looking to extend winning run against ${teams[1]}`, excerpt: `${teams[0]} will be looking to continue their impressive form when they host ${teams[1]} in what promises to be an exciting encounter...`, readTime: '4 min read', image: 'analysis' },
    { source: 'The Guardian', title: `Tactical Analysis: How ${teams[0]} can exploit ${teams[1]}'s defensive weakness`, excerpt: `Our tactical expert breaks down the key battles and strategies that could decide this crucial fixture...`, readTime: '7 min read', image: 'tactics' },
    { source: 'Goal.com', title: `Betting Tips: ${teams[0]} vs ${teams[1]} - Best odds and predictions`, excerpt: `Our experts analyze the markets and provide their top picks for this weekend's fixture...`, readTime: '3 min read', image: 'odds' },
  ]
  return articles[Math.floor(Math.random() * articles.length)]
}

const generateVideo = (match, teams) => {
  const videos = [
    { channel: 'Sky Sports', title: `${teams[0]} vs ${teams[1]} | MATCH PREVIEW`, duration: '4:32', views: Math.floor(Math.random() * 500000) + 100000, thumbnail: 'preview' },
    { channel: 'GOAL', title: `Top 10 Goals: ${teams[0]} vs ${teams[1]} | Classic Moments`, duration: '8:15', views: Math.floor(Math.random() * 2000000) + 500000, thumbnail: 'goals' },
    { channel: 'ESPN FC', title: `${teams[0]} PRESS CONFERENCE | Manager speaks ahead of ${teams[1]} clash`, duration: '12:45', views: Math.floor(Math.random() * 300000) + 50000, thumbnail: 'presser' },
    { channel: 'Football Daily', title: `Why ${teams[0]} WILL BEAT ${teams[1]} | Tactical Breakdown`, duration: '6:28', views: Math.floor(Math.random() * 400000) + 80000, thumbnail: 'tactics' },
  ]
  return videos[Math.floor(Math.random() * videos.length)]
}

const generateMeme = (match, teams) => {
  const memes = [
    { caption: `${teams[0]} fans watching ${teams[1]} struggle this season:`, template: 'laughing', source: 'r/soccer', upvotes: Math.floor(Math.random() * 5000) + 1000 },
    { caption: `POV: You bet on ${teams[1]} to win away from home`, template: 'sad', source: 'Football Twitter', upvotes: Math.floor(Math.random() * 8000) + 2000 },
    { caption: `${teams[0]} after going 1-0 up in the first minute:`, template: 'celebration', source: '@FootballMemes', upvotes: Math.floor(Math.random() * 10000) + 3000 },
    { caption: `Me checking my bet slip after ${teams[0]} concede in the 90th minute:`, template: 'shock', source: 'r/soccerbetting', upvotes: Math.floor(Math.random() * 6000) + 1500 },
  ]
  return memes[Math.floor(Math.random() * memes.length)]
}

const generateStats = (match, teams) => {
  const stats = [
    { title: 'Head to Head', stats: [{ label: `${teams[0]} wins`, value: Math.floor(Math.random() * 15) + 5 }, { label: 'Draws', value: Math.floor(Math.random() * 10) + 2 }, { label: `${teams[1]} wins`, value: Math.floor(Math.random() * 12) + 3 }] },
    { title: 'Recent Form', stats: [{ label: `${teams[0]}`, value: 'W-W-D-W-L' }, { label: `${teams[1]}`, value: 'L-W-W-D-W' }] },
    { title: 'Goals Scored (Season)', stats: [{ label: teams[0], value: Math.floor(Math.random() * 30) + 20 }, { label: teams[1], value: Math.floor(Math.random() * 30) + 15 }] },
  ]
  return stats[Math.floor(Math.random() * stats.length)]
}

const generateNews = (match, teams) => {
  const news = [
    { headline: `🚨 TEAM NEWS: ${teams[0]} star returns from injury ahead of ${teams[1]} clash`, time: '2 hours ago', source: 'Sky Sports' },
    { headline: `⚡ BREAKING: ${teams[1]} midfielder ruled out of ${teams[0]} game`, time: '45 mins ago', source: 'BBC Sport' },
    { headline: `📋 CONFIRMED: ${teams[0]} lineup announced - Key changes made`, time: '1 hour ago', source: 'Official' },
    { headline: `🎯 ${teams[0]} targeting club record against ${teams[1]} today`, time: '3 hours ago', source: 'The Athletic' },
  ]
  return news[Math.floor(Math.random() * news.length)]
}

export default function ContentFeed({ isOpen, onClose }) {
  const [content, setContent] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Parse event name to extract match name
  const parseEventName = (rawName) => {
    if (!rawName) return rawName
    const patterns = [
      /^(Starting\s+In\s+[\d']+mi?)\s*(.+)$/i,
      /^(In-Play)\s*(.+)$/i,
      /^(Today|Tomorrow)\s+(\d{1,2}:\d{2})\s*(.+)$/,
      /^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{1,2}:\d{2})\s*(.+)$/,
      /^(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{1,2}:\d{2})\s*(.+)$/,
      /^(\d{1,2}:\d{2})\s*(.+)$/,
    ]
    for (const pattern of patterns) {
      const match = rawName.match(pattern)
      if (match) {
        return match.length === 4 ? match[3].trim() : match[2].trim()
      }
    }
    return rawName
  }

  // Generate content from matches
  const generateContent = useCallback((events) => {
    const allContent = []
    const types = ['tweet', 'article', 'video', 'meme', 'stats', 'news']

    events.forEach((event) => {
      const matchName = parseEventName(event.event_name)
      const teams = matchName.split(/ v | vs /i).map(t => t.trim())
      if (teams.length < 2) return

      // Generate 2-4 pieces of content per match
      const numContent = Math.floor(Math.random() * 3) + 2
      const usedTypes = new Set()

      for (let i = 0; i < numContent; i++) {
        let type
        do {
          type = types[Math.floor(Math.random() * types.length)]
        } while (usedTypes.has(type) && usedTypes.size < types.length)
        usedTypes.add(type)

        let data
        switch (type) {
          case 'tweet': data = generateTweet(event, teams); break
          case 'article': data = generateArticle(event, teams); break
          case 'video': data = generateVideo(event, teams); break
          case 'meme': data = generateMeme(event, teams); break
          case 'stats': data = generateStats(event, teams); break
          case 'news': data = generateNews(event, teams); break
        }

        allContent.push({
          id: `${event.id}-${type}-${i}-${Date.now()}`,
          type,
          matchName,
          teams,
          competition: event.competition,
          data,
          timestamp: new Date(Date.now() - Math.random() * 7200000).toISOString() // Random time in last 2 hours
        })
      }
    })

    // Shuffle and sort by timestamp
    return allContent
      .sort(() => Math.random() - 0.5)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
  }, [])

  // Fetch and generate content
  const fetchContent = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/events?sport=football&data_type=exchange`)
      const events = await res.json()
      const generated = generateContent(events.slice(0, 10)) // Limit to 10 matches
      setContent(generated)
    } catch (err) {
      console.error('Error fetching content:', err)
    } finally {
      setLoading(false)
    }
  }, [generateContent])

  useEffect(() => {
    if (isOpen) {
      fetchContent()
    }
  }, [isOpen, fetchContent])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!isOpen || !autoRefresh) return
    const interval = setInterval(fetchContent, 30000)
    return () => clearInterval(interval)
  }, [isOpen, autoRefresh, fetchContent])

  // Format relative time
  const formatTime = (timestamp) => {
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
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  // Filter content
  const filteredContent = filter === 'all'
    ? content
    : content.filter(c => c.type === filter)

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
            <span className="text-white/40 text-sm hidden md:block">Live football content from around the web</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                autoRefresh
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-white/10 text-white/50'
              }`}
            >
              {autoRefresh ? '● Live' : '○ Paused'}
            </button>
            <button
              onClick={fetchContent}
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
          ) : filteredContent.length === 0 ? (
            <div className="text-center text-white/40 py-16">
              <p className="text-lg">No content available</p>
              <p className="text-sm mt-1">Check back later for updates</p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto py-4 px-4 space-y-4">
              {filteredContent.map((item) => (
                <ContentCard key={item.id} item={item} formatTime={formatTime} formatNumber={formatNumber} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// Content Card Component
function ContentCard({ item, formatTime, formatNumber }) {
  const typeConfig = contentTypes[item.type]

  return (
    <div className="bg-[#161616] rounded-xl border border-white/5 overflow-hidden hover:border-white/10 transition-all">
      {/* Card Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded flex items-center justify-center text-xs ${typeConfig.bg}`}>
            {typeConfig.icon}
          </span>
          <span className="text-white/60 text-sm">{item.competition}</span>
        </div>
        <span className="text-white/40 text-xs">{formatTime(item.timestamp)}</span>
      </div>

      {/* Card Content */}
      <div className="p-4">
        {item.type === 'tweet' && (
          <TweetContent data={item.data} formatNumber={formatNumber} />
        )}
        {item.type === 'article' && (
          <ArticleContent data={item.data} />
        )}
        {item.type === 'video' && (
          <VideoContent data={item.data} formatNumber={formatNumber} />
        )}
        {item.type === 'meme' && (
          <MemeContent data={item.data} formatNumber={formatNumber} />
        )}
        {item.type === 'stats' && (
          <StatsContent data={item.data} />
        )}
        {item.type === 'news' && (
          <NewsContent data={item.data} />
        )}
      </div>

      {/* Card Footer - Match Context */}
      <div className="px-4 py-2 bg-white/5 flex items-center gap-2">
        <span className="text-white/40 text-xs">Related to:</span>
        <span className="text-white/70 text-xs font-medium">{item.matchName}</span>
      </div>
    </div>
  )
}

// Tweet Content
function TweetContent({ data, formatNumber }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-10 h-10 bg-gradient-to-br from-gray-600 to-gray-800 rounded-full flex items-center justify-center text-white font-bold">
          {data.author[0]}
        </div>
        <div>
          <div className="flex items-center gap-1">
            <span className="text-white font-semibold text-sm">{data.author}</span>
            {data.verified && (
              <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.818-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.51 1.5 12 1.5s-2.816.917-3.437 2.25c-.415-.165-.866-.25-1.336-.25-2.11 0-3.818 1.79-3.818 4 0 .494.083.964.237 1.4-1.272.65-2.147 2.018-2.147 3.6 0 1.495.782 2.798 1.942 3.486-.02.17-.032.34-.032.514 0 2.21 1.708 4 3.818 4 .47 0 .92-.086 1.335-.25.62 1.334 1.926 2.25 3.437 2.25 1.512 0 2.818-.916 3.437-2.25.415.163.865.248 1.336.248 2.11 0 3.818-1.79 3.818-4 0-.174-.012-.344-.033-.513 1.158-.687 1.943-1.99 1.943-3.484zm-6.616-3.334l-4.334 6.5c-.145.217-.382.334-.625.334-.143 0-.288-.04-.416-.126l-.115-.094-2.415-2.415c-.293-.293-.293-.768 0-1.06s.768-.294 1.06 0l1.77 1.767 3.825-5.74c.23-.345.696-.436 1.04-.207.346.23.44.696.21 1.04z"/>
              </svg>
            )}
          </div>
          <span className="text-white/50 text-xs">{data.handle}</span>
        </div>
      </div>
      <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">{data.content}</p>
      <div className="flex items-center gap-6 mt-3 text-white/50 text-xs">
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          {formatNumber(data.likes)}
        </span>
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          {formatNumber(data.retweets)}
        </span>
      </div>
    </div>
  )
}

// Article Content
function ArticleContent({ data }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-blue-400 text-xs font-medium">{data.source}</span>
        <span className="text-white/30">•</span>
        <span className="text-white/40 text-xs">{data.readTime}</span>
      </div>
      <h3 className="text-white font-semibold mb-2">{data.title}</h3>
      <p className="text-white/60 text-sm line-clamp-2">{data.excerpt}</p>
      <button className="mt-3 text-blue-400 text-sm font-medium hover:underline">
        Read full article →
      </button>
    </div>
  )
}

// Video Content
function VideoContent({ data, formatNumber }) {
  return (
    <div>
      {/* Video Thumbnail Placeholder */}
      <div className="relative bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg aspect-video mb-3 flex items-center justify-center group cursor-pointer overflow-hidden">
        <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors" />
        <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center z-10 group-hover:scale-110 transition-transform">
          <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
        <span className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">
          {data.duration}
        </span>
      </div>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-red-400 text-xs font-medium">{data.channel}</span>
      </div>
      <h3 className="text-white font-medium text-sm">{data.title}</h3>
      <span className="text-white/40 text-xs">{formatNumber(data.views)} views</span>
    </div>
  )
}

// Meme Content
function MemeContent({ data, formatNumber }) {
  const memeImages = {
    laughing: '😂🤣',
    sad: '😭💀',
    celebration: '🎉🥳',
    shock: '😱😳'
  }

  return (
    <div>
      <p className="text-white font-medium mb-3">{data.caption}</p>
      {/* Meme Image Placeholder */}
      <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-lg aspect-square max-w-xs flex items-center justify-center text-6xl">
        {memeImages[data.template] || '😂'}
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-white/40 text-xs">{data.source}</span>
        <span className="text-white/50 text-xs flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z"/>
          </svg>
          {formatNumber(data.upvotes)}
        </span>
      </div>
    </div>
  )
}

// Stats Content
function StatsContent({ data }) {
  return (
    <div>
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
        <span className="text-green-400">📊</span> {data.title}
      </h3>
      <div className="space-y-2">
        {data.stats.map((stat, i) => (
          <div key={i} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
            <span className="text-white/70 text-sm">{stat.label}</span>
            <span className="text-white font-bold">{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// News Content
function NewsContent({ data }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs font-bold rounded">BREAKING</span>
        <span className="text-white/40 text-xs">{data.time}</span>
      </div>
      <h3 className="text-white font-semibold text-lg leading-tight">{data.headline}</h3>
      <span className="text-white/50 text-xs mt-2 block">{data.source}</span>
    </div>
  )
}
