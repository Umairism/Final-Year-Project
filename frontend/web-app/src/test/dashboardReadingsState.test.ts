import { describe, expect, it } from 'vitest';
import { getDashboardReadingsState } from '@/lib/dashboardReadingsState';
describe('dashboard readings state machine',()=>{
 it.each([
  [{id:'r'},true,false,'ready'],[{id:'r'},false,true,'ready'],[undefined,true,false,'loading'],[undefined,false,true,'error'],[undefined,false,false,'empty'],[{id:'r'},false,false,'ready'],
 ])('maps state', (reading,loading,error,expected)=>expect(getDashboardReadingsState(reading,loading,error)).toBe(expected));
});
