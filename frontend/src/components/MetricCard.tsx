import { motion } from 'framer-motion'
import { type LucideIcon } from 'lucide-react'
import { formatNumber, formatPercentage } from '../lib/utils'
import { cn } from '../lib/utils'

interface MetricCardProps {
  title: string
  value: number
  icon: LucideIcon
  color: string
  prefix?: string
  suffix?: string
  isPercentage?: boolean
  subtitle?: string
  delay?: number
}

export function MetricCard({ title, value, icon: Icon, color, prefix = '', suffix = '', isPercentage = false, subtitle, delay = 0 }: MetricCardProps) {
  const displayValue = isPercentage ? formatPercentage(value) : prefix + formatNumber(value) + suffix

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative group"
    >
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 hover:border-slate-700 transition-all duration-300 hover:shadow-2xl hover:shadow-violet-500/5">
        <div className="flex items-start justify-between mb-4">
          <div className={cn("p-2.5 rounded-xl", color)}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Live</span>
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <h3 className="text-3xl font-bold tracking-tight text-white">{displayValue}</h3>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
          )}
        </div>

        {/* Decorative gradient */}
        <div className={cn("absolute bottom-0 left-0 right-0 h-1 rounded-b-2xl opacity-50", color)} />
      </div>
    </motion.div>
  )
}
