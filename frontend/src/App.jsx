import React, { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import Navbar from './components/Navbar';
import MetricCards from './components/MetricCards';
import FileUpload from './components/FileUpload';
import ConfigPanel from './components/ConfigPanel';
import ProductTable from './components/ProductTable';
import ChartsSection from './components/ChartsSection';
import Toast from './components/Toast';

import AuthPage from './pages/AuthPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';

import {
  getUserProfile,
  updateUserProfile,
  uploadXmlFiles,
  calculateMetrics,
  downloadCalculatedCsv,
  downloadCalculatedExcel,
} from './services/api';

export default function App() {
  // 1. Authentication State
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('gestao_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // 2. Navigation State
  const [activeTab, setActiveTab] = useState('pricing');
  const [toast, setToast] = useState(null);

  // 3. Pricing & Product State
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSavingDefault, setIsSavingDefault] = useState(false);

  const [markup, setMarkup] = useState(60.0);
  const [custoAdicional, setCustoAdicional] = useState(0.0);
  const [selectedTaxes, setSelectedTaxes] = useState(['ICMS ST', 'FCP ST', 'IPI', 'II']);
  const [unidadesPorEmbalagem, setUnidadesPorEmbalagem] = useState({});

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  // Sync user defaults when user logs in or profile changes
  useEffect(() => {
    if (user) {
      if (user.markup_padrao !== undefined) setMarkup(Number(user.markup_padrao));
      if (user.custo_adicional_padrao !== undefined) setCustoAdicional(Number(user.custo_adicional_padrao));
      if (user.impostos_padrao && Array.isArray(user.impostos_padrao)) setSelectedTaxes(user.impostos_padrao);
      localStorage.setItem('gestao_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('gestao_user');
    }
  }, [user]);

  // Recalculate metrics when parameters or packaging change
  const runRecalculate = useCallback(async () => {
    if (produtos.length === 0) return;
    try {
      const calcResult = await calculateMetrics({
        produtos,
        markup,
        custo_adicional_unitario: custoAdicional,
        impostos_selecionados: selectedTaxes,
        unidades_por_embalagem: unidadesPorEmbalagem,
      });
      setProdutos(calcResult.produtos);
      setResumo(calcResult.resumo);
    } catch (err) {
      console.error('Erro ao recalcular:', err);
    }
  }, [produtos, markup, custoAdicional, selectedTaxes, unidadesPorEmbalagem]);

  // Debounced live calculation when inputs change
  const calcTimeoutRef = useRef(null);
  useEffect(() => {
    if (produtos.length > 0) {
      clearTimeout(calcTimeoutRef.current);
      calcTimeoutRef.current = setTimeout(() => {
        runRecalculate();
      }, 150);
    }
    return () => clearTimeout(calcTimeoutRef.current);
  }, [markup, custoAdicional, selectedTaxes, unidadesPorEmbalagem]);

  // Handle XML File Upload
  const handleUploadXmls = async (files) => {
    try {
      setIsProcessing(true);
      const res = await uploadXmlFiles(files, user?.id, selectedTaxes);

      if (res.avisos && res.avisos.length > 0) {
        res.avisos.forEach((aviso) => showToast(aviso, 'info'));
      }
      if (res.erros && res.erros.length > 0) {
        res.erros.forEach((erro) => showToast(erro, 'error'));
      }

      if (res.produtos && res.produtos.length > 0) {
        // Inicializa dicionário de unidades por embalagem
        const initialUnidades = {};
        res.produtos.forEach((p) => {
          initialUnidades[p.id] = 1.0;
        });
        setUnidadesPorEmbalagem(initialUnidades);

        // Calcula métricas iniciais
        const calcResult = await calculateMetrics({
          produtos: res.produtos,
          markup,
          custo_adicional_unitario: custoAdicional,
          impostos_selecionados: selectedTaxes,
          unidades_por_embalagem: initialUnidades,
        });

        setProdutos(calcResult.produtos);
        setResumo(calcResult.resumo);

        showToast(`${res.produtos.length} produto(s) importado(s) com sucesso!`, 'success');
        
        // Efeito comemorativo de sucesso
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#0c8de4', '#10b981', '#6366f1'],
        });
      } else {
        showToast('Nenhum produto novo encontrado nos arquivos enviados.', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Inline unit change handler
  const handleUpdateUnidade = (productId, newUnit) => {
    setUnidadesPorEmbalagem((prev) => ({
      ...prev,
      [productId]: newUnit,
    }));
  };

  // Quick save current parameters to user profile
  const handleSaveAsDefault = async () => {
    if (!user) return;
    try {
      setIsSavingDefault(true);
      const res = await updateUserProfile({
        usuario_id: user.id,
        nome: user.nome,
        email: user.email,
        empresa: user.empresa || '',
        cargo: user.cargo || '',
        markup_padrao: markup,
        custo_adicional_padrao: custoAdicional,
        impostos_padrao: selectedTaxes,
      });
      setUser(res.user);
      showToast('Preferências salvas como padrão do seu perfil!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSavingDefault(false);
    }
  };

  // Export CSV
  const handleExportCsv = async () => {
    if (produtos.length === 0) return;
    try {
      await downloadCalculatedCsv(produtos);
      showToast('Planilha CSV exportada com sucesso!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleExportExcel = async () => {
    if (produtos.length === 0) return;
    try {
      await downloadCalculatedExcel(produtos);
      showToast('Planilha Excel exportada com sucesso!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Logout handler
  const handleLogout = () => {
    setUser(null);
    setProdutos([]);
    setResumo(null);
    setActiveTab('pricing');
    showToast('Sessão encerrada com sucesso.', 'info');
  };

  // If not authenticated, display modern Auth Page
  if (!user) {
    return (
      <>
        <AuthPage onLoginSuccess={(u) => setUser(u)} showToast={showToast} />
        <Toast toast={toast} onClose={() => setToast(null)} />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'pricing' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            
            {/* Metric Summary Cards */}
            {resumo && <MetricCards resumo={resumo} />}

            {/* XML Upload Box */}
            <FileUpload onUpload={handleUploadXmls} isProcessing={isProcessing} />

            {/* Configuration Controls */}
            {produtos.length > 0 && (
              <ConfigPanel
                markup={markup}
                setMarkup={setMarkup}
                custoAdicional={custoAdicional}
                setCustoAdicional={setCustoAdicional}
                selectedTaxes={selectedTaxes}
                setSelectedTaxes={setSelectedTaxes}
                onSaveAsDefault={handleSaveAsDefault}
                isSavingDefault={isSavingDefault}
              />
            )}

            {/* Products Table */}
            {produtos.length > 0 && (
              <ProductTable
                produtos={produtos}
                unidadesPorEmbalagem={unidadesPorEmbalagem}
                onUpdateUnidade={handleUpdateUnidade}
                onExportCsv={handleExportCsv}
                onExportExcel={handleExportExcel}
              />
            )}

            {/* Quick Charts */}
            {produtos.length > 0 && resumo && (
              <ChartsSection produtos={produtos} resumo={resumo} />
            )}

          </div>
        )}

        {activeTab === 'dashboard' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-6">
              <h1 className="text-2xl font-extrabold text-slate-800">📊 Dashboard Analítico de Precificação</h1>
              <p className="text-sm text-slate-500 mt-1">
                Visualização detalhada da composição de custos, margens e distribuição de lucros.
              </p>
            </div>
            {resumo && <MetricCards resumo={resumo} />}
            <ChartsSection produtos={produtos} resumo={resumo} />
          </div>
        )}

        {activeTab === 'history' && (
          <HistoryPage user={user} showToast={showToast} />
        )}

        {activeTab === 'profile' && (
          <ProfilePage
            user={user}
            onUserUpdated={(updated) => setUser(updated)}
            showToast={showToast}
          />
        )}
      </main>

      {/* Floating Notifications Toast */}
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
