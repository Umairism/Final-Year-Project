const AUTH_TOKEN_KEY = 'healsense_auth_token';
export const getAccessToken = () => localStorage.getItem(AUTH_TOKEN_KEY);
export const setAccessToken = (token: string) => localStorage.setItem(AUTH_TOKEN_KEY, token);
export const clearAccessToken = () => localStorage.removeItem(AUTH_TOKEN_KEY);
export { AUTH_TOKEN_KEY };
