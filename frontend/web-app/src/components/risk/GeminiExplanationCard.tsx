import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, Sparkles } from 'lucide-react';

interface GeminiExplanationCardProps {
  explanation?: string | null;
  timestamp?: string | Date;
}

export const GeminiExplanationCard: React.FC<GeminiExplanationCardProps> = ({
  explanation,
  timestamp,
}) => {
  if (!explanation) return null;

  return (
    <Card className="border-indigo-500/20 bg-indigo-500/5">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-500" />
          <CardTitle className="text-base font-semibold text-indigo-950 dark:text-indigo-200">
            Decision Support Explanation
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          {explanation}
        </p>
        {timestamp && (
          <div className="mt-3 text-xs text-muted-foreground">
            Generated at: {new Date(timestamp).toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
