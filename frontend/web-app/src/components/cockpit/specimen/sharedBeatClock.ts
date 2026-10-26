export class SharedBeatClock {
  readonly origin = performance.now();
  phase(bpm:number, now=performance.now()){return ((now-this.origin)*bpm/60000)%1;}
  elapsed(now=performance.now()){return (now-this.origin)/1000;}
}
