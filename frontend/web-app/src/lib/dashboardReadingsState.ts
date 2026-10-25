export type DashboardReadingsState = 'loading' | 'error' | 'empty' | 'ready';
export const getDashboardReadingsState = (currentReading: unknown, isLoadingHistory: boolean, isHistoryError: boolean): DashboardReadingsState => {
  if (currentReading) return 'ready';
  if (isLoadingHistory) return 'loading';
  if (isHistoryError) return 'error';
  return 'empty';
};
