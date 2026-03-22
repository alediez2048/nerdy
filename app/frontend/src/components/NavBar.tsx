// PC-10: Persistent navigation bar + Clerk auth
import { useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { colors, font } from '../design/tokens'
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'

function ThemeToggle() {
  const [light, setLight] = useState(() => localStorage.getItem('theme') === 'light')

  useEffect(() => {
    document.body.classList.toggle('light-mode', light)
    localStorage.setItem('theme', light ? 'light' : 'dark')
  }, [light])

  return (
    <button onClick={() => setLight(!light)} style={s.themeToggle}>
      {light ? '☾ Dark' : '☀ Light'}
    </button>
  )
}

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (path: string) => {
    if (path === '/campaigns') {
      return location.pathname.startsWith('/campaigns')
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`)
  }

  return (
    <nav style={s.bar}>
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
      <div style={s.center}>
        <button
          onClick={() => navigate('/dashboard')}
          style={isActive('/dashboard') ? s.navLinkActive : s.navLink}
        >
          Dashboard
        </button>
        <button
          onClick={() => navigate('/campaigns')}
          style={isActive('/campaigns') ? s.navLinkActive : s.navLink}
        >
          Campaigns
        </button>
        <button
          onClick={() => navigate('/sessions')}
          style={isActive('/sessions') ? s.navLinkActive : s.navLink}
        >
          Sessions
        </button>
        <button
          onClick={() => navigate('/ads')}
          style={isActive('/ads') ? s.navLinkActive : s.navLink}
        >
          Ad Library
        </button>
        <button
          onClick={() => navigate('/competitive')}
          style={isActive('/competitive') ? s.navLinkActive : s.navLink}
        >
          Competitive
        </button>
        <button
          onClick={() => navigate('/curated')}
          style={isActive('/curated') ? s.navLinkActive : s.navLink}
        >
          Curated Set
        </button>
      </div>
      <div style={s.right}>
        <ThemeToggle />
        <SignedIn>
          <UserButton />
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button style={s.signInBtn}>Sign In</button>
          </SignInButton>
        </SignedOut>
      </div>
    </nav>
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
}
