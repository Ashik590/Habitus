import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

function HabitusLogo() {
  return (
    <svg
      className="brand-logo"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <path d="M8 7v10" />
      <path d="M16 7v10" />
      <path d="M8 12h8" />
    </svg>
  )
}

export function Layout() {
  const { user, logout, isInitializing } = useAuth()
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/">
          <HabitusLogo />
          <span>Habitus</span>
        </NavLink>
        <nav className="site-nav" aria-label="Main navigation">
          <NavLink className="nav-item" to="/" end>Home</NavLink>
          <NavLink className="nav-item" to="/languages">Languages</NavLink>
          <NavLink className="nav-item" to="/about">About</NavLink>
          {isInitializing ? null : user ? (
            <>
              <NavLink className="nav-item" to="/profile">Dashboard</NavLink>
              <span className="nav-divider" aria-hidden="true" />
              <button className="nav-item nav-logout-btn" type="button" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink className="nav-item" to="/login">Log in</NavLink>
              <span className="nav-divider" aria-hidden="true" />
              <NavLink className="button small nav-cta-btn" to="/register">Create account</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="page-container"><Outlet /></main>
    </div>
  )
}
