// API Configuration
// In production, this points to the Railway backend
// In development, it's empty (uses Vite proxy to localhost:3001)

export const API_BASE = import.meta.env.PROD
  ? 'https://betai-v2-production.up.railway.app'
  : ''
