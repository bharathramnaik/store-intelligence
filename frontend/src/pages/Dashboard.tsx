import { useState, useMemo } from 'react'
import { Users, ShoppingCart, Timer, UsersRound, DoorOpen, AlertTriangle } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { FunnelChart } from '../components/FunnelChart'
import { HeatmapChart } from '../components/HeatmapChart'
import { LiveLineChart } from '../components/LiveLineChart'
import { useMetrics, useFunnel, useHeatmap } from '../hooks/useApi'

interface DashboardProps {
  storeId: string
}

function generateMockHistory(baseValue: number, points: number = 20) {
  return Array.from({ length: points }, (_, i) => ({
    time: `${String(Math.floor(i / 2)).padStart(2, '0')}:${String((i % 2) * 30).padStart(2, '0')}`,
    value: Math.max(0, baseValue + Math.sin(i * 0.5) * baseValue * 0.3 + (Math.random() - 0.5) * baseValue * 0.2),
  }))
}

export function Dashboard({ storeId }: DashboardProps) {
  const { data: metrics, loading: metricsLoading, error: metricsError } = useMetrics(storeId, { refreshInterval: 8000 })
  const { data: funnel, loading: funnelLoading } = useFunnel(storeId, { refreshInterval: 15000 })
  const { data: heatmap, loading: heatmapLoading } = useHeatmap(storeId, { refreshInterval: 20000 })

  const visitorHistory = useMemo(() => 
    generateMockHistory(metrics?.unique_visitors || 50), 
    [metrics?.unique_visitors]
  )

  const conversionHistory = useMemo(() => 
    generateMockHistory((metrics?.conversion_rate || 0.3) * 100, 20), 
    [metrics?.conversion_rate]
  )

  return (
    <div className="space-y-6">
      {metricsError && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span className="text-sm text-red-300">{metricsError}</span>
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Dashboard</h2>
          <p className="text-sm text-slate-400 mt-1">Real-time store analytics for {storeId}</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Live Data</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Unique Visitors"
          value={metrics?.unique_visitors || 0}
          icon={Users}
          color="bg-gradient-to-br from-violet-500 to-purple-600"
          delay={0}
        />
        <MetricCard
          title="Conversion Rate"
          value={metrics?.conversion_rate || 0}
          icon={ShoppingCart}
          color="bg-gradient-to-br from-emerald-500 to-teal-600"
          isPercentage
          delay={0.1}
        />
        <MetricCard
          title="Avg Dwell"
          value={Object.values(metrics?.avg_dwell_per_zone || {}).reduce((a, b) => a + b, 0) / Math.max(Object.keys(metrics?.avg_dwell_per_zone || {}).length, 1)}
          icon={Timer}
          color="bg-gradient-to-br from-blue-500 to-cyan-600"
          suffix="ms"
          delay={0.2}
        />
        <MetricCard
          title="Queue Depth"
          value={metrics?.queue_depth || 0}
          icon={UsersRound}
          color="bg-gradient-to-br from-orange-500 to-red-600"
          delay={0.3}
        />
        <MetricCard
          title="Abandonment"
          value={metrics?.abandonment_rate || 0}
          icon={DoorOpen}
          color="bg-gradient-to-br from-rose-500 to-pink-600"
          isPercentage
          delay={0.4}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FunnelChart data={funnel} loading={funnelLoading} />
        <HeatmapChart data={heatmap} loading={heatmapLoading} />
      </div>

      {/* Live Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiveLineChart 
          title="Visitor Trend (Last Hour)" 
          data={visitorHistory} 
          color="#8b5cf6"
        />
        <LiveLineChart 
          title="Conversion Trend (Last Hour)" 
          data={conversionHistory} 
          color="#10b981"
        />
      </div>
    </div>
  )
}
