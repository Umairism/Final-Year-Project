import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { useVitals, getVitalStatus } from '@/hooks/useVitals';
import { usePatient } from '@/hooks/usePatient';
import { deviceApi } from '@/lib/api';
import { API_CONFIG } from '@/lib/config';
import { VitalCard } from '@/components/VitalCard';
import { TrendChart } from '@/components/TrendChart';
import { AlertBanner } from '@/components/AlertBanner';
import { HistoryTable } from '@/components/HistoryTable';
import { PatientHeader } from '@/components/PatientHeader';
import { EmergencyButton } from '@/components/EmergencyButton';
import { SettingsDialog } from '@/components/SettingsDialog';
import { AlertsDialog } from '@/components/AlertsDialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Heart,
  Wind,
  Thermometer,
  Activity,
  Droplets,
  LayoutDashboard,
  LineChart,
  Clock,
  User,
  LogOut,
  Settings,
  Bell,
} from 'lucide-react';

import { HeartRateCard } from '@/components/vitals/HeartRateCard';
import { SpO2Card } from '@/components/vitals/SpO2Card';
import { TemperatureCard } from '@/components/vitals/TemperatureCard';
import { BloodPressureCard } from '@/components/vitals/BloodPressureCard';
import { BpEntryDialog } from '@/components/vitals/BpEntryDialog';
import { RiskGauge } from '@/components/risk/RiskGauge';
import { GeminiExplanationCard } from '@/components/risk/GeminiExplanationCard';
import { VitalTrendChart } from '@/components/vitals/VitalTrendChart';
import { formatAgeSeconds } from '@/lib/format';
import { useFusionRisk } from '@/hooks/useFusionRisk';
import { PatientAssistantPanel } from '@/components/ai/PatientAssistantPanel';
import { getDashboardReadingsState } from '@/lib/dashboardReadingsState';

