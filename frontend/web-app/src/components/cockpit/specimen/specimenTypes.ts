import * as THREE from 'three';
export type LayerMode='all'|'neural'|'cardio'|'pulmo'|'muscle';
export type RenderMode='hologram'|'neural'|'xray'|'thermal';
export type OrganFocus='whole'|'heart'|'brain'|'lungs';
export type ScenarioName='live'|'stable'|'tachycardia'|'hypoxia';
export interface TelemetryViewModel{heartRate:number|null;spo2:number|null;temperature:number|null;respiratoryRate:number|null;status:string;isFresh:boolean;bpm:number;simulated:boolean;scenario:ScenarioName;}
export interface MaterialSnapshot{color:THREE.Color;emissive?:THREE.Color;emissiveIntensity?:number;opacity:number;transparent:boolean;wireframe:boolean;}
export interface SpecimenHandles{group:THREE.Group;muscular:THREE.Group;neural:THREE.Group;cardio:THREE.Group;pulmonary:THREE.Group;heart:THREE.Group;leftVentricle:THREE.Mesh;leftLung:THREE.Mesh;rightLung:THREE.Mesh;coronaries:THREE.Group;pulseParticles:THREE.Points;materials:THREE.Material[];pins:Record<string,THREE.Vector3>;}
