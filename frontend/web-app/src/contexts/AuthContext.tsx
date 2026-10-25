import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { API_CONFIG } from '@/lib/config';
import { authApi, getAuthErrorMessage, patientApi } from '@/lib/api';
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/authToken';

export interface EmergencyContact { name: string; phone: string; relation: string; type: 'doctor' | 'family' | 'other'; }
export interface User { id: string; email: string; name: string; patientId: string | null; isEmailVerified: boolean; age: number; gender: string; bloodType: string; medicalConditions: string[]; currentMedications: string[]; emergencyContacts: EmergencyContact[]; diabetes?: 'true'|'false'|'unknown'; smokingStatus?: 'non_smoker'|'former_smoker'|'current_smoker'|'unknown'; }
interface AuthContextType { user: User | null; isLoading: boolean; isAuthenticated: boolean; login: (email:string,password:string)=>Promise<{success:boolean;error?:string;code?:string}>; signup:(email:string,password:string,name:string,age:number,bloodType:string,gender?:string)=>Promise<{success:boolean;error?:string;verificationRequired?:boolean}>; resendVerification:(email:string)=>Promise<{success:boolean;error?:string}>; logout:()=>Promise<void>; updateProfile:(updates:Partial<User>)=>Promise<{success:boolean;error?:string}>; }
const AuthContext=createContext<AuthContextType|undefined>(undefined);
const LEGACY='healsense_mock_users';
const profileUser=(basic:any, profile:any):User=>({id:basic.id,email:basic.email,name:basic.full_name,patientId:basic.patient_id,isEmailVerified:basic.is_email_verified,age:profile?.age??0,gender:profile?.gender??'',bloodType:profile?.bloodType??'',medicalConditions:profile?.conditions??[],currentMedications:profile?.medications??[],emergencyContacts:profile?.emergencyContacts??[],diabetes:profile?.diabetes,smokingStatus:profile?.smokingStatus});
const basicUser=(u:any):User=>profileUser(u,null);

export const AuthProvider=({children}:{children:ReactNode})=>{
 const [user,setUser]=useState<User|null>(null); const [isLoading,setIsLoading]=useState(true);
 const hydrate=async(basic:any)=>{let profile=null; if(basic.patient_id){try{profile=await patientApi.getProfile(basic.patient_id);}catch{}} setUser(profileUser(basic,profile));};
 useEffect(()=>{(async()=>{localStorage.removeItem(LEGACY); const token=getAccessToken(); if(!token||token.trim().startsWith('{')){clearAccessToken();setIsLoading(false);return;} try{await hydrate(await authApi.me());}catch{clearAccessToken();setUser(null);} finally{setIsLoading(false);}})();},[]);
 const login=async(email:string,password:string)=>{if(API_CONFIG.useMockData)return {success:false,error:'Live backend mode is required for authentication.'}; try{const r=await authApi.login({email,password});setAccessToken(r.access_token);await hydrate(r.user);return {success:true};}catch(error:any){const code=error?.detail?.error;return {success:false,code,error:getAuthErrorMessage(error)};}};
 const signup=async(email:string,password:string,name:string,age:number,bloodType:string,gender='Unspecified')=>{if(API_CONFIG.useMockData)return {success:false,error:'Live backend mode is required for authentication.'};try{const r=await authApi.register({email,password,full_name:name,age,blood_type:bloodType||undefined,gender});return {success:true,verificationRequired:r.verification_required};}catch(error){return {success:false,error:getAuthErrorMessage(error)};}};
 const resendVerification=async(email:string)=>{try{await authApi.resendVerification(email);return {success:true};}catch(error){return {success:false,error:getAuthErrorMessage(error)};}};
 const logout=async()=>{clearAccessToken();localStorage.removeItem(LEGACY);setUser(null);};
 const updateProfile=async(updates:Partial<User>)=>{if(!user)return {success:false,error:'No user logged in'};setUser({...user,...updates});return {success:true};};
 return <AuthContext.Provider value={{user,isLoading,isAuthenticated:!!user,login,signup,resendVerification,logout,updateProfile}}>{children}</AuthContext.Provider>;
};
export const useAuth=()=>{const context=useContext(AuthContext);if(!context)throw new Error('useAuth must be used within an AuthProvider');return context;};
