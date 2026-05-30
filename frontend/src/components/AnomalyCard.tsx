import { motion } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, Zap } from 'lucide-react'
import type { AnomalyData } from '../types'
import { cn } from '../lib/utils'
import { timeAgo } from '../lib/utils'

interface AnomalyCardProps {
  anomaly: AnomalyData
  index: number
}

const severityConfig = {
  CRITICAL: {
    icon: AlertTriangle,
    gradient: 'from-rose-500/20 to-red-600/20',
    border: 'border-rose-500/30',
    iconBg: 'bg-rose-500/20',
    iconColor: 'text-rose-400',
    badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  },
  WARN: {
    icon: AlertCircle,
    gradient: 'from-amber-500/20 to-orange-600/20',
    border: 'border-amber-500/30',
    iconBg: 'bg-amber-500/20',
    iconColor: 'text-amber-400',
    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  },
  INFO: {
    icon: Info,
    gradient: 'from-blue-500/20 to-cyan-600/20',
    border: 'border-blue-500/30',
    iconBg: 'bg-blue-500/20',
    iconColor: 'text-blue-400',
    badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
}

export function AnomalyCard({ anomaly, index }: AnomalyCardProps) {
  const config = severityConfig[anomaly.severity]
  const Icon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className={cn(
        "relative overflow-hidden rounded-xl border p-4 bg-gradient-to-br",
        config.gradient,
        config.border
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn("p-2 rounded-lg shrink-0", config.iconBg)}>
          <Icon className={cn("w-4 h-4", config.iconColor)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-white text-sm">{anomaly.anomaly_type}</span>
            <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border", config.badge)}>
              {anomaly.severity}
            </span>
          </div>
          <p className="text-sm text-slate-300 mb-2 leading-relaxed">{anomaly.message}</p>
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Zap className="w-3 h-3" />
            <span className="italic">{anomaly.suggested_action}</span>
          </div>
        </div>
        <span className="text-[10px] text-slate-500 shrink-0">{timeAgo(anomaly.created_at)}</span>
      </div>
    </motion.div>
  )
}
