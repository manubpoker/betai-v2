import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../config'

// Simulated users/punters for the social feed
const PUNTERS = [
  { id: 1, name: 'SharpShooter99', avatar: '🎯', verified: true, winRate: 67, followers: 12400, streak: 5 },
  { id: 2, name: 'FootyExpert', avatar: '⚽', verified: true, winRate: 62, followers: 8900, streak: 3 },
  { id: 3, name: 'ValueHunter', avatar: '💎', verified: false, winRate: 58, followers: 3200, streak: 2 },
  { id: 4, name: 'AccaKing', avatar: '👑', verified: true, winRate: 54, followers: 15600, streak: 0 },
  { id: 5, name: 'StatsMaster', avatar: '📊', verified: false, winRate: 61, followers: 5400, streak: 4 },
  { id: 6, name: 'PremierPunter', avatar: '🏆', verified: true, winRate: 59, followers: 9100, streak: 1 },
  { id: 7, name: 'OddsAnalyst', avatar: '🔢', verified: false, winRate: 56, followers: 2800, streak: 2 },
  { id: 8, name: 'BetWiseGuru', avatar: '🧠', verified: true, winRate: 64, followers: 11200, streak: 6 },
]

// Generate hot takes based on events
const generateTakes = (events) => {
  const takeTemplates = [
    { template: (team) => `${team} are going to smash it today 🔥`, sentiment: 'bullish' },
    { template: (team) => `Everyone sleeping on ${team}... easy money 💰`, sentiment: 'bullish' },
    { template: (team) => `${team} look shaky lately, fading them hard`, sentiment: 'bearish' },
    { template: (team) => `Over 2.5 goals is basically free money here`, sentiment: 'bullish' },
    { template: (team) => `${team} haven't kept a clean sheet in 5 games... BTTS ✅`, sentiment: 'bullish' },
    { template: (team) => `Trap line. ${team} are value but won't win`, sentiment: 'bearish' },
    { template: (team) => `${team} at these odds? Lock it in 🔒`, sentiment: 'bullish' },
    { template: (team) => `This game has 0-0 written all over it`, sentiment: 'bearish' },
    { template: (team) => `${team} manager masterclass incoming`, sentiment: 'bullish' },
    { template: (team) => `Don't overthink it. ${team} win.`, sentiment: 'bullish' },
  ]

  const takes = []

  events.slice(0, 8).forEach((event, idx) => {
    const odds = event.odds || []
    if (odds.length === 0) return

    const teams = odds.map(o => o.selection_name).filter(n => n !== 'The Draw')
    if (teams.length === 0) return

    const randomTeam = teams[Math.floor(Math.random() * teams.length)]
    const template = takeTemplates[Math.floor(Math.random() * takeTemplates.length)]
    const punter = PUNTERS[Math.floor(Math.random() * PUNTERS.length)]

    takes.push({
      id: `take-${event.id}-${idx}`,
      type: 'take',
      punter,
      content: template.template(randomTeam),
      sentiment: template.sentiment,
      event: {
        id: event.id,
        name: parseEventName(event.event_name),
        competition: event.competition,
        time: event.start_time
      },
      likes: Math.floor(Math.random() * 500) + 50,
      comments: Math.floor(Math.random() * 80) + 5,
      reposts: Math.floor(Math.random() * 100) + 10,
      timestamp: new Date(Date.now() - Math.random() * 3600000 * 4).toISOString()
    })
  })

  return takes
}

