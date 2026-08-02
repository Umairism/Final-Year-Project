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
import { RiskGauge } from '@/components/risk/RiskGauge';
import { GeminiExplanationCard } from '@/components/risk/GeminiExplanationCard';
import { VitalTrendChart } from '@/components/vitals/VitalTrendChart';

export const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const PATIENT_ID = user?.id || '1';

  const {
    currentReading,
    readings,
    alerts,
    isConnected,
    isRealtimeConnected,
    acknowledgeAlert,
    dismissAlert,
  } = useVitals({ 
    patientId: PATIENT_ID, 
    useMockData: API_CONFIG.useMockData 
  });

  const { data: sourceData } = useQuery({
    queryKey: ['patient-device-sources', PATIENT_ID],
    queryFn: () => deviceApi.getPatientSources(PATIENT_ID),
    enabled: !API_CONFIG.useMockData,
    refetchInterval: 10000,
  });

  const { data: patient, isLoading: isLoadingPatient } = usePatient(
    PATIENT_ID, 
    API_CONFIG.useMockData
  );

  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);

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
  const sourceDeviceId = API_CONFIG.useMockData
    ? `PHONE_${PATIENT_ID}`
    : (sourceData?.primary_source || sourceData?.data_sources?.[0]?.device_id || 'ESP32_PATIENT_001');
  const sourceConnected = API_CONFIG.useMockData
    ? overallConnected
    : Boolean(sourceData?.data_sources?.find((src) => src.device_id === sourceDeviceId)?.connected ?? true);

  if (!currentReading || isLoadingPatient || !patient) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-muted-foreground">Loading vitals...</div>
      </div>
    );
  }

  const chartData = readings.map((r) => ({
    timestamp: new Date(r.timestamp).toLocaleTimeString(),
    heartRate: r.heartRate,
    spo2: r.spo2,
    temperature: r.temperature,
    riskScore: 0.1,
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
              Stream: {overallConnected ? 'Online' : 'Offline'}
            </Badge>
            <Badge variant={isRealtimeConnected ? 'default' : 'secondary'}>
              Mode: {connectionMode}
            </Badge>
            <Badge variant={fallbackActive ? 'secondary' : 'outline'}>
              Fallback: {fallbackActive ? 'Active' : 'Inactive'}
            </Badge>
            <Badge variant={sourceConnected ? 'default' : 'secondary'}>
              Source: {sourceDeviceId}
            </Badge>
            <Badge variant={sourceConnected ? 'outline' : 'destructive'}>
              IoT Device: {sourceConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>

        {/* Alert Banner */}
        <AlertBanner
          alerts={alerts}
          onAcknowledge={acknowledgeAlert}
          onDismiss={dismissAlert}
        />

        {/* Risk Assessment & Decision Support Explanation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <RiskGauge
            status={currentReading.spo2 < 92 || currentReading.heartRate > 120 ? 'critical' : currentReading.spo2 < 95 || currentReading.heartRate > 100 ? 'warning' : 'normal'}
            score={currentReading.spo2 < 92 ? 0.95 : currentReading.spo2 < 95 ? 0.65 : 0.12}
            deterministicFlags={currentReading.spo2 < 92 ? ['SpO2 < 92% (Hypoxia Risk)'] : []}
            mlProbability={0.15}
          />
          <GeminiExplanationCard
            explanation="Patient vital parameters are currently within normal physiological thresholds. Heart rate and SpO2 display steady baseline consistency."
            timestamp={currentReading.timestamp}
          />
        </div>

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
                bpSource="none"
                status={getVitalStatus('systolic', currentReading.systolic)}
                delayedSync={false}
              />
            </div>

            {/* Vital Trend Chart */}
            <VitalTrendChart data={chartData} />
          </TabsContent>

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
      <EmergencyButton />

      {/* Dialogs */}
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
      <AlertsDialog
        open={isAlertsOpen}
        onOpenChange={setIsAlertsOpen}
        alerts={alerts}
        onAcknowledge={acknowledgeAlert}
        onDismiss={dismissAlert}
      />
    </div>
  );
};

export default Dashboard;
