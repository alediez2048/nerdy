import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider, useAuth } from '@clerk/clerk-react'
import { registerClerkTokenGetter } from './api/auth'
import './index.css'
import App from './App.tsx'

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string

if (!CLERK_KEY) {
  console.warn('Missing VITE_CLERK_PUBLISHABLE_KEY — running without Clerk auth')
}

/** Registers Clerk's getToken with the API auth module. Only renders inside ClerkProvider. */
function ClerkTokenRegistrar() {
  const { getToken } = useAuth()
  useEffect(() => {
    registerClerkTokenGetter(() => getToken())
  }, [getToken])
  return null
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {CLERK_KEY ? (
      <ClerkProvider
        publishableKey={CLERK_KEY}
        appearance={{
          layout: {
            unsafe_disableDevelopmentModeWarnings: true,
          },
          variables: {
            colorPrimary: '#00f0ff',
            colorBackground: '#0a0a0f',
            colorText: '#f0f0f5',
            colorTextSecondary: '#6b7280',
            colorInputBackground: '#12121a',
            colorInputText: '#f0f0f5',
            borderRadius: '10px',
          },
          elements: {
            footerAction: { display: 'none' },
            footer: { display: 'none' },
            card: { backgroundColor: '#0a0a0f', border: '1px solid rgba(0,240,255,0.15)' },
            headerTitle: { color: '#f0f0f5' },
            headerSubtitle: { color: '#6b7280' },
            socialButtonsBlockButton: { borderColor: 'rgba(0,240,255,0.2)' },
            formFieldInput: { borderColor: 'rgba(0,240,255,0.2)' },
            userButtonPopoverCard: { backgroundColor: '#0a0a0f', border: '1px solid rgba(0,240,255,0.15)' },
            userButtonPopoverActionButton: { color: '#f0f0f5' },
            userButtonPopoverActionButtonText: { color: '#f0f0f5' },
            userButtonPopoverFooter: { display: 'none' },
          },
        }}
      >
        <ClerkTokenRegistrar />
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>,
)
