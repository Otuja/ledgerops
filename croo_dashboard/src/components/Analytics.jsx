import React, { useEffect, useState } from 'react';
import { BarChart, Activity, PieChart as PieChartIcon, CheckCircle } from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart as RechartsBarChart, Bar
} from 'recharts';
import { executeService, fetchLogs } from '../lib/api';

const mockChartData = [
  { name: 'Mon', volume: 400 },
  { name: 'Tue', volume: 300 },
  { name: 'Wed', volume: 550 },
  { name: 'Thu', volume: 200 },
  { name: 'Fri', volume: 700 },
  { name: 'Sat', volume: 900 },
  { name: 'Sun', volume: 850 },
];

const mockUsageData = [
  { name: 'Trust Lookups', value: 45 },
  { name: 'Tax Exports', value: 25 },
  { name: 'Tx Logging', value: 20 },
  { name: 'Analytics', value: 10 },
];

const Analytics = () => {
  const [analyticsReports, setAnalyticsReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseResult, setPurchaseResult] = useState(null);

  useEffect(() => {
    fetchLogs()
      .then((data) => {
        const reports = (Array.isArray(data) ? data : []).filter(tx =>
          tx.service_id && (
            tx.service_id.toLowerCase().includes('analytics') ||
            tx.service_id.toLowerCase().includes('report')
          )
        );
        setAnalyticsReports(reports);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handlePurchase = async () => {
    setPurchasing(true);
    setPurchaseResult(null);
    try {
      const data = await executeService('analytics');
      setPurchaseResult(data.result);
      // Could re-fetch stats here to update UI
    } catch (err) {
      setPurchaseResult(`Error: ${err.message}`);
    } finally {
      setPurchasing(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-semibold text-slate-100 flex items-center gap-3">
              <Activity className="w-8 h-8 text-fuchsia-500" />
              Network Analytics
            </h1>
            <p className="text-slate-400 mt-2 text-lg">
              On-chain volume and agent behavior trends.
            </p>
            {purchaseResult && (
              <div className="mt-4 text-sm bg-fuchsia-500/10 border border-fuchsia-500/20 text-fuchsia-300 p-3 rounded-lg flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                {purchaseResult}
              </div>
            )}
          </div>
          <button 
            onClick={handlePurchase}
            disabled={purchasing}
            className="flex items-center gap-2 bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:from-fuchsia-500 hover:to-purple-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl border border-white/10 transition-all font-bold shadow-[0_0_15px_rgba(192,38,211,0.3)] hover:shadow-[0_0_25px_rgba(192,38,211,0.5)]"
          >
            {purchasing ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Executing on Base...</>
            ) : (
              <><BarChart className="w-4 h-4" /> Buy New Report ($0.20)</>
            )}
          </button>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-md p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-fuchsia-400" />
              7-Day Agent Volume
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#d946ef" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#d946ef" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem' }}
                    itemStyle={{ color: '#e2e8f0' }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="#d946ef" strokeWidth={3} fillOpacity={1} fill="url(#colorVolume)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-md p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-6 flex items-center gap-2">
              <PieChartIcon className="w-5 h-5 text-fuchsia-400" />
              Service Popularity
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsBarChart data={mockUsageData} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{fill: '#334155', opacity: 0.4}}
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem' }}
                  />
                  <Bar dataKey="value" fill="#d946ef" radius={[0, 4, 4, 0]} barSize={20} />
                </RechartsBarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* History Table */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-md overflow-hidden">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="text-xl font-medium text-slate-200">Purchased Analytics Reports</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-900/50 text-slate-400 text-xs uppercase font-semibold">
                <tr>
                  <th className="px-6 py-4">Report ID</th>
                  <th className="px-6 py-4">Buyer Agent</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Date</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {loading ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400">Loading reports...</td>
                  </tr>
                ) : analyticsReports.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400">No analytics reports found.</td>
                  </tr>
                ) : (
                  analyticsReports.map((tx, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/60 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-mono text-slate-300 text-sm">
                          ANLY-{tx.order_id.substring(0, 8).toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-mono text-slate-400 text-sm">{tx.buyer_id.substring(0, 16)}...</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-fuchsia-400 bg-fuchsia-400/10 px-2.5 py-1 rounded-full text-xs font-medium border border-fuchsia-400/20">
                          COMPLETED
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-sm">
                        {new Date(tx.created_at || Date.now()).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="text-slate-300 hover:text-white transition-colors text-sm font-medium">
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Analytics;
