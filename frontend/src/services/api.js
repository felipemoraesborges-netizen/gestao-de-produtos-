const API_BASE = '/api';

// Token Management
export function getAccessToken() {
  return localStorage.getItem('gestao_access_token');
}

export function getRefreshToken() {
  return localStorage.getItem('gestao_refresh_token');
}

export function setTokens(accessToken, refreshToken) {
  if (accessToken) localStorage.setItem('gestao_access_token', accessToken);
  if (refreshToken) localStorage.setItem('gestao_refresh_token', refreshToken);
}

export function clearTokens() {
  localStorage.removeItem('gestao_access_token');
  localStorage.removeItem('gestao_refresh_token');
  localStorage.removeItem('gestao_user');
}

// Authenticated fetch wrapper with automatic JWT header & refresh token logic
export async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let res = await fetch(url, { ...options, headers });

  // Handle Token Expiration (401) with Refresh Token
  if (res.status === 401) {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setTokens(refreshData.access_token, refreshData.refresh_token);

          // Retry original request with newly refreshed token
          const retryHeaders = new Headers(options.headers || {});
          retryHeaders.set('Authorization', `Bearer ${refreshData.access_token}`);
          res = await fetch(url, { ...options, headers: retryHeaders });
        } else {
          clearTokens();
          window.dispatchEvent(new CustomEvent('auth:expired'));
        }
      } catch (err) {
        clearTokens();
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
    } else {
      clearTokens();
      window.dispatchEvent(new CustomEvent('auth:expired'));
    }
  }

  return res;
}

// ==========================================
// AUTENTICAÇÃO & USUÁRIO
// ==========================================
export async function loginUser(identificador, senha) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identificador, senha }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Usuário ou senha inválidos.');
  
  if (data.access_token) {
    setTokens(data.access_token, data.refresh_token);
  }
  return data.user;
}

export async function logoutUser() {
  try {
    await authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
  } catch (e) {
    console.warn('Erro durante logout:', e);
  } finally {
    clearTokens();
  }
}

export async function registerUser(userData) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let errorMsg = 'Erro ao criar conta';
    if (typeof data.detail === 'string') {
      errorMsg = data.detail;
    } else if (Array.isArray(data.detail)) {
      errorMsg = data.detail.map((err) => {
        const field = err.loc ? err.loc[err.loc.length - 1] : '';
        if (field === 'usuario') return 'Usuário inválido: use apenas letras (sem acentos), números, ponto, traço ou underline';
        if (field === 'senha') return 'A senha deve ter no mínimo 10 caracteres';
        if (field === 'email') return 'Formato de e-mail inválido';
        return err.msg || 'Campo inválido';
      }).join('. ');
    } else if (data.message) {
      errorMsg = data.message;
    }
    throw new Error(errorMsg);
  }
  return data;
}

export async function getUserProfile(userId) {
  // Uses /api/auth/me which authenticates strictly via JWT token
  const res = await authFetch(`${API_BASE}/auth/me`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao buscar perfil');
  return data.user;
}

export async function updateUserProfile(profileData) {
  const res = await authFetch(`${API_BASE}/auth/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profileData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao atualizar perfil');
  return data;
}

export async function changeUserPassword(passwordData) {
  const res = await authFetch(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(passwordData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao alterar senha');
  return data;
}

// ==========================================
// IMPORTAÇÃO NF-E & PRECIFICAÇÃO
// ==========================================
export async function uploadXmlFiles(files, userId, selectedTaxes) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  formData.append('impostos_selecionados', JSON.stringify(selectedTaxes));

  const res = await authFetch(`${API_BASE}/nfe/upload`, {
    method: 'POST',
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao processar arquivos XML');
  return data;
}

export async function calculateMetrics(calculationData) {
  const res = await authFetch(`${API_BASE}/nfe/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(calculationData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao calcular métricas');
  return data;
}

export async function getInvoiceHistory(userId) {
  const res = await authFetch(`${API_BASE}/nfe/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar histórico');
  return data.notas;
}

export async function downloadCalculatedCsv(produtos) {
  const res = await authFetch(`${API_BASE}/nfe/export-csv`, {
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

// ==========================================
// SERVIÇOS DE GESTÃO DE ESTOQUE
// ==========================================
export async function getEstoque(userId, statusFiltro = 'todos', busca = '') {
  let url = `${API_BASE}/estoque?`;
  if (statusFiltro && statusFiltro !== 'todos') url += `status_filtro=${encodeURIComponent(statusFiltro)}&`;
  if (busca) url += `busca=${encodeURIComponent(busca)}&`;

  const res = await authFetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar catálogo de estoque');
  return data;
}

export async function saveEstoqueItem(itemData) {
  const res = await authFetch(`${API_BASE}/estoque/item`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(itemData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao salvar produto no estoque');
  return data;
}

export async function deleteEstoqueItem(produtoId, userId, userName) {
  const url = `${API_BASE}/estoque/${produtoId}`;
  const res = await authFetch(url, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao excluir item do estoque');
  return data;
}

export async function movimentarEstoque(movData) {
  const res = await authFetch(`${API_BASE}/estoque/movimentar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(movData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao registrar movimentação de estoque');
  return data;
}

export async function incorporarNfeAoEstoque(payload) {
  const res = await authFetch(`${API_BASE}/estoque/incorporar-nfe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao incorporar produtos ao estoque');
  return data;
}

export async function getMovimentacoesEstoque(userId, produtoId = null, limit = 50) {
  let url = `${API_BASE}/estoque/movimentacoes?limit=${limit}&`;
  if (produtoId) url += `produto_id=${produtoId}&`;

  const res = await authFetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar movimentações');
  return data.movimentacoes;
}

// ==========================================
// SERVIÇOS DE PAINÉIS & RELATÓRIOS
// ==========================================
export async function getDesempenhoRelatorio(userId) {
  const res = await authFetch(`${API_BASE}/relatorios/desempenho`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar relatório de desempenho');
  return data;
}

export async function downloadReposicaoCsv(userId) {
  const res = await authFetch(`${API_BASE}/relatorios/reposicao-csv`);
  if (!res.ok) throw new Error('Erro ao exportar relatório de reposição');
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `reposicao_compras_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

// ==========================================
// SERVIÇOS DE TRILHA DE AUDITORIA
// ==========================================
export async function getAuditoriaLogs(userId, acao = 'TODAS', termo = '', limit = 100, offset = 0) {
  let url = `${API_BASE}/auditoria?limit=${limit}&offset=${offset}&`;
  if (acao && acao !== 'TODAS') url += `acao=${encodeURIComponent(acao)}&`;
  if (termo) url += `termo=${encodeURIComponent(termo)}&`;

  const res = await authFetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro ao carregar logs de auditoria');
  return data;
}

export async function logAuditoriaFrontend(eventData) {
  try {
    await authFetch(`${API_BASE}/auditoria/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(eventData),
    });
  } catch (e) {
    console.warn('Falha ao registrar log de auditoria frontend:', e);
  }
}

export async function downloadAuditoriaCsv(userId, acao = 'TODAS', termo = '') {
  let url = `${API_BASE}/auditoria/export-csv?`;
  if (acao && acao !== 'TODAS') url += `acao=${encodeURIComponent(acao)}&`;
  if (termo) url += `termo=${encodeURIComponent(termo)}&`;

  const res = await authFetch(url);
  if (!res.ok) throw new Error('Erro ao exportar trilha de auditoria');
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `auditoria_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}
