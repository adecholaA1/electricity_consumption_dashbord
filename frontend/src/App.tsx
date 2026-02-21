import "./App.css"
import ChartAreaInteractive from "./curves"
import { ThemeProvider } from "./components/ui/theme-provider"
import { BrowserRouter, Routes, Route } from "react-router-dom"

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChartAreaInteractive />} />
          <Route path="/load" element={<ChartAreaInteractive />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App