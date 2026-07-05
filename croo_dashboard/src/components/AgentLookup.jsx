import React, { useState } from 'react';
import { Search, ShieldCheck, AlertTriangle, AlertOctagon, Users, Clock, TrendingUp, Zap, Flag, CreditCard } from 'lucide-react';
import { fetchTrustScore, executeService } from '../lib/api';
import { usePolling } from '../hooks/usePolling';

// Determine badge color and label from trust score
function TrustBadge({ score }) {
  const isHigh   = score >= 70;
  const isMid    = score >= 40 && score < 70;

  const config = isHigh
    ? { bg: 'bg-emerald-500/15', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400', label: 'Trusted' }
    : isMid
    ? { bg: 'bg-amber-500/15', border: 'border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400', label: 'Caution' }
    : { bg: 'bg-rose-500/15', border: 'border-rose-500/30', text: 'text-rose-400', dot: 'bg-rose-500', label: 'High Risk' };

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${config.bg} ${config.border} ${config.text}`}>
      <div className={`w-2.5 h-2.5 rounded-full ${config.dot} ${isHigh ? 'animate-pulse' : ''}`} />
      <span className="font-bold text-sm uppercase tracking-widest">{config.label}</span>
    </div>
  );
}

// Circular score ring
function ScoreRing({ score }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (score / 100) * circumference;
  const isHigh = score >= 70;
  const isMid  = score >= 40;

  const ringColor = isHigh ? '#10b981' : isMid ? '#f59e0b' : '#f43f5e';

  return (
    <div className="relative flex items-center justify-center w-36 h-36">
      <svg className="w-36 h-36 -rotate-90" viewBox="0 0 128 128">
        {/* Track */}
        <circle cx="64" cy="64" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
        {/* Progress */}
        <circle
          cx="64" cy="64" r={radius}
          fill="none"
          stroke={ringColor}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-black text-white">{score}</span>
        <span className="text-xs text-surface-400 uppercase tracking-wider">/ 100</span>
      </div>
    </div>
  );
}

// Individual metric card
function MetricCard({ icon: Icon, label, value, subtext, color = 'text-brand-400' }) {
  return (
    <div className="glass rounded-xl p-4 flex items-start gap-3">
      <div className={`p-2 rounded-lg bg-surface-800 border border-white/5 ${color} shrink-0`}>
        <Icon size={16} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-surface-400 uppercase tracking-wider mb-0.5">{label}</p>
        <p className="text-lg font-bold text-white truncate">{value}</p>
        {subtext && <p className="text-xs text-surface-500">{subtext}</p>}
      </div>
    </div>
  );
}

// Flag pill
function FlagPill({ flag }) {
  const labels = {
    high_self_trade_concentration: { label: 'Self-Trade Concentration', color: 'bg-rose-500/15 border-rose-500/25 text-rose-400' },
    low_buyer_diversity:           { label: 'Low Buyer Diversity',       color: 'bg-amber-500/15 border-amber-500/25 text-amber-400' },
    recent_account:                { label: 'Recent Account',            color: 'bg-blue-500/15 border-blue-500/25 text-blue-400' },
    high_dispute_rate:             { label: 'High Dispute Rate',         color: 'bg-rose-500/15 border-rose-500/25 text-rose-400' },
  };
  const cfg = labels[flag] || { label: flag, color: 'bg-surface-700 border-white/10 text-surface-300' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold ${cfg.color}`}>
      <Flag size={10} />
      {cfg.label}
    </span>
  );
}

