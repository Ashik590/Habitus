import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function Layout() {
  const { user, logout } = useAuth()
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/">BhashaLab</NavLink>
        <nav aria-label="Main navigation">
          <NavLink to="/languages">Languages</NavLink>
          {user ? (
            <><NavLink to="/profile">Profile</NavLink><button className="link-button" type="button" onClick={logout}>Log out</button></>
          ) : (
            <><NavLink to="/login">Log in</NavLink><NavLink className="button small" to="/register">Create account</NavLink></>
          )}
        </nav>
      </header>
      <main className="page-container"><Outlet /></main>
    </div>
  )
}
