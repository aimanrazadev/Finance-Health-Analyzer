import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export const getAuthHeaders = (token) => ({
  Authorization: `Bearer ${token}`,
});

export default api;
