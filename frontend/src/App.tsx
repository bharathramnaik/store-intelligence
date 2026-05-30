import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { AnomaliesPage } from './pages/AnomaliesPage'
import { HealthPage } from './pages/HealthPage'

function App() {
  const [storeId, setStoreId] = useState('STORE_BLR_002')

  return (
    <BrowserRouter>
      <Layout storeId={storeId} onStoreChange={setStoreId}>
        <Routes>
          <Route path="/" element={<Dashboard storeId={storeId} />} />
          <Route path="/anomalies" element={<AnomaliesPage storeId={storeId} />} />
          <Route path="/health" element={<HealthPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
