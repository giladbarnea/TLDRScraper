import './index.css'
import 'katex/dist/katex.min.css'
import React from 'react'
import ReactDOM from 'react-dom/client'
import PortfolioApp from '../../vendor/portfolio/portfolio.js'
import App from './App'
import { initQuakeConsole } from './lib/quakeConsole'

initQuakeConsole()

const isPortfolioRoute = window.location.pathname.startsWith('/portfolio')
const RootComponent = isPortfolioRoute ? PortfolioApp : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RootComponent />
  </React.StrictMode>
)
