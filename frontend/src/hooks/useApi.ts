import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import type { MetricData, FunnelData, HeatmapData, AnomalyData, HealthData } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
})

interface UseApiOptions {
  refreshInterval?: number
  enabled?: boolean
}

export function useMetrics(storeId: string, options: UseApiOptions = {}) {
  const { refreshInterval = 10000, enabled = true } = options
  const [data, setData] = useState<MetricData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const lastData = useRef<MetricData | null>(null)

  const fetch = useCallback(async () => {
    try {
      const res = await api.get<MetricData>(`/stores/${storeId}/metrics`)
      lastData.current = res.data
      setData(res.data)
      setError(null)
    } catch (err) {
      setError(axios.isAxiosError(err) ? err.message : 'Unknown error')
      // Keep last known data
      if (lastData.current) setData(lastData.current)
    } finally {
      setLoading(false)
    }
  }, [storeId])

  useEffect(() => {
    if (!enabled) return
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, enabled, refreshInterval])

  return { data, loading, error, refetch: fetch }
}

export function useFunnel(storeId: string, options: UseApiOptions = {}) {
  const { refreshInterval = 15000, enabled = true } = options
  const [data, setData] = useState<FunnelData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    try {
      const res = await api.get<FunnelData>(`/stores/${storeId}/funnel`)
      setData(res.data)
      setError(null)
    } catch (err) {
      setError(axios.isAxiosError(err) ? err.message : 'Unknown error')
      console.error('Funnel fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [storeId])

  useEffect(() => {
    if (!enabled) return
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, enabled, refreshInterval])

  return { data, loading, error }
}

export function useHeatmap(storeId: string, options: UseApiOptions = {}) {
  const { refreshInterval = 20000, enabled = true } = options
  const [data, setData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const res = await api.get<HeatmapData>(`/stores/${storeId}/heatmap`)
      setData(res.data)
    } catch (err) {
      console.error('Heatmap fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [storeId])

  useEffect(() => {
    if (!enabled) return
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, enabled, refreshInterval])

  return { data, loading }
}

export function useAnomalies(storeId: string, options: UseApiOptions = {}) {
  const { refreshInterval = 10000, enabled = true } = options
  const [data, setData] = useState<AnomalyData[]>([])
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const res = await api.get<AnomalyData[]>(`/stores/${storeId}/anomalies`)
      setData(res.data || [])
    } catch (err) {
      console.error('Anomalies fetch error:', err)
      setData([])
    } finally {
      setLoading(false)
    }
  }, [storeId])

  useEffect(() => {
    if (!enabled) return
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, enabled, refreshInterval])

  return { data, loading }
}

export function useHealth(options: UseApiOptions = {}) {
  const { refreshInterval = 5000, enabled = true } = options
  const [data, setData] = useState<HealthData | null>(null)

  const fetch = useCallback(async () => {
    try {
      const res = await api.get<HealthData>('/health')
      setData(res.data)
    } catch (err) {
      console.error('Health fetch error:', err)
    }
  }, [])

  useEffect(() => {
    if (!enabled) return
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, enabled, refreshInterval])

  return { data }
}
