import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Sparkles } from 'lucide-react';
import { SafeMarkdown } from '@/lib/safeMarkdown';
import { getAiErrorMessage } from '@/lib/api';

export interface GeminiExplanationCardProps { explanation?: string | null; timestamp?: string | Date; loading?: boolean; error?: unknown; onRetry?: () => void; level?: string; confidence?: number; explainedAt?: string | Date; newerReading?: boolean; }
export const GeminiExplanationCard: React.FC<GeminiExplanationCardProps> = ({ explanation, timestamp, loading, error, onRetry, level, confidence, explainedAt, newerReading }) => (
  <Card className="border-indigo-500/20 bg-indigo-500/5">
    <CardHeader className="pb-2"><div className="flex items-center justify-between gap-2"><CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-5 w-5 text-indigo-500" />Decision Support Explanation</CardTitle><Button variant="ghost" size="sm" onClick={onRetry}><RefreshCw className="mr-1 h-3 w-3" />Refresh</Button></div></CardHeader>
    <CardContent className="space-y-3 text-sm">
      {loading && <p className="text-muted-foreground">Generating decision-support explanation...</p>}
      {error && !loading && <div className="rounded border border-destructive/30 p-2 text-destructive">{getAiErrorMessage(error)}<Button variant="link" onClick={onRetry}>Retry</Button></div>}
      {!loading && !error && explanation && <SafeMarkdown text={explanation} />}
      {!loading && !error && !explanation && <p className="text-muted-foreground">No explanation available yet.</p>}
      {(level || confidence != null) && <div className="flex flex-wrap gap-2"><Badge>Final risk: {level ?? 'unknown'}</Badge>{confidence != null && <Badge variant="outline">Confidence: {Math.round(confidence * 100)}%</Badge>}</div>}
      {explainedAt && <p className="text-xs text-muted-foreground">Based on reading: {new Date(explainedAt).toLocaleString()}</p>}
      {newerReading && <p className="text-xs text-amber-700">Newer reading available — refresh</p>}
    </CardContent>
  </Card>
);
