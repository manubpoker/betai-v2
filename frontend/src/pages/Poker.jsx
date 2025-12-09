export default function Poker() {
  const tables = [
    { name: 'Texas Hold\'em', stakes: '$0.01/$0.02 - $100/$200', players: '24,512' },
    { name: 'Omaha', stakes: '$0.05/$0.10 - $50/$100', players: '8,234' },
    { name: 'Sit & Go', stakes: '$1 - $500', players: '3,456' },
    { name: 'Tournaments', stakes: 'Various', players: '12,789' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Poker</h1>

      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <p className="text-gray-300">
          Welcome to the poker lobby. Choose from cash games, sit & go, or tournaments.
          This section is a placeholder - full poker functionality coming soon.
        </p>
      </div>

      {/* Lobby interface placeholder */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="bg-gray-700 px-4 py-3 border-b border-gray-600">
          <h2 className="font-medium text-white">Lobby</h2>
        </div>

        <div className="divide-y divide-gray-700">
          {tables.map((table) => (
            <div
              key={table.name}
              className="px-4 py-4 hover:bg-gray-700 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-white">{table.name}</h3>
                  <p className="text-sm text-gray-400">Stakes: {table.stakes}</p>
                </div>
                <div className="text-right">
                  <p className="text-betfair-gold font-medium">{table.players}</p>
                  <p className="text-sm text-gray-400">players online</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
