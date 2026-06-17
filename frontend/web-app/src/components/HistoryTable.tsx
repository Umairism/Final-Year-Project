import { VitalReading } from '@/types/vitals';
import { getVitalStatus } from '@/hooks/useVitals';
import { format } from 'date-fns';
import { Download, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

interface HistoryTableProps {
  readings: VitalReading[];
}

const StatusCell = ({ status }: { status: 'normal' | 'warning' | 'critical' }) => {
  return (
    <span
      className={cn(
        'inline-block w-2 h-2 rounded-full',
        status === 'normal' && 'bg-success',
        status === 'warning' && 'bg-warning',
        status === 'critical' && 'bg-destructive'
      )}
    />
  );
};

export const HistoryTable = ({ readings }: HistoryTableProps) => {
  const sortedReadings = [...readings].reverse();

  const exportToCSV = () => {
    const headers = [
      'Timestamp',
      'Heart Rate',
      'SpO2',
      'Temperature',
      'Systolic',
      'Diastolic',
      'Respiratory Rate',
    ];

    const rows = sortedReadings.map((r) => [
      format(r.timestamp, 'yyyy-MM-dd HH:mm:ss'),
      r.heartRate,
      r.spo2,
      r.temperature,
      r.systolic,
      r.diastolic,
      r.respiratoryRate,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vitals-history-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-muted-foreground" />
          <h3 className="font-display font-semibold">Reading History</h3>
        </div>
        <Button variant="outline" size="sm" onClick={exportToCSV}>
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      <ScrollArea className="h-[400px]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Time</TableHead>
              <TableHead className="text-center">HR (bpm)</TableHead>
              <TableHead className="text-center">SpO₂ (%)</TableHead>
              <TableHead className="text-center">Temp (°C)</TableHead>
              <TableHead className="text-center">BP (mmHg)</TableHead>
              <TableHead className="text-center">RR (/min)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedReadings.map((reading) => (
              <TableRow key={reading.id} className="group">
                <TableCell className="font-mono text-sm">
                  {format(reading.timestamp, 'MMM dd, HH:mm:ss')}
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <StatusCell status={getVitalStatus('heartRate', reading.heartRate)} />
                    <span>{reading.heartRate}</span>
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <StatusCell status={getVitalStatus('spo2', reading.spo2)} />
                    <span>{reading.spo2}</span>
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <StatusCell status={getVitalStatus('temperature', reading.temperature)} />
                    <span>{reading.temperature}</span>
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <StatusCell status={getVitalStatus('systolic', reading.systolic)} />
                    <span>
                      {reading.systolic}/{reading.diastolic}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <StatusCell status={getVitalStatus('respiratoryRate', reading.respiratoryRate)} />
                    <span>{reading.respiratoryRate}</span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
};
