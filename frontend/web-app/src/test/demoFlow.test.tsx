import {describe,expect,it,vi} from 'vitest';
import {cockpitSearchParams,parseCockpitQuery} from '@/lib/demoFlow';

describe('clinical demo flow',()=>{
  it('parses valid and ignores invalid cockpit parameters',()=>{expect(parseCockpitQuery('?mode=simulation&scenario=hypoxia')).toEqual({mode:'simulation',scenario:'hypoxia'});expect(parseCockpitQuery('?mode=simulation&scenario=unknown')).toEqual({mode:'simulation',scenario:'stable'});expect(parseCockpitQuery('?mode=invalid&scenario=hypoxia')).toEqual({mode:'live'});expect(cockpitSearchParams({mode:'live'})).toEqual({mode:'live'});expect(cockpitSearchParams({mode:'simulation',scenario:'hypoxia'})).toEqual({mode:'simulation',scenario:'hypoxia'});});
});