export const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const PATIENT_ID = user?.patientId ?? '';

  const {
    currentReading,
    readings,
    alerts,
    isConnected,
    isRealtimeConnected,
    acknowledgeAlert,
    dismissAlert,
    isLoadingHistory,
    isHistoryError,
    refetchHistory,
  } = useVitals({ 
    patientId: PATIENT_ID, 
    useMockData: API_CONFIG.useMockData 
  });

  const { data: sourceData } = useQuery({
    queryKey: ['patient-device-sources', PATIENT_ID],
    queryFn: () => deviceApi.getPatientSources(PATIENT_ID),
    refetchInterval: 10000,
    enabled: Boolean(PATIENT_ID) && !API_CONFIG.useMockData,
  });

  const { data: patient, isLoading: isLoadingPatient } = usePatient(
    PATIENT_ID, 
    API_CONFIG.useMockData
  );

  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isBpEntryOpen, setIsBpEntryOpen] = useState(false);
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, []);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged);
  const overallConnected = API_CONFIG.useMockData ? isConnected : (isRealtimeConnected || isConnected);
  const connectionMode = API_CONFIG.useMockData
    ? 'Mock Stream'
    : (isRealtimeConnected ? 'WebSocket Live' : 'Polling Fallback');

  const fallbackActive = !API_CONFIG.useMockData && !isRealtimeConnected;
  const selectedSource = sourceData?.dataSources.find((src) => src.deviceId === sourceData.primarySource) ?? sourceData?.dataSources[0];
  const sourceDeviceId = selectedSource?.deviceId ?? 'No device registered';
  const presenceLabel = selectedSource?.presenceStatus === 'online' ? 'Online' : selectedSource?.presenceStatus === 'stale' ? 'Stale' : selectedSource?.presenceStatus === 'never_seen' ? 'Never seen' : selectedSource?.presenceStatus === 'disabled' ? 'Disabled' : 'Unknown';
  const lastSeenAge = selectedSource?.lastSeenSecondsAgo == null ? null : selectedSource.lastSeenSecondsAgo + Math.max(0, Math.floor((now - (sourceData?.fetchedAt ?? now))/1000));
  const hasDemo = API_CONFIG.useMockData || readings.some(r => r.dataOrigin === 'simulated' || r.dataOrigin === 'seed');
  const fusion = useFusionRisk(PATIENT_ID, currentReading, !API_CONFIG.useMockData);

  if (isLoadingPatient) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-muted-foreground">Loading vitals...</div>
      </div>
    );
  }
  if (!PATIENT_ID) return <div className="flex items-center justify-center min-h-screen"><div className="animate-pulse text-muted-foreground">Loading account...</div></div>;
  if (!patient) return <div className="p-8 text-destructive">Unable to load patient data.</div>;
  const readingsState = getDashboardReadingsState(currentReading, isLoadingHistory, isHistoryError);
  if (readingsState === 'loading') return <div className="flex items-center justify-center min-h-screen"><div className="animate-pulse text-muted-foreground">Loading readings...</div></div>;
  if (readingsState === 'error') return <div className="flex items-center justify-center min-h-screen"><div className="rounded-lg border border-destructive/40 bg-card p-6 space-y-4"><h2 className="text-xl font-semibold">Unable to load readings</h2><Button onClick={() => refetchHistory()}>Retry</Button></div></div>;
  if (readingsState === 'empty') return <div className="min-h-screen bg-background p-6"><div className="rounded-lg border bg-card p-4 flex flex-wrap gap-3"><Badge variant={overallConnected ? 'default' : 'secondary'}>Dashboard Link: {overallConnected ? 'Online' : 'Offline'}</Badge><Badge variant="outline">Source: {sourceDeviceId}</Badge><Badge variant="secondary">IoT Device: {presenceLabel}</Badge><Badge variant="outline">Last seen: {formatAgeSeconds(lastSeenAge)}</Badge></div><div className="mt-6 rounded-lg border bg-card p-8"><h2 className="text-xl font-semibold">No readings yet</h2><p className="text-muted-foreground">Connect an ESP32 device or log a manual BP reading.</p><Button className="mt-4" onClick={() => setIsBpEntryOpen(true)}>Log BP</Button></div><BpEntryDialog patientId={PATIENT_ID} open={isBpEntryOpen} onOpenChange={setIsBpEntryOpen} /></div>;

  const chartData = readings.map((r) => ({
    timestamp: new Date(r.timestamp).toLocaleTimeString(),
    heartRate: r.heartRate,
    spo2: r.spo2,
    temperature: r.temperature,
    riskScore: r.riskScore ?? 0,
  }));

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation Header */}
      <header className="border-b bg-card">
        <div className="container flex items-center justify-between h-16 px-4">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-600" />
            <span className="font-bold text-xl">HealSense</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-muted-foreground hidden md:block">
              {user?.name} • {user?.age} yrs • {user?.bloodType}
            </div>
            <Badge variant={overallConnected ? "default" : "destructive"}>
              {overallConnected ? "Connected" : "Disconnected"}
            </Badge>
            <Button variant="ghost" size="sm" onClick={() => navigate('/devices')}>
              Devices
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setIsAlertsOpen(true)}>
              <Bell className="h-5 w-5" />
              {unacknowledgedAlerts.length > 0 && (
                <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] text-white">
                  {unacknowledgedAlerts.length}
                </span>
              )}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => navigate('/profile')}>
              <User className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-6 space-y-6">
        <div className="rounded-lg border bg-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={overallConnected ? 'default' : 'destructive'}>
              Dashboard Link: {overallConnected ? 'Online' : 'Offline'}
            </Badge>
            <Badge variant={isRealtimeConnected ? 'default' : 'secondary'}>
              Mode: {API_CONFIG.useMockData ? 'Mock Data' : connectionMode}
            </Badge>
            <Badge variant={fallbackActive ? 'secondary' : 'outline'}>
              Fallback: {fallbackActive ? 'Active' : 'Inactive'}
            </Badge>
            <Badge variant={selectedSource?.isOnline === true ? 'default' : 'secondary'}>
              Source: {sourceDeviceId}
            </Badge>
            <Badge variant={selectedSource?.isOnline === true ? 'default' : 'secondary'}>
              IoT Device: {presenceLabel}
            </Badge>
            <Badge variant="outline">Last seen: {formatAgeSeconds(lastSeenAge)}</Badge>
            {currentReading && <Badge variant="outline">Last reading: {currentReading.timestamp.toLocaleTimeString()} ({formatAgeSeconds(Math.floor((now-currentReading.timestamp.getTime())/1000))})</Badge>}
          </div>
        </div>
        {hasDemo && <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-800">DEMO DATA — simulated or seeded readings are shown. These values are not being presented as live patient telemetry.</div>}

        {/* Alert Banner */}
        <AlertBanner
          alerts={alerts}
          onAcknowledge={acknowledgeAlert}
          onDismiss={dismissAlert}
        />

        {/* Risk Assessment & Decision Support Explanation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <RiskGauge
            status={currentReading.status ?? (currentReading.spo2 < 92 || currentReading.heartRate > 120 ? 'critical' : currentReading.spo2 < 95 || currentReading.heartRate > 100 ? 'warning' : 'normal')}
            score={currentReading.riskScore ?? (currentReading.spo2 < 92 ? 0.95 : currentReading.spo2 < 95 ? 0.65 : 0.12)}
            deterministicFlags={[
              ...(currentReading.systolic != null && currentReading.diastolic != null && (currentReading.systolic >= 180 || currentReading.diastolic >= 120)
                ? ['Hypertensive crisis (BP ≥ 180/120)'] : []),
              ...(currentReading.spo2 < 92 ? ['SpO2 < 92% (Hypoxia Risk)'] : []),
            ]}
            mlProbability={currentReading.predictionConfidence ?? null}
          />
          <GeminiExplanationCard
            explanation={fusion.data?.clinical_reasoning}
            timestamp={currentReading.timestamp}
            loading={fusion.isLoading}
            error={fusion.error}
            onRetry={() => fusion.refetch()}
            level={fusion.data?.fused_decision?.final_risk_level}
            confidence={fusion.data?.fused_decision?.confidence_score}
            explainedAt={fusion.data ? currentReading.timestamp : undefined}
            newerReading={false}
          />
        </div>

        <PatientAssistantPanel patientId={PATIENT_ID} latestReadingTimestamp={currentReading.timestamp} />

        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="dashboard" className="gap-2">
              <LayoutDashboard className="w-4 h-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="trends" className="gap-2">
              <LineChart className="w-4 h-4" />
              <span className="hidden sm:inline">Trends</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-2">
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6 animate-fade-in">
            {/* Vital Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <HeartRateCard
                heartRate={currentReading.heartRate}
                status={getVitalStatus('heartRate', currentReading.heartRate)}
                delayedSync={false}
              />
              <SpO2Card
                spo2={currentReading.spo2}
                status={getVitalStatus('spo2', currentReading.spo2)}
                delayedSync={false}
              />
              <TemperatureCard
                temperature={currentReading.temperature}
                status={getVitalStatus('temperature', currentReading.temperature)}
                delayedSync={false}
              />
              <BloodPressureCard
                systolic={currentReading.systolic}
                diastolic={currentReading.diastolic}
                bpSource={currentReading.bpSource ?? 'none'}
                status={getVitalStatus('systolic', currentReading.systolic)}
                delayedSync={currentReading.delayedSync ?? false}
                onLogBp={() => setIsBpEntryOpen(true)}
              />
            </div>

            {/* Vital Trend Chart */}
            <VitalTrendChart data={chartData} />
             {/* Quick Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TrendChart
                title="Heart Rate"
                data={readings}
                dataKey="heartRate"
                color="hsl(var(--chart-1))"
                unit="bpm"
                thresholds={{ warningMin: 50, warningMax: 100 }}
              />
              <TrendChart
                title="Blood Oxygen"
                data={readings}
                dataKey="spo2"
                color="hsl(var(--chart-2))"
                unit="%"
                thresholds={{ warningMin: 95 }}
              />
             </div>
           </TabsContent>

           <TabsContent value="trends" className="space-y-4 animate-fade-in">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TrendChart
                title="Heart Rate"
                data={readings}
                dataKey="heartRate"
                color="hsl(var(--chart-1))"
                unit="bpm"
                thresholds={{ warningMin: 50, warningMax: 100 }}
              />
              <TrendChart
                title="Blood Oxygen (SpO₂)"
                data={readings}
                dataKey="spo2"
                color="hsl(var(--chart-2))"
                unit="%"
                thresholds={{ warningMin: 95 }}
              />
              <TrendChart
                title="Temperature"
                data={readings}
                dataKey="temperature"
                color="hsl(var(--chart-3))"
                unit="°C"
                thresholds={{ warningMin: 36, warningMax: 37.5 }}
              />
              <TrendChart
                title="Systolic Blood Pressure"
                data={readings}
                dataKey="systolic"
                color="hsl(var(--chart-4))"
                unit="mmHg"
                thresholds={{ warningMin: 100, warningMax: 140 }}
              />
              <TrendChart
                title="Diastolic Blood Pressure"
                data={readings}
                dataKey="diastolic"
                color="hsl(var(--chart-5))"
                unit="mmHg"
                thresholds={{ warningMin: 60, warningMax: 90 }}
              />
              <TrendChart
                title="Respiratory Rate"
                data={readings}
                dataKey="respiratoryRate"
                color="hsl(var(--chart-1))"
                unit="/min"
                thresholds={{ warningMin: 12, warningMax: 20 }}
              />
            </div>
          </TabsContent>

          <TabsContent value="history" className="animate-fade-in">
            <HistoryTable readings={readings} />
          </TabsContent>
        </Tabs>
      </main>

      {/* Emergency Button */}
      <EmergencyButton patientId={PATIENT_ID} />

      {/* Dialogs */}
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
      <AlertsDialog
        open={isAlertsOpen}
        onOpenChange={setIsAlertsOpen}
        alerts={alerts}
        onAcknowledge={acknowledgeAlert}
        onDismiss={dismissAlert}
      />
      <BpEntryDialog patientId={PATIENT_ID} open={isBpEntryOpen} onOpenChange={setIsBpEntryOpen} />
    </div>
  );
};

export default Dashboard;
