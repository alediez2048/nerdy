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
      <ClerkProvider publishableKey={CLERK_KEY}>
        <ClerkTokenRegistrar />
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>,
)
