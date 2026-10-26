import { useEffect } from 'react';
export const useScopedDarkTheme = () => useEffect(() => { const root=document.documentElement; const had=root.classList.contains('dark'); root.classList.add('dark'); return () => { if(!had) root.classList.remove('dark'); }; }, []);
