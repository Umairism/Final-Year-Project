import { VitalReading, VitalStatus } from '@/types/vitals';
import { getVitalStatus } from '@/hooks/useVitals';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { format } from 'date-fns';

interface TrendChartProps {
  title: string;
  data: VitalReading[];
  dataKey: keyof VitalReading;
  color: string;
  unit: string;
  thresholds?: {
    warningMin?: number;
    warningMax?: number;
    criticalMin?: number;
    criticalMax?: number;
  };
}

export const TrendChart = ({
  title,
  data,
  dataKey,
  color,
  unit,
  thresholds,
}: TrendChartProps) => {
  const chartData = data.map((reading) => ({
    time: format(reading.timestamp, 'HH:mm'),
    value: reading[dataKey],
    timestamp: reading.timestamp,
  }));

  const currentValue = chartData[chartData.length - 1]?.value;
  const status = currentValue 
    ? getVitalStatus(dataKey as any, currentValue as number) 
    : 'normal';

  const getStatusColor = (s: VitalStatus) => {
    switch (s) {
      case 'critical': return 'hsl(var(--vital-critical))';
      case 'warning': return 'hsl(var(--vital-warning))';
      default: return color;
    }
  };

  return (
    <div className="chart-container">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold text-foreground">{title}</h3>
        <div className="flex items-baseline gap-1">
          <span 
            className="text-2xl font-display font-bold"
            style={{ color: getStatusColor(status) }}
          >
            {String(currentValue)}
          </span>
          <span className="text-sm text-muted-foreground">{unit}</span>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="hsl(var(--border))" 
              vertical={false}
            />
            <XAxis
              dataKey="time"
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={35}
              domain={['dataMin - 5', 'dataMax + 5']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-md)',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
              formatter={(value: number) => [`${value} ${unit}`, title] as [string, string]}
            />
            {thresholds?.warningMax && (
              <ReferenceLine
                y={thresholds.warningMax}
                stroke="hsl(var(--vital-warning))"
                strokeDasharray="5 5"
                strokeOpacity={0.5}
              />
            )}
            {thresholds?.warningMin && (
              <ReferenceLine
                y={thresholds.warningMin}
                stroke="hsl(var(--vital-warning))"
                strokeDasharray="5 5"
                strokeOpacity={0.5}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                fill: color,
                stroke: 'hsl(var(--background))',
                strokeWidth: 2,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
