import { useEffect, useRef, useState } from 'react'
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isMobileView, setIsMobileView] = useState(() => window.matchMedia('(max-width: 720px)').matches)
  const headerRef = useRef<HTMLElement | null>(null)
  const menuButtonRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo(0, 0)
  }, [key, navigationType])

  useEffect(() => {
    const query = window.matchMedia('(max-width: 720px)')
    function updateViewport(event: MediaQueryListEvent) {
      setIsMobileView(event.matches)
      if (!event.matches) setMobileMenuOpen(false)
    }
    query.addEventListener('change', updateViewport)
    return () => query.removeEventListener('change', updateViewport)
  }, [])

  useEffect(() => {
    if (!mobileMenuOpen) return

    function closeOnOutsideClick(event: PointerEvent) {
      if (event.target instanceof Node && !headerRef.current?.contains(event.target)) {
        setMobileMenuOpen(false)
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setMobileMenuOpen(false)
        menuButtonRef.current?.focus()
      }
    }

    function closeOnHistoryNavigation() {
      setMobileMenuOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    window.addEventListener('popstate', closeOnHistoryNavigation)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
      window.removeEventListener('popstate', closeOnHistoryNavigation)
    }
  }, [mobileMenuOpen])

  return (
    <div className="app-shell">
      <header className="site-header" ref={headerRef}>
        <NavLink className="brand" to="/" onClick={() => setMobileMenuOpen(false)}>
          <HabitusLogo />
          <span>Habitus</span>
        </NavLink>
        <button
          className="mobile-menu-toggle"
          type="button"
          ref={menuButtonRef}
          aria-expanded={mobileMenuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          <span className="mobile-menu-icon" aria-hidden="true"><span /><span /><span /></span>
          {mobileMenuOpen ? 'Close' : 'Menu'}
        </button>
        <div
          className={`mobile-nav-panel${mobileMenuOpen ? ' is-open' : ''}`}
          inert={isMobileView && !mobileMenuOpen}
          aria-hidden={isMobileView && !mobileMenuOpen ? true : undefined}
        >
          <div className="mobile-nav-content">
            <nav
              id="primary-navigation"
              className="site-nav"
              aria-label="Main navigation"
              onClick={(event) => {
                if (event.target instanceof Element && event.target.closest('a, button')) {
                  setMobileMenuOpen(false)
                }
              }}
            >
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
          </div>
        </div>
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
