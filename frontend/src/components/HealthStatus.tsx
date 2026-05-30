import { motion } from 'framer-motion'
import { Server, Wifi, WifiOff, Clock } from 'lucide-react'
import type { HealthData } from '../types'
import { timeAgo } from '../lib/utils'
import { cn } from '../lib/utils'

interface HealthStatusProps {
  data: HealthData | null
}

export function HealthStatus({ data }: HealthStatusProps) {
  if (!data) {
    return (
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500" />
        </div>
      </div>
    )
  }

  const isHealthy = data.service === 'healthy'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className={cn(
          "p-2 rounded-lg",
          isHealthy ? "bg-emerald-500/20" : "bg-rose-500/20"
        )}>
          <Server className={cn("w-4 h-4", isHealthy ? "text-emerald-400" : "text-rose-400")} />
        </div>
        <div>
          <h3 className="font-semibold text-white">System Health</h3>
          <p className="text-xs text-slate-400">{data.stores.length} stores monitored</p>
        </div>
        <div className={cn(
          "ml-auto px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border",
          isHealthy 
            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
        )}>
          {data.service}
        </div>
      </div>

      <div className="space-y-3">
        {data.stores.map((store, idx) => (
          <motion.div
            key={store.store_id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.05 }}
            className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
          >
            <div className="flex items-center gap-3">
              {store.status === 'ACTIVE' ? (
                <Wifi className="w-4 h-4 text-emerald-400" />
              ) : (
                <WifiOff className="w-4 h-4 text-rose-400" />
              )}
              <div>
                <p className="text-sm font-medium text-white">{store.store_id}</p>
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="w-3 h-3" />
                  {timeAgo(store.last_event_timestamp)}
                </div>
              </div>
            </div>
            <div className={cn(
              "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
              store.status === 'ACTIVE'
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-rose-500/10 text-rose-400"
            )}>
              {store.status}
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
