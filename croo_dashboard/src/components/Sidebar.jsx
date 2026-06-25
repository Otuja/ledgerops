import React from 'react';
import { LayoutDashboard, Zap, FileText, Handshake, Briefcase, ShieldCheck } from 'lucide-react';

export default function Sidebar({ currentView, setCurrentView, isOpen, setIsOpen }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'services', label: 'Services', icon: Zap },
    { id: 'lookup', label: 'Agent Lookup', icon: ShieldCheck },
    { id: 'transactions', label: 'Transactions', icon: FileText },
    { id: 'negotiations', label: 'Negotiations', icon: Handshake },
    { id: 'wallets', label: 'Wallets', icon: Briefcase },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-20 md:hidden" 
          onClick={() => setIsOpen(false)}
        />
      )}
      
      <aside className={`w-64 bg-surface-900 border-r border-white/5 flex flex-col h-screen fixed inset-y-0 left-0 transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform duration-300 ease-in-out z-30`}>
        <div className="p-6">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="LedgerOps Logo" className="w-8 h-8 rounded-lg object-cover shadow-lg shadow-brand-500/20" />
            <h1 className="text-xl font-bold tracking-tight text-white">Ledger<span className="text-surface-400 font-normal">Ops</span></h1>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setCurrentView(item.id);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium ${
                currentView === item.id
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                  : 'text-surface-400 hover:bg-surface-800 hover:text-surface-100 border border-transparent'
              }`}
            >
              <item.icon size={20} className={currentView === item.id ? 'text-brand-400' : 'text-surface-400'} />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-6 border-t border-white/5">
          <div className="glass rounded-xl p-4 flex flex-col gap-2">
            <p className="text-xs uppercase tracking-wider text-surface-400 font-semibold">Network</p>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-500 animate-pulse-glow"></div>
              <span className="text-sm font-medium text-surface-200">Base Mainnet</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
