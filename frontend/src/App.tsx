import React, { useState, useEffect } from 'react';
import { Topbar } from './components/Topbar';
import { Navigation, NavTab } from './components/Navigation';
import { RecoveryPlayground } from './components/RecoveryPlayground';
import { DashboardView } from './components/DashboardView';
import { Transactions } from './components/Transactions';
import { ApprovalQueue } from './components/ApprovalQueue';
import { AuditTrail } from './components/AuditTrail';
import { SimulationView } from './components/SimulationView';
import { SettingsView } from './components/SettingsView';
import { fetchHealth, fetchApprovals } from './services/api';
import { SystemStatus } from './types';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('playground');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const loadStatusAndApprovals = async () => {
    try {
      setLoadingHealth(true);
      setHealthError(null);
      const [healthData, approvalsData] = await Promise.allSettled([
        fetchHealth(),
        fetchApprovals()
      ]);

      if (healthData.status === 'fulfilled') {
        setSystemStatus(healthData.value);
      } else {
        throw new Error(healthData.reason?.message || 'Failed to connect to backend');
      }

      if (approvalsData.status === 'fulfilled') {
        setPendingApprovalsCount(approvalsData.value.length);
      }
    } catch (err: any) {
      setHealthError(err.message || 'Failed to connect to backend');
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    loadStatusAndApprovals();
  }, [activeTab]);

  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100">
      <Topbar 
        status={systemStatus} 
        loading={loadingHealth} 
        onRefresh={loadStatusAndApprovals} 
        onLogoClick={() => setActiveTab('playground')}
      />

      <div className="flex flex-1">
        <Navigation 
          activeTab={activeTab} 
          onSelectTab={setActiveTab} 
          pendingApprovalsCount={pendingApprovalsCount} 
        />

        <main className="flex-1 p-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
          {healthError && (
            <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 flex items-center gap-3 text-xs">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div>
                <p className="font-semibold">Backend Connection Error</p>
                <p className="text-red-400">{healthError} — Make sure FastAPI is running on port 8000.</p>
              </div>
            </div>
          )}

          {/* Tab Views */}
          {activeTab === 'playground' && <RecoveryPlayground />}
          {activeTab === 'dashboard' && <DashboardView />}
          {activeTab === 'transactions' && <Transactions />}
          {activeTab === 'approvals' && <ApprovalQueue />}
          {activeTab === 'audit' && <AuditTrail />}
          {activeTab === 'simulation' && <SimulationView />}
          {activeTab === 'settings' && (
            <SettingsView 
              status={systemStatus} 
              onRefresh={loadStatusAndApprovals} 
            />
          )}
        </main>
      </div>
    </div>
  );
};