// Generate shared bets based on events
const generateSharedBets = (events) => {
  const bets = []
  const betTypes = ['single', 'double', 'acca']

  events.slice(0, 10).forEach((event, idx) => {
    const odds = event.odds || []
    if (odds.length === 0) return

    const punter = PUNTERS[Math.floor(Math.random() * PUNTERS.length)]
    const selection = odds[Math.floor(Math.random() * odds.length)]
    if (!selection || !selection.back_odds) return

    const stake = [10, 20, 25, 50, 100][Math.floor(Math.random() * 5)]
    const betType = betTypes[Math.floor(Math.random() * betTypes.length)]
    const won = Math.random() > 0.45

    bets.push({
      id: `bet-${event.id}-${idx}`,
      type: 'bet',
      punter,
      betType,
      stake,
      totalOdds: selection.back_odds,
      potentialReturn: (stake * selection.back_odds).toFixed(2),
      status: Math.random() > 0.3 ? 'pending' : (won ? 'won' : 'lost'),
      selections: [{
        event: parseEventName(event.event_name),
        competition: event.competition,
        selection: selection.selection_name,
        odds: selection.back_odds
      }],
      likes: Math.floor(Math.random() * 300) + 20,
      copies: Math.floor(Math.random() * 50) + 5,
      timestamp: new Date(Date.now() - Math.random() * 3600000 * 6).toISOString()
    })
  })

  return bets
}

