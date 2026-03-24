// PC-10: Persistent navigation bar + Clerk auth
import { useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { colors, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'

import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'

const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [light, setLight] = useState(() => localStorage.getItem('theme') === 'light')

  useEffect(() => {
    document.body.classList.toggle('light-mode', light)
    localStorage.setItem('theme', light ? 'light' : 'dark')
  }, [light])

  return (
    <button onClick={() => setLight(!light)} style={s.themeToggle}>
      {compact ? (light ? '☾' : '☀') : light ? '☾ Dark' : '☀ Light'}
    </button>
  )
}

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const isMobile = useMediaQuery('(max-width: 900px)')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname, isMobile])

  const isActive = (path: string) => {
    if (path === '/campaigns') {
      return location.pathname.startsWith('/campaigns')
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`)
  }

  const navItems = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/campaigns', label: 'Campaigns' },
    { path: '/sessions', label: 'Sessions' },
    { path: '/ads', label: 'Ad Library' },
    { path: '/competitive', label: 'Competitive' },
    { path: '/curated', label: 'Curated Set' },
  ]

  return (
    <>
      <nav style={{ ...s.bar, ...(isMobile ? s.barMobile : {}) }}>
        <div style={s.left}>
          <a
            href="/campaigns"
            onClick={(e) => {
              e.preventDefault()
              navigate('/campaigns')
            }}
            style={s.logo}
            aria-label="Go to Campaigns"
          >
            <img src="/nerdy-logo.png" alt="Nerdy" style={s.logoImg} />
          </a>
        </div>
        {!isMobile && (
          <div style={s.center}>
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                style={isActive(item.path) ? s.navLinkActive : s.navLink}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
        <div style={s.right}>
          <ThemeToggle compact={isMobile} />
          {!isMobile && CLERK_ENABLED && (
            <>
              <SignedIn>
                <UserButton />
              </SignedIn>
              <SignedOut>
                <SignInButton mode="modal">
                  <button style={s.signInBtn}>Sign In</button>
                </SignInButton>
              </SignedOut>
            </>
          )}
          {isMobile ? (
            <button
              onClick={() => setMenuOpen((open) => !open)}
              style={s.menuBtn}
              aria-expanded={menuOpen}
              aria-label="Toggle navigation menu"
            >
              {menuOpen ? 'Close' : 'Menu'}
            </button>
          ) : null}
        </div>
      </nav>
      {isMobile && menuOpen && (
        <div style={s.mobileMenu}>
          <div style={s.mobileMenuInner}>
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                style={isActive(item.path) ? s.mobileNavLinkActive : s.mobileNavLink}
              >
                {item.label}
              </button>
            ))}
            {CLERK_ENABLED && (
              <div style={s.mobileAuthRow}>
                <SignedIn>
                  <UserButton />
                </SignedIn>
                <SignedOut>
                  <SignInButton mode="modal">
                    <button style={s.signInBtn}>Sign In</button>
                  </SignInButton>
                </SignedOut>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

const s: Record<string, React.CSSProperties> = {
  bar: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: '64px',
    background: colors.surface,
    borderBottom: `1px solid ${colors.muted}20`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 24px',
    zIndex: 1000,
    fontFamily: font.family,
  },
  barMobile: {
    padding: '0 14px',
  },
  left: {
    display: 'flex',
    alignItems: 'center',
  },
  logo: {
    display: 'block',
    textDecoration: 'none',
  },
  logoImg: {
    width: '92px',
    height: 'auto',
    display: 'block',
  },
  center: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
    flex: 1,
    justifyContent: 'center',
  },
  navLink: {
    background: 'transparent',
    border: 'none',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    fontFamily: font.family,
    padding: '8px 0',
    textDecoration: 'none',
    position: 'relative',
  },
  navLinkActive: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    fontFamily: font.family,
    padding: '8px 0',
    textDecoration: 'none',
    position: 'relative',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  menuBtn: {
    padding: '8px 14px',
    borderRadius: '100px',
    border: `1px solid ${colors.cyan}40`,
    background: `${colors.cyan}14`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: font.family,
    fontWeight: 600,
  },
  signInBtn: {
    padding: '8px 16px',
    borderRadius: '100px',
    border: `1px solid ${colors.cyan}`,
    background: 'transparent',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: font.family,
    fontWeight: 600,
  },
  themeToggle: {
    padding: '8px 16px',
    borderRadius: '100px',
    border: `1px solid ${colors.muted}40`,
    background: `${colors.muted}10`,
    color: colors.white,
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: font.family,
  },
  mobileMenu: {
    position: 'fixed',
    top: '64px',
    left: 0,
    right: 0,
    zIndex: 999,
    background: 'rgba(32, 35, 68, 0.94)',
    borderBottom: `1px solid ${colors.muted}20`,
    backdropFilter: 'blur(12px)',
  },
  mobileMenuInner: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '12px 14px 16px',
  },
  mobileNavLink: {
    background: 'transparent',
    border: `1px solid ${colors.muted}20`,
    color: colors.white,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    fontFamily: font.family,
    padding: '12px 14px',
    textAlign: 'left' as const,
    borderRadius: '14px',
  },
  mobileNavLinkActive: {
    background: `${colors.cyan}14`,
    border: `1px solid ${colors.cyan}40`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    fontFamily: font.family,
    padding: '12px 14px',
    textAlign: 'left' as const,
    borderRadius: '14px',
  },
  mobileAuthRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    paddingTop: '4px',
  },
}
