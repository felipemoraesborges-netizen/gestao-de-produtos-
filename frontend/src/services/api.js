const API_BASE = '/api';

const fetchWithSession = (url, options = {}) => fetch(url, { ...options, credentials: 'include' });

export async function loginUser(identificador, senha) {
  const res = await fetchWithSession(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identificador, senha }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao realizar login');
  return data.user;
}

export async function registerUser(userData) {
  const res = await fetchWithSession(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao criar conta');
  return data;
}

export async function getUserProfile(_userId) {
  const res = await fetchWithSession(`${API_BASE}/auth/me`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao buscar perfil');
  return data.user;
}

export async function updateUserProfile(profileData) {
  const res = await fetchWithSession(`${API_BASE}/auth/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profileData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao atualizar perfil');
  return data;
}

export async function changeUserPassword(passwordData) {
  const res = await fetchWithSession(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(passwordData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao alterar senha');
  return data;
}

export async function uploadXmlFiles(files, userId, selectedTaxes) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  if (userId) {
    formData.append('usuario_id', userId);
  }
  formData.append('impostos_selecionados', JSON.stringify(selectedTaxes));

  const res = await fetchWithSession(`${API_BASE}/nfe/upload`, {
    method: 'POST',
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao processar arquivos XML');
  return data;
}

export async function calculateMetrics(calculationData) {
  const res = await fetchWithSession(`${API_BASE}/nfe/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(calculationData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao calcular métricas');
  return data;
}

export async function getInvoiceHistory(_userId) {
  const url = `${API_BASE}/nfe/history`;
  const res = await fetchWithSession(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar histórico');
  return data.notas;
}

export async function downloadCalculatedCsv(produtos) {
  const res = await fetchWithSession(`${API_BASE}/nfe/export-csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(produtos),
  });
  if (!res.ok) throw new Error('Erro ao exportar planilha CSV');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `precificacao_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadCalculatedExcel(produtos) {
  const res = await fetchWithSession(`${API_BASE}/nfe/export-excel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(produtos),
  });
  if (!res.ok) throw new Error('Erro ao exportar planilha Excel');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `precificacao_${new Date().toISOString().slice(0, 10)}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function logoutUser() {
  const res = await fetchWithSession(`${API_BASE}/auth/logout`, { method: 'POST' });
  if (!res.ok) throw new Error('Erro ao encerrar a sess?o');
}
