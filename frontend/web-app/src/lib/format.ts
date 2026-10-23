export const formatInt = (value: number | null | undefined) => value == null || Number.isNaN(value) ? '—' : String(Math.round(value));
export const formatFixed = (value: number | null | undefined, digits: number) => value == null || Number.isNaN(value) ? '—' : value.toFixed(digits);
export const formatAgeSeconds = (seconds: number | null | undefined) => { if (seconds == null) return 'never'; const s=Math.max(0,Math.round(seconds)); const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), r=s%60; return h ? `${h}h ${m}m ago` : m ? `${m}m ago` : `${r}s ago`; };