// Parse event name
const parseEventName = (rawName) => {
  if (!rawName) return rawName
  const patterns = [
    /^(Starting\s+In\s+[\d']+mi?)\s*(.+)$/i,
    /^(In-Play)\s*(.+)$/i,
    /^(Today|Tomorrow)\s+(\d{1,2}:\d{2})\s*(.+)$/,
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

export default function SocialBetFeed({ isOpen, onClose, balance, onBalanceChange }) {
  const [feedItems, setFeedItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, takes, bets, trending
  const [following, setFollowing] = useState(new Set([1, 2, 4])) // Initially following some punters
  const [likedItems, setLikedItems] = useState(new Set())
  const [showCompose, setShowCompose] = useState(false)
  const [newTake, setNewTake] = useState('')

  // Fetch events and generate feed
  const fetchFeed = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/events?sport=football&data_type=exchange`)
      const events = await res.json()

      const takes = generateTakes(events)
      const bets = generateSharedBets(events)

      // Combine and sort by timestamp
      const combined = [...takes, ...bets].sort(
        (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
      )

      setFeedItems(combined)
    } catch (err) {
      console.error('Error fetching feed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchFeed()
    }
  }, [isOpen, fetchFeed])

  // Format relative time
  const formatTime = (timestamp) => {
    const diff = Date.now() - new Date(timestamp).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'now'
    if (mins < 60) return `${mins}m`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h`
    return `${Math.floor(hours / 24)}d`
  }

  // Toggle follow
  const toggleFollow = (punterId) => {
    setFollowing(prev => {
      const newSet = new Set(prev)
      if (newSet.has(punterId)) {
        newSet.delete(punterId)
      } else {
        newSet.add(punterId)
      }
      return newSet
    })
  }

  // Toggle like
  const toggleLike = (itemId) => {
    setLikedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }

  // Filter items
  const filteredItems = feedItems.filter(item => {
    if (filter === 'all') return true
    if (filter === 'takes') return item.type === 'take'
    if (filter === 'bets') return item.type === 'bet'
    if (filter === 'following') return following.has(item.punter.id)
    if (filter === 'trending') return item.likes > 200
    return true
  })

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-4 md:inset-8 bg-[#000] rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <span className="text-2xl">🔥</span>
            </div>
            <div>
              <h2 className="text-white font-bold text-xl">The Feed</h2>
              <p className="text-white/70 text-sm">Hot takes & shared bets</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCompose(true)}
              className="px-4 py-2 bg-white text-purple-600 rounded-full font-bold text-sm hover:bg-white/90 transition-colors"
            >
              + Post Take
            </button>
            <button onClick={onClose} className="text-white/70 hover:text-white p-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="bg-[#111] px-6 py-3 border-b border-white/10 overflow-x-auto">
          <div className="flex items-center gap-2">
            {[
              { key: 'all', label: 'For You', icon: '✨' },
              { key: 'following', label: 'Following', icon: '👥' },
              { key: 'takes', label: 'Hot Takes', icon: '🔥' },
              { key: 'bets', label: 'Shared Bets', icon: '🎰' },
              { key: 'trending', label: 'Trending', icon: '📈' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
                  filter === tab.key
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
                    : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Feed */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="flex items-center gap-3 text-white/60">
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Loading feed...</span>
                </div>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="text-center text-white/40 py-16">
                <span className="text-4xl">🦗</span>
                <p className="mt-4">Nothing here yet</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {filteredItems.map(item => (
                  item.type === 'take' ? (
                    <TakeCard
                      key={item.id}
                      item={item}
                      formatTime={formatTime}
                      isFollowing={following.has(item.punter.id)}
                      isLiked={likedItems.has(item.id)}
                      onFollow={() => toggleFollow(item.punter.id)}
                      onLike={() => toggleLike(item.id)}
                    />
                  ) : (
                    <BetCard
                      key={item.id}
                      item={item}
                      formatTime={formatTime}
                      isFollowing={following.has(item.punter.id)}
                      isLiked={likedItems.has(item.id)}
                      onFollow={() => toggleFollow(item.punter.id)}
                      onLike={() => toggleLike(item.id)}
                      onCopy={() => {/* Copy bet logic */}}
                    />
                  )
                ))}
              </div>
            )}
          </div>

          {/* Sidebar - Top Punters */}
          <div className="hidden lg:block w-80 bg-[#0a0a0a] border-l border-white/10 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                <span>🏆</span> Top Punters
              </h3>
              <div className="space-y-3">
                {PUNTERS.sort((a, b) => b.winRate - a.winRate).slice(0, 6).map(punter => (
                  <div key={punter.id} className="bg-white/5 rounded-xl p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-xl">
                        {punter.avatar}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1">
                          <span className="text-white font-medium text-sm truncate">{punter.name}</span>
                          {punter.verified && (
                            <svg className="w-4 h-4 text-purple-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-white/50">
                          <span className="text-green-400">{punter.winRate}% win</span>
                          {punter.streak > 0 && (
                            <span className="text-orange-400">🔥{punter.streak}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => toggleFollow(punter.id)}
                        className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                          following.has(punter.id)
                            ? 'bg-white/10 text-white/70'
                            : 'bg-purple-500 text-white'
                        }`}
                      >
                        {following.has(punter.id) ? 'Following' : 'Follow'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Trending Markets */}
              <h3 className="text-white font-bold mt-6 mb-4 flex items-center gap-2">
                <span>📊</span> Hot Markets
              </h3>
              <div className="space-y-2">
                {['Liverpool to Win', 'Man City -1.5', 'BTTS Yes', 'Over 2.5 Goals', 'Arsenal Clean Sheet'].map((market, i) => (
                  <div key={i} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                    <span className="text-white/80 text-sm">{market}</span>
                    <span className="text-green-400 text-xs">{Math.floor(Math.random() * 500) + 100} bets</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Compose Take Modal */}
        {showCompose && (
          <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-10">
            <div className="bg-[#1a1a1a] rounded-2xl w-full max-w-lg mx-4 overflow-hidden">
              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <h3 className="text-white font-bold">Post Your Take</h3>
                <button onClick={() => setShowCompose(false)} className="text-white/50 hover:text-white">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-4">
                <textarea
                  value={newTake}
                  onChange={(e) => setNewTake(e.target.value)}
                  placeholder="What's your take? 🔥"
                  className="w-full h-32 bg-white/5 border border-white/10 rounded-xl p-4 text-white placeholder-white/30 resize-none focus:outline-none focus:border-purple-500"
                />
                <div className="flex items-center justify-between mt-4">
                  <span className="text-white/40 text-sm">{280 - newTake.length} characters left</span>
                  <button
                    disabled={!newTake.trim()}
                    className={`px-6 py-2 rounded-full font-bold transition-colors ${
                      newTake.trim()
                        ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
                        : 'bg-white/10 text-white/30 cursor-not-allowed'
                    }`}
                  >
                    Post Take
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

// Take Card Component
function TakeCard({ item, formatTime, isFollowing, isLiked, onFollow, onLike }) {
  return (
    <div className="p-4 hover:bg-white/5 transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-2xl flex-shrink-0">
          {item.punter.avatar}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-white font-bold">{item.punter.name}</span>
            {item.punter.verified && (
              <svg className="w-4 h-4 text-purple-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            )}
            <span className="text-white/40 text-sm">· {formatTime(item.timestamp)}</span>
            {!isFollowing && (
              <button
                onClick={onFollow}
                className="text-purple-400 text-sm font-medium hover:underline"
              >
                Follow
              </button>
            )}
          </div>
          <div className="text-green-400 text-xs">{item.punter.winRate}% win rate</div>
        </div>
      </div>

      {/* Content */}
      <div className="mt-3 ml-15">
        <p className="text-white text-lg">{item.content}</p>

        {/* Event Context */}
        <div className="mt-2 bg-white/5 rounded-lg px-3 py-2 inline-block">
          <span className="text-white/60 text-sm">{item.event.name}</span>
          <span className="text-white/40 text-xs ml-2">· {item.event.competition}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-4 ml-15 flex items-center gap-6">
        <button
          onClick={onLike}
          className={`flex items-center gap-2 transition-colors ${
            isLiked ? 'text-pink-500' : 'text-white/50 hover:text-pink-500'
          }`}
        >
          <svg className="w-5 h-5" fill={isLiked ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <span className="text-sm">{item.likes + (isLiked ? 1 : 0)}</span>
        </button>
        <button className="flex items-center gap-2 text-white/50 hover:text-blue-400 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-sm">{item.comments}</span>
        </button>
        <button className="flex items-center gap-2 text-white/50 hover:text-green-400 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          <span className="text-sm">{item.reposts}</span>
        </button>
        <button className="text-white/50 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// Bet Card Component
function BetCard({ item, formatTime, isFollowing, isLiked, onFollow, onLike, onCopy }) {
  const statusColors = {
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    won: 'bg-green-500/20 text-green-400 border-green-500/30',
    lost: 'bg-red-500/20 text-red-400 border-red-500/30'
  }

  return (
    <div className="p-4 hover:bg-white/5 transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center text-2xl flex-shrink-0">
          {item.punter.avatar}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-white font-bold">{item.punter.name}</span>
            {item.punter.verified && (
              <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            )}
            <span className="text-white/40 text-sm">shared a bet · {formatTime(item.timestamp)}</span>
          </div>
          <div className="text-blue-400 text-xs">{item.punter.winRate}% win rate · {item.punter.followers.toLocaleString()} followers</div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${statusColors[item.status]}`}>
          {item.status === 'pending' ? '⏳ Pending' : item.status === 'won' ? '✅ Won' : '❌ Lost'}
        </span>
      </div>

      {/* Bet Slip */}
      <div className="mt-3 ml-15 bg-gradient-to-br from-[#1a1a2e] to-[#16213e] rounded-xl overflow-hidden border border-white/10">
        <div className="p-4">
          {item.selections.map((sel, i) => (
            <div key={i} className="mb-2 last:mb-0">
              <div className="text-white font-medium">{sel.selection}</div>
              <div className="text-white/50 text-sm">{sel.event}</div>
              <div className="text-white/40 text-xs">{sel.competition}</div>
            </div>
          ))}
        </div>
        <div className="bg-white/5 px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-white/50 text-xs">Stake</div>
            <div className="text-white font-bold">£{item.stake}</div>
          </div>
          <div className="text-center">
            <div className="text-white/50 text-xs">Odds</div>
            <div className="text-yellow-400 font-bold">{item.totalOdds.toFixed(2)}</div>
          </div>
          <div className="text-right">
            <div className="text-white/50 text-xs">Returns</div>
            <div className="text-green-400 font-bold">£{item.potentialReturn}</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-4 ml-15 flex items-center gap-4">
        <button
          onClick={onLike}
          className={`flex items-center gap-2 transition-colors ${
            isLiked ? 'text-pink-500' : 'text-white/50 hover:text-pink-500'
          }`}
        >
          <svg className="w-5 h-5" fill={isLiked ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <span className="text-sm">{item.likes + (isLiked ? 1 : 0)}</span>
        </button>
        <button
          onClick={onCopy}
          className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-full text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Copy Bet ({item.copies})
        </button>
        <button className="text-white/50 hover:text-white transition-colors ml-auto">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