export default function AgentLookup() {
  const [query, setQuery]   = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError]   = useState('');
  const [searched, setSearched] = useState(false);
  const { data } = usePolling(fetchTrustScore, 10000);
  const lookups = data || [];

  const handleLookup = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError('');
    setReport(null);
    setSearched(true);
    try {
      const data = await fetchTrustScore(trimmed);
      setReport(data);
    } catch (err) {
      setError('Failed to fetch trust report. Make sure the API is running.');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setPurchasing(true);
    setError('');
    setSearched(true);
    try {
      const data = await executeService('trust', trimmed);
      if (data) {
        const localData = await fetchTrustScore(trimmed);
        setReport(localData);
      }
    } catch (err) {
      setError('Failed to purchase trust report on-chain.');
    } finally {
      setPurchasing(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') handleLookup();
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Page Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/20">
            <ShieldCheck size={22} className="text-brand-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Agent Lookup</h2>
            <p className="text-sm text-surface-400">Independent trust report on any CROO agent — powered by on-chain data</p>
          </div>
        </div>
      </div>

      {/* Search Box */}
      <div className="glass rounded-2xl border-t border-t-white/10 p-6 animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        <label className="block text-sm font-semibold text-surface-300 mb-3">Agent ID</label>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-surface-500" />
            <input
              id="agent-lookup-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKey}
              placeholder="e.g. agent_0xabc123..."
              className="w-full bg-surface-800/80 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-surface-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/25 transition-all text-sm"
            />
          </div>
          <button
            id="agent-lookup-btn"
            onClick={handleLookup}
            disabled={loading || purchasing || !query.trim()}
            className="px-6 py-3 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-200 text-sm whitespace-nowrap flex items-center gap-2"
          >
            {loading ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Analysing…</>
            ) : (
              <><Search size={15} /> Local Look Up</>
            )}
          </button>
        </div>
        <div className="flex items-center gap-4 mt-4">
          <button
            onClick={handlePurchase}
            disabled={loading || purchasing || !query.trim()}
            className="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-400 hover:to-purple-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-all duration-200 text-sm flex items-center gap-2 shadow-[0_0_15px_rgba(139,92,246,0.3)] hover:shadow-[0_0_25px_rgba(139,92,246,0.5)] border border-white/10"
          >
            {purchasing ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Executing on Base...</>
            ) : (
              <><CreditCard size={15} /> Purchase On-Chain ($0.20)</>
            )}
          </button>
          <p className="text-xs text-surface-500">
            Click 'Purchase' to seamlessly execute the transaction on Base via the Python SDK, bypassing MetaMask entirely.
          </p>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="glass rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-center gap-3 text-rose-400 text-sm">
          <AlertOctagon size={18} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Empty state before first search */}
      {!searched && !loading && (
        <div className="glass rounded-2xl border-t border-t-white/10 p-12 flex flex-col items-center text-center animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div className="p-4 rounded-2xl bg-surface-800/80 border border-white/5 mb-4">
            <ShieldCheck size={32} className="text-surface-500" />
          </div>
          <p className="text-surface-300 font-semibold mb-1">Search for any CROO agent</p>
          <p className="text-sm text-surface-500 max-w-md">
            Enter an agent ID above to see their trust score, completion rate, dispute history, buyer diversity and account age — the same signals CROO uses to detect sybil behaviour.
          </p>
        </div>
      )}

      {/* Results */}
      {report && !loading && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Score Hero Card */}
          <div className="glass rounded-2xl border-t border-t-white/10 p-6">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
              <ScoreRing score={report.trust_score} />
              <div className="flex-1 text-center md:text-left">
                <div className="flex flex-col md:flex-row items-center md:items-start gap-3 mb-3">
                  <TrustBadge score={report.trust_score} />
                  {report.flags.length > 0 && (
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-800 border border-white/10 text-xs text-surface-400">
                      <AlertTriangle size={12} className="text-amber-400" />
                      {report.flags.length} flag{report.flags.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
                <p className="font-mono text-sm text-surface-400 mb-2 break-all">{report.target_agent_id}</p>
                <p className="text-surface-200 text-sm leading-relaxed max-w-xl">{report.summary}</p>
              </div>
              <div className="text-xs text-surface-600 text-right shrink-0">
                <p>Call ID</p>
                <p className="font-mono">{report.call_id?.slice(0, 8)}…</p>
              </div>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            <MetricCard
              icon={ShieldCheck}
              label="Completed Orders"
              value={report.completed_orders}
              subtext={`${(report.completion_rate * 100).toFixed(1)}% completion rate`}
              color="text-emerald-400"
            />
            <MetricCard
              icon={AlertTriangle}
              label="Disputed Orders"
              value={report.disputed_or_refunded_orders}
              subtext={`${(report.dispute_rate * 100).toFixed(1)}% dispute rate`}
              color={report.dispute_rate > 0.15 ? 'text-rose-400' : 'text-surface-400'}
            />
            <MetricCard
              icon={Users}
              label="Unique Buyers"
              value={report.unique_buyer_count}
              subtext="Distinct counterparties"
              color={report.unique_buyer_count < 3 ? 'text-amber-400' : 'text-brand-400'}
            />
            <MetricCard
              icon={Clock}
              label="Account Age"
              value={`${report.account_age_days}d`}
              subtext={report.account_age_days < 2 ? 'New account' : 'Since first transaction'}
              color={report.account_age_days < 2 ? 'text-blue-400' : 'text-surface-400'}
            />
            <MetricCard
              icon={TrendingUp}
              label="Total Volume"
              value={`${parseFloat(report.total_volume_usdc).toFixed(2)} USDC`}
              subtext="Lifetime settled"
              color="text-brand-400"
            />
            <MetricCard
              icon={Zap}
              label="Avg Delivery Speed"
              value={`${report.avg_delivery_vs_sla.toFixed(2)}× SLA`}
              subtext={report.avg_delivery_vs_sla <= 1 ? 'On or ahead of schedule' : 'Behind SLA target'}
              color={report.avg_delivery_vs_sla <= 1 ? 'text-emerald-400' : 'text-amber-400'}
            />
          </div>

          {/* Flags */}
          {report.flags.length > 0 && (
            <div className="glass rounded-2xl border-t border-t-white/10 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Flag size={15} className="text-amber-400" />
                <h3 className="text-sm font-semibold text-surface-200 uppercase tracking-wider">Risk Flags</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {report.flags.map((f) => <FlagPill key={f} flag={f} />)}
              </div>
            </div>
          )}

          {report.flags.length === 0 && (
            <div className="glass rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3 text-emerald-400 text-sm">
              <ShieldCheck size={18} className="shrink-0" />
              No risk flags detected — clean profile.
            </div>
          )}
        </div>
      )}

      {/* Recent Lookups (Paid on-chain) */}
      {lookups.length > 0 && (
        <div className="space-y-4 animate-fade-in-up mt-12 pt-8 border-t border-white/5">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white tracking-tight">Paid Lookups History</h3>
            <span className="bg-brand-500/20 text-brand-400 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full">On-Chain</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {lookups.map(lookup => (
              <div key={lookup.call_id || lookup.order_id} className="glass rounded-xl p-4 border border-white/5 hover:border-white/10 transition-colors cursor-pointer" onClick={() => { setQuery(lookup.target_agent_id); setTimeout(() => { setLoading(true); setError(''); setReport(null); setSearched(true); fetchTrustScore(lookup.target_agent_id).then(setReport).catch(() => setError('Failed to fetch trust report.')).finally(() => setLoading(false)); }, 0); }}>
                <div className="flex justify-between items-start mb-2">
                  <span className="font-mono text-xs text-brand-400">{lookup.target_agent_id}</span>
                  <div className={`px-2 py-0.5 rounded text-xs font-bold ${lookup.trust_score >= 70 ? 'bg-emerald-500/20 text-emerald-400' : lookup.trust_score >= 40 ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'}`}>
                    Score: {lookup.trust_score}
                  </div>
                </div>
                <div className="flex justify-between text-xs text-surface-400">
                  <span>Order: {lookup.order_id.substring(0,8)}...</span>
                  <span>{new Date(lookup.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
