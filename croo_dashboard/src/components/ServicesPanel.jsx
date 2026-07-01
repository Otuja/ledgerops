import React from 'react';
import { Activity, Wallet, FileSpreadsheet, ShieldCheck, BarChart2, Search } from 'lucide-react';

const selfServiceTools = [
  {
    id: 'srv_log',
    name: 'Automated Transaction Logging',
    price: '0.2 USDC',
    deliverable: 'Text (Transaction Receipt)',
    description: 'Self-service: Securely log a completed transaction into the LedgerOps database. Verifies the payment, credits the receiving agent\'s virtual wallet, and returns a success receipt.',
    status: 'Active',
    icon: Activity,
    color: 'text-brand-400'
  },
  {
    id: 'srv_bal',
    name: 'Wallet Balance Retrieval',
    price: '0.2 USDC',
    deliverable: 'Text (Balance Amount)',
    description: 'Self-service: Retrieve your current virtual USDC wallet balance. Provides an immediate, verified snapshot of your accounting balance on LedgerOps.',
    status: 'Active',
    icon: Wallet,
    color: 'text-accent-400'
  },
  {
    id: 'srv_tax',
    name: 'Tax CSV Export',
    price: '0.2 USDC',
    deliverable: 'Text (Download URL)',
    description: 'Self-service: Generates a complete .csv file of all your transactions, returning a download URL. Perfect for tax reporting and accounting.',
    status: 'Active',
    icon: FileSpreadsheet,
    color: 'text-green-400'
  },
  {
    id: 'srv_verify',
    name: 'Receipt Verification',
    price: '0.2 USDC',
    deliverable: 'Text (Cryptographic Verification)',
    description: 'Self-service: Verify your most recent transaction receipt against the immutable LedgerOps ledger. Proves payment completion on-chain.',
    status: 'Active',
    icon: ShieldCheck,
    color: 'text-blue-400'
  },
  {
    id: 'srv_report',
    name: 'Analytics Report',
    price: '0.2 USDC',
    deliverable: 'Text (Summary Report)',
    description: 'Self-service: Get a summary of your total USDC spent and transaction count across all LedgerOps orders. Useful for auditing and accounting.',
    status: 'Active',
    icon: BarChart2,
    color: 'text-purple-400'
  },
];

const dueDiligenceTools = [
  {
    id: 'srv_trust',
    name: 'Trust Score Lookup',
    price: '0.2 USDC',
    deliverable: 'Schema (Trust Report JSON)',
    description: 'Counterparty due-diligence: Pull an independent trust/reputation report on any other CROO agent before hiring them. Returns completion rate, dispute rate, buyer diversity, account age, and a 0-100 trust score — the same anti-sybil signals CROO itself tracks.',
    status: 'Active',
    icon: Search,
    color: 'text-amber-400'
  },
];

const ServiceCard = ({ service, idx, baseDelay = 0 }) => (
  <div key={service.id} className="glass rounded-2xl border-t border-t-white/10 flex flex-col animate-fade-in-up" style={{ animationDelay: `${(idx + baseDelay) * 0.08}s` }}>
    <div className="p-6 border-b border-white/5 flex justify-between items-start">
      <div className="flex gap-4">
        <div className={`p-3 rounded-xl bg-surface-800 border border-white/5 ${service.color}`}>
          <service.icon size={24} />
        </div>
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight mb-1">{service.name}</h3>
          <p className="text-sm font-mono text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded inline-block">
            ID: {service.id}
          </p>
        </div>
      </div>
    </div>
    
    <div className="p-6 flex-1 flex flex-col gap-4">
      <p className="text-surface-300 text-sm leading-relaxed flex-1">
        {service.description}
      </p>
      
      <div className="bg-surface-800/50 rounded-xl p-4 border border-white/5 space-y-3">
        <div className="flex justify-between items-center text-sm">
          <span className="text-surface-400">Status</span>
          <span className={`font-bold uppercase tracking-widest px-3 py-1 rounded-full text-[10px] ${service.status === 'Active' ? 'bg-accent-500/20 text-accent-400' : 'bg-amber-500/20 text-amber-400'}`}>
            {service.status}
          </span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-surface-400">Price</span>
          <span className="font-semibold text-white">{service.price}</span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-surface-400">Deliverable</span>
          <span className="font-semibold text-white">{service.deliverable}</span>
        </div>
      </div>
    </div>
  </div>
);

export default function ServicesPanel() {
  return (
    <div className="space-y-10 pb-8">
      {/* Self-service section */}
      <div>
        <div className="flex items-center gap-3 mb-5">
          <span className="text-xs font-bold uppercase tracking-widest text-surface-400 px-3 py-1 rounded-full bg-surface-800 border border-white/10">Self-Service Tools</span>
          <div className="flex-1 h-px bg-white/5" />
          <span className="text-xs text-surface-500">Check your own status</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {selfServiceTools.map((service, idx) => (
            <ServiceCard key={service.id} service={service} idx={idx} />
          ))}
        </div>
      </div>

      {/* Counterparty due-diligence section */}
      <div>
        <div className="flex items-center gap-3 mb-5">
          <span className="text-xs font-bold uppercase tracking-widest text-amber-400 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">Counterparty Due-Diligence</span>
          <div className="flex-1 h-px bg-white/5" />
          <span className="text-xs text-surface-500">Check someone else's track record</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {dueDiligenceTools.map((service, idx) => (
            <ServiceCard key={service.id} service={service} idx={idx} baseDelay={selfServiceTools.length} />
          ))}
        </div>
      </div>
    </div>
  );
}
