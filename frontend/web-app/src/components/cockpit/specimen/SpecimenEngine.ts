import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {buildSpecimen} from './geometryBuilders';
import {LayerMode,RenderMode,OrganFocus,SpecimenHandles,TelemetryViewModel} from './specimenTypes';
import {SPO2_PALETTE,spo2Band,pulseSpeedMultiplier,cardiacScale,breathScale,pinIsVisible} from './specimenDynamics';
import {SharedBeatClock} from './sharedBeatClock';

type PinElement=HTMLElement;
type FocusState={target:THREE.Vector3;radius:number};

export class SpecimenEngine {
  scene=new THREE.Scene();
  camera:THREE.PerspectiveCamera;
  renderer:THREE.WebGLRenderer;
  controls:OrbitControls;
  handles:SpecimenHandles;
  private raf=0;
  private visible=true;
  private telemetry:TelemetryViewModel={heartRate:72,spo2:98,temperature:36.7,respiratoryRate:14,status:'normal',isFresh:false,bpm:72,simulated:false,scenario:'live'};
  private readonly resizeObserver:ResizeObserver;
  private readonly beatClock:SharedBeatClock;
  private renderMode:RenderMode='hologram';
  private focusAnimating=false;
  private focus:FocusState={target:new THREE.Vector3(0,1.3,0),radius:5};
  private pinElements:Record<string,PinElement>={};

