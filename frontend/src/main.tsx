import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource/source-sans-3/400.css'
import '@fontsource/source-sans-3/600.css'
import '@fontsource/source-sans-3/700.css'
import '@fontsource/newsreader/500.css'
import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router'
import './styles.css'

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 60000, refetchOnWindowFocus: false } } })
const App = lazy(() => import('./App'))
const SquadStudio = lazy(() => import('./SquadStudio'))
const Players = lazy(() => import('./Players'))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><BrowserRouter><Suspense fallback={<p className="connection-state" role="status">Loading Scout…</p>}><Routes>
    <Route path="/" element={<SquadStudio />} />
    <Route path="/scout" element={<App />} />
    <Route path="/players" element={<Players />} />
    <Route path="*" element={<SquadStudio />} />
  </Routes></Suspense></BrowserRouter></QueryClientProvider></React.StrictMode>,
)
