export default function Casino() {
  const games = [
    { name: 'Slots', icon: '🎰' },
    { name: 'Roulette', icon: '🎡' },
    { name: 'Blackjack', icon: '🃏' },
    { name: 'Poker', icon: '♠️' },
    { name: 'Baccarat', icon: '💎' },
    { name: 'Craps', icon: '🎲' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Casino</h1>

      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <p className="text-gray-300">
          Casino games are coming soon. This section will feature slots, table games,
          and live dealer options.
        </p>
      </div>

      {/* Game grid placeholder */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {games.map((game) => (
          <div
            key={game.name}
            className="bg-gray-800 rounded-lg p-6 text-center hover:bg-gray-700
                       transition-colors cursor-pointer"
          >
            <div className="text-4xl mb-2">{game.icon}</div>
            <h3 className="font-medium text-white">{game.name}</h3>
            <p className="text-sm text-gray-400 mt-1">Coming Soon</p>
          </div>
        ))}
      </div>
    </div>
  )
}