  constructor(private host:HTMLElement,beatClock=new SharedBeatClock()){
    this.beatClock=beatClock;
    this.scene.fog=new THREE.FogExp2(0xe8edf2,.035);
    this.camera=new THREE.PerspectiveCamera(45,1,.1,100);
    this.camera.position.set(0,1.3,5);
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});this.renderer.setClearColor(0xe8edf2,1);
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));
    host.appendChild(this.renderer.domElement);
    this.controls=new OrbitControls(this.camera,this.renderer.domElement);
    this.controls.enableDamping=true;this.controls.dampingFactor=.05;this.controls.target.set(0,1.3,0);
    this.controls.minDistance=1.8;this.controls.maxDistance=8.5;this.controls.autoRotate=true;this.controls.autoRotateSpeed=.6;
    this.controls.addEventListener('start',()=>{this.focusAnimating=false;this.controls.autoRotate=false;});
    this.scene.add(new THREE.AmbientLight(0x64748b,2.2));
    const cyan=new THREE.DirectionalLight(0x0f766e,1.8);cyan.position.set(4,5,4);this.scene.add(cyan);
    const rose=new THREE.DirectionalLight(0xbe123c,.9);rose.position.set(-4,-2,-3);this.scene.add(rose);
    this.handles=buildSpecimen();
    this.scene.add(this.handles.group,this.handles.group.userData.floor);
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(host);this.resize();this.loop();
  }

  private resize(){const width=this.host.clientWidth;const height=this.host.clientHeight||500;if(!width)return;this.camera.aspect=width/height;this.camera.updateProjectionMatrix();this.renderer.setSize(width,height,false);}
  setTelemetry(telemetry:TelemetryViewModel){this.telemetry=telemetry;this.applyTelemetryPalette();}
  setPinElements(elements:Record<string,PinElement>){this.pinElements=elements;}

  setLayer(layer:LayerMode){
    const selected={all:null,neural:this.handles.neural,cardio:this.handles.cardio,pulmo:this.handles.pulmonary,muscle:this.handles.muscular}[layer];
    this.handles.muscular.visible=true;
    this.handles.neural.visible=layer==='all'||layer==='neural';
    this.handles.cardio.visible=layer==='all'||layer==='cardio';
    this.handles.pulmonary.visible=layer==='all'||layer==='pulmo';
    if(layer!=='all'&&selected!==this.handles.muscular)this.setGroupOpacity(this.handles.muscular,.14);
    else this.setGroupOpacity(this.handles.muscular,1);
  }
  setAnatomicalLayer(layer:LayerMode){this.setLayer(layer);}

  private setGroupOpacity(group:THREE.Group,opacity:number){group.traverse(object=>{const mesh=object as THREE.Mesh;const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(material=>{if(material){material.transparent=opacity<1||material.transparent;material.opacity=opacity;}});});}
  private restoreMaterials(){this.handles.materials.forEach(material=>{const m=material as any;const original=m.userData.specimenOriginal;if(!original)return;if(original.color!=null)m.color.setHex(original.color);if(m.emissive&&original.emissive!=null)m.emissive.setHex(original.emissive);if(m.emissiveIntensity!=null&&original.emissiveIntensity!=null)m.emissiveIntensity=original.emissiveIntensity;m.opacity=original.opacity;m.transparent=original.transparent;m.wireframe=original.wireframe;});const pulse=this.handles.pulseParticles.material as THREE.PointsMaterial;pulse.size=.09;}
  private recolorGroup(group:THREE.Group,color:number){group.traverse(object=>{const mesh=object as THREE.Mesh;const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(material=>{const m=material as any;if(m?.color)m.color.setHex(color);});});}
  private applyTelemetryPalette(){this.restoreMaterials();const band=spo2Band(this.telemetry.spo2);const lungColor=this.telemetry.simulated&&this.telemetry.scenario==='hypoxia'?SPO2_PALETTE.indigo:SPO2_PALETTE[band];this.recolorGroup(this.handles.pulmonary,lungColor);if(this.telemetry.simulated&&this.telemetry.scenario==='hypoxia'){const material=this.handles.aorta.material as any;material.color?.setHex(SPO2_PALETTE.indigo);if(material.emissive)material.emissive.setHex(0x1e1b4b);}if(this.telemetry.simulated&&this.telemetry.scenario==='tachycardia'){this.recolorGroup(this.handles.heart,0xf43f5e);this.recolorGroup(this.handles.coronaries,0xfb7185);}}

  setRenderMode(mode:RenderMode){this.renderMode=mode;this.applyTelemetryPalette();this.handles.group.traverse(object=>{const mesh=object as THREE.Mesh;const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(material=>{const m=material as any;if(!m?.color)return;if(mode==='xray'){m.wireframe=true;m.color.set(0x38bdf8);m.opacity=.7;m.transparent=true;}else if(mode==='neural'){m.opacity=this.handles.neural.getObjectById(object.id)?1:.2;m.transparent=true;if(this.handles.neural.getObjectById(object.id))m.color.set(0xe879f9);}else if(mode==='thermal'){m.color.set(object===this.handles.leftVentricle?0xef4444:object===this.handles.leftLung||object===this.handles.rightLung?0x22d3ee:0xf59e0b);}});});if(mode==='neural')(this.handles.pulseParticles.material as THREE.PointsMaterial).size=.14;}

  focusOrgan(organ:OrganFocus){const targets={whole:new THREE.Vector3(0,1.3,0),heart:new THREE.Vector3(-.16,1.42,.25),brain:new THREE.Vector3(0,2.75,0),lungs:new THREE.Vector3(.1,1.45,.1)};const radii={whole:5,heart:2.4,brain:2.2,lungs:2.8};this.focus={target:targets[organ],radius:radii[organ]};this.focusAnimating=true;this.controls.autoRotate=false;}
  private updateFocus(){if(!this.focusAnimating)return;const direction=this.camera.position.clone().sub(this.controls.target).normalize();this.controls.target.lerp(this.focus.target,.08);this.camera.position.lerp(this.focus.target.clone().add(direction.multiplyScalar(this.focus.radius)),.08);if(this.controls.target.distanceTo(this.focus.target)<.01)this.focusAnimating=false;}

  updateOverlayTrackPins(){const rect=this.host.getBoundingClientRect();Object.entries(this.handles.pins).forEach(([key,anchor])=>{const element=this.pinElements[key];if(!element)return;const projected=anchor.clone().project(this.camera);const visible=pinIsVisible(projected,anchor,this.camera);element.style.opacity=visible?'1':'0';if(visible){element.style.left=`${(projected.x*.5+.5)*rect.width}px`;element.style.top=`${(-projected.y*.5+.5)*rect.height}px`;}});}
  animateMasterLoop(){this.loop();}

  private loop=()=>{if(!this.visible){this.raf=requestAnimationFrame(this.loop);return;}this.raf=requestAnimationFrame(this.loop);const now=performance.now();const elapsed=this.beatClock.elapsed(now);const t=this.telemetry;const phase=this.beatClock.phase(t.bpm,now);const active=t.simulated||t.isFresh;const beat=active&&cardiacScale(phase)>1;const scale=cardiacScale(phase,active);this.handles.heart.scale.set(scale,scale*1.05,scale);this.handles.coronaries.traverse(object=>{const material=(object as THREE.Mesh).material as any;if(material?.color)material.color.setHex(beat?0xff003d:0xff0044);});const breath=breathScale(elapsed,t.respiratoryRate,active);this.handles.leftLung.scale.set(.8*breath,1.45*breath,.9*breath);this.handles.rightLung.scale.set(.85*breath,1.5*breath,.95*breath);const positions=this.handles.pulseParticles.geometry.attributes.position.array as Float32Array;const curves=this.handles.pulseParticles.userData.curves as THREE.CatmullRomCurve3[];const progress=this.handles.pulseParticles.userData.progress as number[];if(active){const speed=pulseSpeedMultiplier(t.bpm,t.scenario);for(let i=0;i<curves.length;i++){progress[i]=(progress[i]+.016*speed)%1;const point=curves[i].getPoint(progress[i]);positions[i*3]=point.x;positions[i*3+1]=point.y;positions[i*3+2]=point.z;}this.handles.pulseParticles.geometry.attributes.position.needsUpdate=true;}this.updateFocus();this.controls.update();this.updateOverlayTrackPins();this.renderer.render(this.scene,this.camera);};

  dispose(){cancelAnimationFrame(this.raf);this.resizeObserver.disconnect();this.controls.dispose();this.handles.group.traverse(object=>{const mesh=object as THREE.Mesh;if(mesh.geometry)mesh.geometry.dispose();const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(material=>material?.dispose());});this.renderer.dispose();this.renderer.domElement.remove();}
}
