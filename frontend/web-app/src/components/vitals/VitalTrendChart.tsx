import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface VitalTrendChartProps {
  data: Array<{
    timestamp: string;
    heartRate: number;
    spo2: number;
    temperature: number;
    riskScore?: number;
  }>;
}

export const VitalTrendChart: React.FC<VitalTrendChartProps> = ({ data }) => {
  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="text-base font-semibold">Physiological Trend History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="timestamp" stroke="#888888" fontSize={12} />
              <YAxis yAxisId="left" stroke="#888888" fontSize={12} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 1]} stroke="#888888" fontSize={12} />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="heartRate"
                name="Heart Rate (BPM)"
                stroke="#f43f5e"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="spo2"
                name="SpO₂ (%)"
                stroke="#0ea5e9"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="temperature"
                name="Temp (°C)"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="riskScore"
                name="Risk Score"
                stroke="#8b5cf6"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
