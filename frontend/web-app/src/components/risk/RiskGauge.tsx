import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface RiskGaugeProps {
  status: 'normal' | 'warning' | 'critical';
  score?: number;
  deterministicFlags?: string[];
  mlProbability?: number | null;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  status,
  score = 0.0,
  deterministicFlags = [],
  mlProbability,
}) => {
  const getBadgeClass = () => {
    switch (status) {
      case 'critical':
        return 'bg-destructive text-destructive-foreground';
      case 'warning':
        return 'bg-amber-500 text-white';
      case 'normal':
      default:
        return 'bg-emerald-500 text-white';
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold">Current Risk Assessment</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <Badge className={`text-sm px-3 py-1 uppercase font-bold ${getBadgeClass()}`}>
              {status}
            </Badge>
            <div className="mt-2 text-sm text-muted-foreground">
              Fused Risk Score: <span className="font-semibold text-foreground">{score.toFixed(2)}</span>
            </div>
          </div>
          {mlProbability != null && (
            <div className="text-right text-xs text-muted-foreground">
              <div>ML Probability</div>
              <div className="font-semibold text-foreground">{(mlProbability * 100).toFixed(1)}%</div>
            </div>
          )}
        </div>

        {deterministicFlags.length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Triggered Safety Rules:
            </span>
            <ul className="mt-1 space-y-1">
              {deterministicFlags.map((flag, idx) => (
                <li key={idx} className="text-xs text-rose-500 font-medium flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
