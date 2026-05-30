import { motion } from 'framer-motion'
import { Filter, ArrowDownRight } from 'lucide-react'
import type { FunnelData } from '../types'
import { formatNumber } from '../lib/utils'

interface FunnelChartProps {
  data: FunnelData | null
  loading: boolean
}

const stageColors = [
  'from-violet-500 to-indigo-600',
  'from-indigo-500 to-blue-600',
  'from-blue-500 to-cyan-600',
  'from-cyan-500 to-emerald-600',
]

export function FunnelChart({ data, loading }: FunnelChartProps) {
  if (loading) {
    return (
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 h-[400px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500" />
      </div>
    )
  }

  if (!data || !data.stages.length) {
    return (
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 h-[400px] flex items-center justify-center">
        <p className="text-slate-500">No funnel data available</p>
      </div>
    )
  }

  const maxCount = Math.max(...data.stages.map(s => s.count))

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500">
          <Filter className="w-4 h-4 text-white" />
        </div>
        <div>
          <h3 className="font-semibold text-white">Conversion Funnel</h3>
          <p className="text-xs text-slate-400">{data.total_sessions} total sessions</p>
        </div>
      </div>

      <div className="space-y-3">
        {data.stages.map((stage, idx) => {
          const width = maxCount > 0 ? (stage.count / maxCount) * 100 : 0
          const dropOff = stage.drop_off_pct

          return (
            <div key={stage.stage} className="relative">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-medium text-slate-300">{stage.stage}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{formatNumber(stage.count)}</span>
                  {dropOff !== null && dropOff > 0 && (
                    <span className="flex items-center gap-0.5 text-xs text-rose-400">
                      <ArrowDownRight className="w-3 h-3" />
                      {dropOff.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
              <div className="h-10 bg-slate-800/50 rounded-lg overflow-hidden relative">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${width}%` }}
                  transition={{ duration: 0.8, delay: idx * 0.15, ease: "easeOut" }}
                  className={`h-full bg-gradient-to-r ${stageColors[idx]} rounded-lg flex items-center px-3`}
                >
                  <span className="text-xs font-semibold text-white/90 whitespace-nowrap">
                    {width > 15 ? `${width.toFixed(0)}%` : ''}
                  </span>
                </motion.div>
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
