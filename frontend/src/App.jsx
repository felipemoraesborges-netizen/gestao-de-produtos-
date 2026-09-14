import React, { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import { ArrowRight, FileSpreadsheet, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react';
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
  logoutUser,
  updateUserProfile,
  uploadXmlFiles,
  calculateMetrics,
  downloadCalculatedCsv,
  downloadCalculatedExcel,
} from './services/api';

export default function App() {
  // 1. Authentication State
  const [user, setUser] = useState(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  // 2. Navigation State
  const [activeTab, setActiveTab] = useState('pricing');
  const [toast, setToast] = useState(null);

  // 3. Pricing & Product State
  const [produtos, setProdutos] = useState([]);
  const [baseProdutos, setBaseProdutos] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSavingDefault, setIsSavingDefault] = useState(false);

  const [markup, setMarkup] = useState(60.0);
  const [custoAdicional, setCustoAdicional] = useState(0.0);
  const [selectedTaxes, setSelectedTaxes] = useState(['ICMS ST', 'FCP ST', 'IPI', 'II']);
  const [unidadesPorEmbalagem, setUnidadesPorEmbalagem] = useState({});
  const podeEditarPrecos = ['admin', 'operador'].includes(user?.nivel_acesso || 'operador');

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  // Restore and validate the saved session when the application starts.
  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      try {
        const freshUser = await getUserProfile();
        if (!cancelled) setUser(freshUser);
      } catch (error) {
        console.error('Sessão salva inválida ou expirada:', error);
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsRestoringSession(false);
      }
    };

    restoreSession();
    return () => { cancelled = true; };
  }, []);

  // Sync user defaults when user logs in or profile changes
  useEffect(() => {
    if (user) {
      if (user.markup_padrao !== undefined) setMarkup(Number(user.markup_padrao));
      if (user.custo_adicional_padrao !== undefined) setCustoAdicional(Number(user.custo_adicional_padrao));
      if (user.impostos_padrao && Array.isArray(user.impostos_padrao)) setSelectedTaxes(user.impostos_padrao);
    }
  }, [user]);

  // Recalculate metrics when parameters or packaging change
  const runRecalculate = useCallback(async () => {
    if (baseProdutos.length === 0) return;
    try {
      const calcResult = await calculateMetrics({
        produtos: baseProdutos,
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
  }, [baseProdutos, markup, custoAdicional, selectedTaxes, unidadesPorEmbalagem]);

  // Debounced live calculation when inputs change
  const calcTimeoutRef = useRef(null);
  useEffect(() => {
    if (baseProdutos.length > 0) {
      clearTimeout(calcTimeoutRef.current);
      calcTimeoutRef.current = setTimeout(() => {
        runRecalculate();
      }, 150);
    }
    return () => clearTimeout(calcTimeoutRef.current);
  }, [baseProdutos, markup, custoAdicional, selectedTaxes, unidadesPorEmbalagem, runRecalculate]);

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

        setBaseProdutos(res.produtos);
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
  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch (error) {
      console.error('Erro ao encerrar a sess?o no servidor:', error);
    }
    setUser(null);
    setProdutos([]);
    setBaseProdutos([]);
    setResumo(null);
    setActiveTab('pricing');
    showToast('Sessão encerrada com sucesso.', 'info');
  };

  if (isRestoringSession) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-white">
          <div className="w-12 h-12 rounded-2xl bg-brand-600/20 border border-brand-400/30 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-brand-300 animate-pulse" />
          </div>
          <div className="text-center">
            <p className="font-bold">Carregando seu ambiente</p>
            <p className="text-xs text-slate-400 mt-1">Validando sua sessão com segurança...</p>
          </div>
        </div>
      </div>
    );
  }

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
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-navy-900 via-slate-900 to-brand-900 px-6 py-8 sm:px-10 sm:py-10 mb-6 shadow-xl shadow-slate-300/40">
              <div className="absolute -right-16 -top-24 w-72 h-72 rounded-full bg-brand-500/20 blur-3xl" />
              <div className="absolute -bottom-32 left-1/3 w-80 h-80 rounded-full bg-cyan-400/10 blur-3xl" />
              <div className="relative max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-brand-300/25 bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-brand-200">
                  <Sparkles className="w-3.5 h-3.5" />
                  Central de precificação
                </div>
                <h1 className="mt-4 text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                  Olá, {user.nome?.split(' ')[0] || 'seja bem-vindo'}.
                  <span className="block text-brand-200">Vamos transformar seus XMLs em decisões melhores.</span>
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                  Importe suas notas fiscais, ajuste suas margens e acompanhe custos e lucros em um só lugar.
                </p>
                <div className="mt-6 flex flex-wrap gap-3 text-xs font-semibold text-slate-200">
                  <span className="inline-flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-300" />Dados protegidos por sessão</span>
                  <span className="inline-flex items-center gap-2"><FileSpreadsheet className="w-4 h-4 text-cyan-300" />Exportação para Excel</span>
                </div>
              </div>
            </section>
            
            {/* Metric Summary Cards */}
            {resumo && <MetricCards resumo={resumo} />}

            {/* XML Upload Box */}
            {podeEditarPrecos ? (
              <FileUpload onUpload={handleUploadXmls} isProcessing={isProcessing} />
            ) : (
              <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
                Seu perfil é somente consulta. Você pode acompanhar o histórico, mas não pode importar ou recalcular produtos.
              </div>
            )}

            {!produtos.length && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {[
                  { icon: UploadCloud, title: '1. Importe seus XMLs', text: 'Envie uma ou várias notas fiscais de uma vez.' },
                  { icon: Sparkles, title: '2. Ajuste sua margem', text: 'Teste markup, custos adicionais e impostos em tempo real.' },
                  { icon: ArrowRight, title: '3. Tome decisões', text: 'Compare resultados e exporte uma planilha pronta.' },
                ].map(({ icon: Icon, title, text }) => (
                  <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center mb-3">
                      <Icon className="w-4 h-4" />
                    </div>
                    <h2 className="text-sm font-bold text-slate-800">{title}</h2>
                    <p className="text-xs leading-5 text-slate-500 mt-1">{text}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Configuration Controls */}
            {produtos.length > 0 && podeEditarPrecos && (
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
