import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const viveka = {
  globalShap: () => api.get('/viveka/global-shap'),
  explain: (id) => api.get(`/viveka/explain/${id}`),
  fairnessAudit: () => api.get('/viveka/fairness-audit'),
  explainCustom: (features) => api.post('/viveka/explain-custom', { features }),
};

export const raksha = {
  inventory: () => api.get('/raksha/inventory'),
  modelDetail: (id) => api.get(`/raksha/inventory/${id}`),
  tierScore: (data) => api.post('/raksha/tier-score', data),
  complianceScorecard: () => api.get('/raksha/compliance-scorecard'),
  validationQueue: () => api.get('/raksha/validation-queue'),
  updateStatus: (id, data) => api.put(`/raksha/inventory/${id}/status`, data),
  boardSummary: () => api.get('/raksha/board-summary'),
};

export const satya = {
  portfolio: (params) => api.get('/satya/portfolio', { params }),
  borrower: (id) => api.get(`/satya/borrower/${id}`),
  psiMonitor: () => api.get('/satya/psi-monitor'),
  heatmap: () => api.get('/satya/heatmap'),
  alerts: () => api.get('/satya/alerts'),
  portfolioSummary: () => api.get('/satya/portfolio-summary'),
};

export default api;
