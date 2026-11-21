import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigationType } from 'react-router-dom'
import footerLandscape from '../assets/misty-lake-dawn.png'
import { useAuth } from '../auth/useAuth'

function HabitusLogo() {
  return (
    <img
      className="brand-logo"
      src="/habitus-mark.svg"
      width="32"
      height="32"
      alt=""
      aria-hidden="true"
    />
  )
}

export function Layout() {
  const { user, logout, isInitializing } = useAuth()
  const { pathname, key } = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo(0, 0)
  }, [key, navigationType])

  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/">
          <HabitusLogo />
          <span>Habitus</span>
        </NavLink>
        <nav className="site-nav" aria-label="Main navigation">
          <NavLink className="nav-item" to="/" end>Home</NavLink>
          <NavLink className="nav-item" to="/practice">Practice</NavLink>
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
      <main className={pathname === '/' ? 'home-main' : 'page-container'}><Outlet /></main>
      <footer className="site-footer">
        <img
          className="footer-landscape"
          src={footerLandscape}
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
          fetchPriority="low"
          width="2172"
          height="724"
        />
        <div className="site-footer-inner">
          <div className="footer-top">
            <div className="footer-brand-block">
              <NavLink className="brand" to="/">
                <HabitusLogo />
                <span>Habitus</span>
              </NavLink>
              <p className="footer-statement">
                Build the confidence to speak a new language, one thoughtful response at a time.
              </p>
              <NavLink className="footer-practice-link" to="/practice">
                Start practising <span aria-hidden="true">→</span>
              </NavLink>
            </div>
            <div className="footer-column">
              <p className="footer-heading">Explore</p>
              <nav className="footer-nav" aria-label="Footer navigation">
                <NavLink to="/" end>Home</NavLink>
                <NavLink to="/practice">Practice</NavLink>
                <NavLink to="/about">About Habitus</NavLink>
              </nav>
            </div>
            <div className="footer-column footer-developer">
              <p className="footer-heading">Created by</p>
              <p className="footer-developer-name">Md Azizul Hakim</p>
              <p>Institute of Information Technology<br />University of Dhaka</p>
              <a href="mailto:bsse1634@iit.du.ac.bd">bsse1634@iit.du.ac.bd</a>
            </div>
          </div>
          <div className="footer-bottom">
            <p>© {new Date().getFullYear()} Habitus</p>
            <p className="footer-origin"><span aria-hidden="true">⌖</span> Originated in Dhaka, Bangladesh</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
