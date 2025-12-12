export default function SportsSidebar({ sports, selected, onSelect }) {
  // Icons for common sports
  const sportIcons = {
    'football': '⚽',
    'tennis': '🎾',
    'horse-racing': '🏇',
    'basketball': '🏀',
    'golf': '⛳',
    'cricket': '🏏',
  }

  return (
    <div className="bf-card">
      {/* Header */}
      <div className="bg-betfair-dark px-3 py-2">
        <h2 className="text-white font-semibold text-sm">Popular</h2>
      </div>

      {/* Sports list */}
      <div className="divide-y divide-gray-200">
        {sports.map((sport) => {
          const sportName = sport.name || sport.sport
          const sportKey = sportName?.toLowerCase().replace(' ', '-')
          const isActive = selected === sportName

          return (
            <button
              key={sportName}
              onClick={() => onSelect(sportName)}
              className={`w-full sport-item ${isActive ? 'active' : ''}`}
            >
              <span className="flex items-center gap-2">
                <span className="text-base">{sportIcons[sportKey] || '🏆'}</span>
                <span className="capitalize text-betfair-black">
                  {sportName?.replace('-', ' ')}
                </span>
              </span>
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                isActive
                  ? 'bg-betfair-black/20 text-betfair-black'
                  : 'bg-gray-200 text-betfair-gray'
              }`}>
                {sport.count}
              </span>
            </button>
          )
        })}
      </div>

      {sports.length === 0 && (
        <p className="text-betfair-gray text-sm text-center py-4">
          No sports available
        </p>
      )}

      {/* Quick links */}
      <div className="border-t border-gray-200 px-3 py-3">
        <div className="text-xs font-semibold text-betfair-gray uppercase mb-2">Quick Links</div>
        <div className="space-y-1">
          <button className="w-full text-left text-sm text-betfair-black hover:text-ai-accent transition-colors py-1">
            In-Play Markets
          </button>
          <button className="w-full text-left text-sm text-betfair-black hover:text-ai-accent transition-colors py-1">
            Starting Soon
          </button>
        </div>
      </div>
    </div>
  )
}
