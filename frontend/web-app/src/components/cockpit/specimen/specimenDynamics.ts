import * as THREE from 'three';
import {ScenarioName} from './specimenTypes';

export const SPO2_PALETTE={cyan:0x06b6d4,amber:0xf59e0b,rose:0xfb7185,indigo:0x312e81};
export const spo2Band=(spo2:number|null)=>spo2==null?'cyan':spo2>=95?'cyan':spo2>=92?'amber':'rose';
export const pulseSpeedMultiplier=(bpm:number,scenario:ScenarioName)=>Math.min(2.2,Math.max(.6,.45+bpm/140)*(scenario==='tachycardia'||scenario==='hypoxia'?1.35:1));
export const isCardiacContractionPhase=(phase:number)=>phase>=.31&&phase<=.42;
export const cardiacScale=(phase:number,active=true)=>active&&isCardiacContractionPhase(phase)?1.22:1;
export const breathScale=(elapsed:number,respiratoryRate:number|null,active=true)=>{if(!active)return 1;if(respiratoryRate==null)return 1+Math.sin(elapsed*.35)*.02;return 1+Math.sin(elapsed*respiratoryRate/60*Math.PI*2)*.12;};
export const pinIsVisible=(projected:THREE.Vector3,anchor:THREE.Vector3,camera:THREE.Camera)=>{if(projected.z>1)return false;const direction=anchor.clone().sub(camera.position).normalize();const facing=direction.dot(camera.getWorldDirection(new THREE.Vector3()))>0;return facing;};
