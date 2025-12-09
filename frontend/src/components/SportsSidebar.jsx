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
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">Sports</h2>

      <div className="space-y-1">
        {sports.map((sport) => {
          const sportName = sport.name || sport.sport
          const sportKey = sportName?.toLowerCase().replace(' ', '-')
          return (
            <button
              key={sportName}
              onClick={() => onSelect(sportName)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg
                         transition-colors text-left ${
                selected === sportName
                  ? 'bg-betfair-gold text-dark-navy'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              <span className="flex items-center gap-2">
                <span>{sportIcons[sportKey] || '🏆'}</span>
                <span className="capitalize">{sportName?.replace('-', ' ')}</span>
              </span>
              <span className={`text-sm font-medium ${
                selected === sportName ? 'text-dark-navy' : 'text-gray-400'
              }`}>
                {sport.count}
              </span>
            </button>
          )
        })}
      </div>

      {sports.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-4">
          No sports available
        </p>
      )}
    </div>
  )
}
