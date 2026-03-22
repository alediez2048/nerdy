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
            colorPrimary: '#17e2ea',
            colorBackground: '#0a0f1a',
            colorText: '#ffffff',
            colorTextSecondary: '#8892a4',
            colorInputBackground: '#141a2a',
            colorInputText: '#ffffff',
            borderRadius: '10px',
          },
          elements: {
            footerAction: { display: 'none' },
            footer: { display: 'none' },
            card: { backgroundColor: '#0a0f1a', border: '1px solid rgba(136,146,164,0.15)' },
            headerTitle: { color: '#ffffff' },
            headerSubtitle: { color: '#8892a4' },
            socialButtonsBlockButton: { borderColor: 'rgba(136,146,164,0.3)' },
            formFieldInput: { borderColor: 'rgba(136,146,164,0.3)' },
            userButtonPopoverCard: { backgroundColor: '#0a0f1a', border: '1px solid rgba(136,146,164,0.15)' },
            userButtonPopoverActionButton: { color: '#ffffff' },
            userButtonPopoverActionButtonText: { color: '#ffffff' },
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
