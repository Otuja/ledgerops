import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export default function RevenueChart({ logs }) {
  // Generate some realistic-looking volume data if there aren't enough logs
  const data = useMemo(() => {
    return logs && logs.length > 5 ? processLogs(logs) : generateMockData();
  }, [JSON.stringify(logs)]);

  return (
    <div className="glass rounded-2xl p-6 border-t border-t-white/10 h-full flex flex-col animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white tracking-tight">Transaction Volume</h3>
        <p className="text-sm text-surface-400">7-day rolling transaction volume (USDC)</p>
      </div>

      <div className="flex-1 w-full min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#9333ea" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis 
              dataKey="date" 
              stroke="rgba(255,255,255,0.3)" 
              fontSize={12}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis 
              stroke="rgba(255,255,255,0.3)" 
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `$${value}`}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                borderColor: 'rgba(255,255,255,0.1)',
                borderRadius: '12px',
                color: '#fff',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)'
              }}
              itemStyle={{ color: '#22d3ee' }}
            />
            <Area 
              type="monotone" 
              dataKey="volume" 
              stroke="#22d3ee" 
              strokeWidth={3}
              fillOpacity={1} 
              fill="url(#colorVolume)" 
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Helper to process actual logs into chart data
function processLogs(logs) {
  // Simple grouping by date
  const grouped = {};
  logs.forEach(log => {
    const date = new Date(log.timestamp).toLocaleDateString('en-US', { weekday: 'short' });
    grouped[date] = (grouped[date] || 0) + (parseFloat(log.amount_usdc || 0) / 1_000_000);
  });
  return Object.keys(grouped).map(date => ({
    date,
    volume: grouped[date]
  }));
}

// Generate beautiful mock data curve
function generateMockData() {
  return [
    { date: 'Mon', volume: 1200 },
    { date: 'Tue', volume: 2100 },
    { date: 'Wed', volume: 1800 },
    { date: 'Thu', volume: 3400 },
    { date: 'Fri', volume: 2900 },
    { date: 'Sat', volume: 4800 },
    { date: 'Sun', volume: 5600 },
  ];
}
