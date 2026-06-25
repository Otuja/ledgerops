import React, { useState, useEffect } from 'react';
import { fetchHealth } from '../lib/api';

export default function HealthBadge() {
  const [isHealthy, setIsHealthy] = useState(true);

  useEffect(() => {
    let isMounted = true;
    
    const checkHealth = async () => {
      const ok = await fetchHealth();
      if (isMounted) setIsHealthy(ok);
      setTimeout(checkHealth, 5000); // Check every 5s
    };
    
    checkHealth();
    return () => { isMounted = false; };
  }, []);

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${
      isHealthy 
        ? 'bg-accent-500/10 border-accent-500/20 text-accent-400' 
        : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
    }`}>
      <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-accent-500 animate-pulse-glow' : 'bg-rose-500'}`}></div>
      <span className="text-xs font-semibold uppercase tracking-wider">
        {isHealthy ? 'System Online' : 'Offline'}
      </span>
    </div>
  );
}
