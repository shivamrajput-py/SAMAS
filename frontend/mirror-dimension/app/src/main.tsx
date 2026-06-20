import { createRoot } from 'react-dom/client'
import '@fontsource/outfit/700.css'
import '@fontsource/outfit/900.css'
import '@fontsource/inter/300.css'
import '@fontsource/inter/400.css'
import '@fontsource/space-mono/400.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(<App />)
