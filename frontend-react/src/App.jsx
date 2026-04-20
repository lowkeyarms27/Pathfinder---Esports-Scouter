import { Routes, Route } from 'react-router-dom'
import { WatchlistProvider } from './context/WatchlistContext'
import Navbar from './components/Navbar'
import Discover from './pages/Discover'
import PlayerProfile from './pages/PlayerProfile'
import Watchlist from './pages/Watchlist'
import Scout from './pages/Scout'

export default function App() {
  return (
    <WatchlistProvider>
      <Navbar />
      <Routes>
        <Route path="/"              element={<Discover />} />
        <Route path="/player/:id"    element={<PlayerProfile />} />
        <Route path="/watchlist"     element={<Watchlist />} />
        <Route path="/scout"         element={<Scout />} />
      </Routes>
    </WatchlistProvider>
  )
}
