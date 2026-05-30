import { motion } from 'framer-motion'
import { Flame, AlertCircle } from 'lucide-react'
import type { HeatmapData } from '../types'
import { formatDuration } from '../lib/utils'

interface HeatmapChartProps {
  data: HeatmapData | null
  loading: boolean
}

export function HeatmapChart({ data, loading }: HeatmapChartProps) {
  if (loading) {
    return (
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 h-[400px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500" />
      </div>
    )
  }

  if (!data || !data.zones.length) {
    return (
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 h-[400px] flex items-center justify-center">
        <p className="text-slate-500">No heatmap data available</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-orange-500 to-red-500">
            <Flame className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Zone Heatmap</h3>
            <p className="text-xs text-slate-400">Visit frequency & dwell time</p>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
          data.data_confidence === 'HIGH' 
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        }`}>
          <AlertCircle className="w-3 h-3" />
          {data.data_confidence} Confidence
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {data.zones.map((zone, idx) => (
          <motion.div
            key={zone.zone_id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
            className="group relative bg-slate-800/50 rounded-xl p-4 hover:bg-slate-800 transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-white">{zone.zone_id}</span>
              <span className="text-xs font-medium text-slate-400">
                {zone.visit_frequency} visits
              </span>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${zone.normalized_score}%` }}
                    transition={{ duration: 0.8, delay: idx * 0.1 }}
                    className="h-full bg-gradient-to-r from-orange-400 to-red-500 rounded-full"
                  />
                </div>
              </div>
              <div className="text-right min-w-[80px]">
                <span className="text-xs text-slate-400">Avg dwell</span>
                <p className="text-sm font-semibold text-white">{formatDuration(zone.avg_dwell_ms)}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
