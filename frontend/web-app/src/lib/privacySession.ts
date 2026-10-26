export const PRIVACY_SEEN_KEY='healsense_privacy_seen';

export function getSessionStorage():Storage|undefined{try{return typeof window==='undefined'?undefined:window.sessionStorage;}catch{return undefined;}}
export function privacySeen(storage?:Storage|null){const target=arguments.length?storage:getSessionStorage();try{return Boolean(target?.getItem(PRIVACY_SEEN_KEY));}catch{return false;}}
export function markPrivacySeen(storage?:Storage|null){const target=arguments.length?storage:getSessionStorage();try{target?.setItem(PRIVACY_SEEN_KEY,'1');return Boolean(target);}catch{return false;}}
export function shouldShowPrivacy(pathname:string,isLoading:boolean,storage?:Storage|null){const target=arguments.length>=3?storage:getSessionStorage();return pathname==='/'&&!isLoading&&Boolean(target)&&!privacySeen(target);}

export function apiOrigin(baseUrl:string){try{return new URL(baseUrl).origin;}catch{return baseUrl.replace(/\/api\/v1\/?$/,'');}}
export function browserConnectionLabel(locationLike:Pick<Location,'protocol'|'hostname'>,secure=typeof window==='undefined'?false:window.isSecureContext){if(locationLike.protocol==='https:'||secure)return 'Secure browser context';if(locationLike.hostname==='localhost'||locationLike.hostname==='127.0.0.1'||locationLike.hostname==='[::1]')return 'Local development connection';return 'Unencrypted local connection — use only on a trusted network';}
