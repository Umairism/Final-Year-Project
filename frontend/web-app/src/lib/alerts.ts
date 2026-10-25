import { Alert } from '@/types/vitals';

export type AlertActions = Map<string, { acknowledged?: boolean; dismissed?: boolean }>;

// Acknowledgement/dismissal are monotonic. Confirmed actions also protect against
// an older in-flight poll arriving after the HTTP response or WebSocket event.
export const visibleAlerts = (alerts: Alert[], actions: AlertActions): Alert[] => {
  const unique = new Map<string, Alert>();
  for (const alert of alerts) {
    const confirmed = actions.get(alert.id);
    const merged = {
      ...alert,
      acknowledged: alert.acknowledged || Boolean(confirmed?.acknowledged),
      dismissed: alert.dismissed || Boolean(confirmed?.dismissed),
    };
    if (merged.dismissed) {
      actions.set(alert.id, { ...confirmed, dismissed: true });
      unique.delete(alert.id);
    } else {
      if (merged.acknowledged) actions.set(alert.id, { ...confirmed, acknowledged: true });
      unique.set(alert.id, merged);
    }
  }
  return [...unique.values()];
};
