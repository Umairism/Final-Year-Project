import { ReactNode } from 'react';
import { VitalStatus } from '@/types/vitals';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface VitalCardProps {
  title: string;
  value: number | string;
  unit: string;
  status: VitalStatus;
  icon: ReactNode;
  trend?: 'up' | 'down' | 'stable';
  secondaryValue?: string;
  className?: string;
}

const statusStyles = {
  normal: {
    card: 'vital-card-normal',
    badge: 'status-badge-normal',
    indicator: 'bg-success',
    pulseClass: 'pulse-indicator-normal',
  },
  warning: {
    card: 'vital-card-warning',
    badge: 'status-badge-warning',
    indicator: 'bg-warning',
    pulseClass: 'pulse-indicator-warning',
  },
  critical: {
    card: 'vital-card-critical',
    badge: 'status-badge-critical',
    indicator: 'bg-destructive',
    pulseClass: 'pulse-indicator-critical',
  },
};

const statusLabels = {
  normal: 'Normal',
  warning: 'Warning',
  critical: 'Critical',
};

export const VitalCard = ({
  title,
  value,
  unit,
  status,
  icon,
  trend,
  secondaryValue,
  className,
}: VitalCardProps) => {
  const styles = statusStyles[status];

  return (
    <div
      className={cn(
        'vital-card animate-fade-in',
        styles.card,
        className
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('status-badge', styles.badge)}>
            <span
              className={cn(
                'w-2 h-2 rounded-full pulse-indicator',
                styles.indicator,
                styles.pulseClass
              )}
            />
            {statusLabels[status]}
          </span>
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-display font-bold tracking-tight">
              {value}
            </span>
            <span className="text-lg text-muted-foreground">{unit}</span>
          </div>
          {secondaryValue && (
            <span className="text-sm text-muted-foreground mt-1 block">
              {secondaryValue}
            </span>
          )}
        </div>

        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 text-sm',
              trend === 'up' && 'text-destructive',
              trend === 'down' && 'text-success',
              trend === 'stable' && 'text-muted-foreground'
            )}
          >
            {trend === 'up' && <TrendingUp className="w-4 h-4" />}
            {trend === 'down' && <TrendingDown className="w-4 h-4" />}
            {trend === 'stable' && <Minus className="w-4 h-4" />}
          </div>
        )}
      </div>
    </div>
  );
};
