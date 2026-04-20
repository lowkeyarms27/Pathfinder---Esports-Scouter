import { createContext, useContext, useState } from 'react'

const WatchlistContext = createContext(null)

export function WatchlistProvider({ children }) {
  const [watchlist, setWatchlist] = useState([])

  function add(player) {
    setWatchlist(prev => prev.find(p => p.id === player.id) ? prev : [...prev, player])
  }

  function remove(playerId) {
    setWatchlist(prev => prev.filter(p => p.id !== playerId))
  }

  function toggle(player) {
    const exists = watchlist.find(p => p.id === player.id)
    exists ? remove(player.id) : add(player)
  }

  function has(playerId) {
    return !!watchlist.find(p => p.id === playerId)
  }

  return (
    <WatchlistContext.Provider value={{ watchlist, add, remove, toggle, has }}>
      {children}
    </WatchlistContext.Provider>
  )
}

export function useWatchlist() {
  return useContext(WatchlistContext)
}
