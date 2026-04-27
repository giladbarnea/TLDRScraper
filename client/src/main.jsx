import './index.css'
import 'katex/dist/katex.min.css'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import GroupCartApp from './groupCart/GroupCartApp'
import { initQuakeConsole } from './lib/quakeConsole'

initQuakeConsole()

const isGroupCartRoute = window.location.pathname.startsWith('/group-cart')
const RootComponent = isGroupCartRoute ? GroupCartApp : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RootComponent />
  </React.StrictMode>
)
