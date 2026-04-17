import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

const JWT_STORAGE_KEY = "vf_ff_jwt";

export function getStoredToken(): string | null {
  return localStorage.getItem(JWT_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token === null) {
    localStorage.removeItem(JWT_STORAGE_KEY);
  } else {
    localStorage.setItem(JWT_STORAGE_KEY, token);
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      setStoredToken(null);
    }
    return Promise.reject(error);
  }
);
