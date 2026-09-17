import React, { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import Navbar from './components/Navbar';
import MetricCards from './components/MetricCards';
import FileUpload from './components/FileUpload';
import ConfigPanel from './components/ConfigPanel';
import ProductTable from './components/ProductTable';
import ChartsSection from './components/ChartsSection';
import Toast from './components/Toast';
import WelcomeGuide from './components/WelcomeGuide';

import AuthPage from './pages/AuthPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';
import InventoryPage from './pages/InventoryPage';
import ReportsPage from './pages/ReportsPage';
import AuditPage from './pages/AuditPage';

import {
  updateUserProfile,
  uploadXmlFiles,
  calculateMetrics,
  downloadCalculatedCsv,
  incorporarNfeAoEstoque,
  getEstoque,
  logAuditoriaFrontend,
  logoutUser,
} from './services/api';

export default function App() {
  // 1. Theme State (Dark / Light)
  const [theme, setTheme] = useState(() => {
    try {
      const stored = localStorage.getItem('gestao_theme');
      if (stored) return stored;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    try {
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      localStorage.setItem('gestao_theme', theme);
    } catch {
      // silencioso
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // 2. Authentication State
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('gestao_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // 3. Navigation State
  const [activeTab, setActiveTab] = useState('pricing');
  const [toast, setToast] = useState(null);
  const [alertaEstoqueCount, setAlertaEstoqueCount] = useState(0);

  // 4. Onboarding Guide State
  const [showGuide, setShowGuide] = useState(() => {
    try {
      return localStorage.getItem('gestao_hide_guide') !== 'true';
    } catch {
      return true;
    }
  });

  // 5. Pricing & Product State
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSavingDefault, setIsSavingDefault] = useState(false);

  const [markup, setMarkup] = useState(60.0);
  const [custoAdicional, setCustoAdicional] = useState(0.0);
  const [selectedTaxes, setSelectedTaxes] = useState(['ICMS ST', 'FCP ST', 'IPI', 'II']);
  const [unidadesPorEmbalagem, setUnidadesPorEmbalagem] = useState({});

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
  }, []);

  // Buscar alertas de estoque para badge na Navbar
  const fetchAlertasEstoque = useCallback(async () => {
    if (!user) return;
    try {
      const res = await getEstoque(user.id);
      if (res && res.resumo) {
        setAlertaEstoqueCount((res.resumo.itens_baixos || 0) + (res.resumo.itens_zerados || 0));
      }
    } catch {
      // Silencioso
    }
  }, [user]);

  useEffect(() => {
    fetchAlertasEstoque();
  }, [fetchAlertasEstoque, activeTab]);

  // Sincronizar preferências do usuário quando perfil carregar
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

  // Recalcular métricas quando parâmetros ou embalagens mudarem
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

  // Debounced live calculation
  const calcTimeoutRef = useRef(null);
  useEffect(() => {
    if (produtos.length > 0) {
      clearTimeout(calcTimeoutRef.current);
      calcTimeoutRef.current = setTimeout(() => {
        runRecalculate();
      }, 150);
    }
    return () => clearTimeout(calcTimeoutRef.current);
  }, [runRecalculate, produtos.length]);

  // Carregar dados de demonstração para novos usuários
  const handleLoadDemo = async () => {
    const demoProdutos = [
      {
        id: 'DEMO_01',
        codigo: 'PAR-INOX-316',
        produto: 'Parafuso Sextavado Aço Inox 316 (Caixa c/ 100 un)',
        unidade: 'CX',
        quantidade: 10,
        unidades_por_embalagem: 100,
        quantidade_real: 1000,
        valor_produtos: 450.00,
        frete: 35.00,
        seguro: 5.00,
        outras_despesas: 0.00,
        desconto: 10.00,
        icms: 54.00,
        icms_st: 32.50,
        ipi: 22.50,
        ii: 0.00,
        pis: 7.42,
        cofins: 34.20,
        numero_nota: '10482',
        serie_nota: '1',
        fornecedor: 'Metalúrgica Inox Brasil Ltda',
        cnpj_emit: '12.345.678/0001-90',
        chave_acesso: '35260812345678000190550010000104821876543210',
        arquivo_xml: 'demo_nfe_parafusos.xml',
      },
      {
        id: 'DEMO_02',
        codigo: 'ISOT-CITRUS-500',
        produto: 'Bebida Isotônica Citrus 500ml (Fardo c/ 12 garrafas)',
        unidade: 'FD',
        quantidade: 25,
        unidades_por_embalagem: 12,
        quantidade_real: 300,
        valor_produtos: 1125.00,
        frete: 65.00,
        seguro: 0.00,
        outras_despesas: 0.00,
        desconto: 25.00,
        icms: 135.00,
        icms_st: 85.00,
        ipi: 0.00,
        ii: 0.00,
        pis: 18.56,
        cofins: 85.50,
        numero_nota: '88219',
        serie_nota: '2',
        fornecedor: 'Distribuidora Bebidas & Cia S.A.',
        cnpj_emit: '98.765.432/0001-11',
        chave_acesso: '35260898765432000111550020000882191987654321',
        arquivo_xml: 'demo_nfe_isotonico.xml',
      },
      {
        id: 'DEMO_03',
        codigo: 'BOB-TERM-80',
        produto: 'Bobina Térmica PDV Amarela 80mm x 40m (Caixa c/ 30 un)',
        unidade: 'CX',
        quantidade: 15,
        unidades_por_embalagem: 30,
        quantidade_real: 450,
        valor_produtos: 855.00,
        frete: 42.00,
        seguro: 0.00,
        outras_despesas: 0.00,
        desconto: 0.00,
        icms: 102.60,
        icms_st: 0.00,
        ipi: 42.75,
        ii: 0.00,
        pis: 14.10,
        cofins: 65.00,
        numero_nota: '44102',
        serie_nota: '1',
        fornecedor: 'Papéis & Suprimentos Industriais',
        cnpj_emit: '44.555.666/0001-22',
        chave_acesso: '35260844555666000122550010000441021456789012',
        arquivo_xml: 'demo_nfe_bobinas.xml',
      },
      {
        id: 'DEMO_04',
        codigo: 'ALC-GEL-70-1L',
        produto: 'Álcool em Gel Antisséptico 70% 1L (Caixa c/ 6 frascos)',
        unidade: 'CX',
        quantidade: 20,
        unidades_por_embalagem: 6,
        quantidade_real: 120,
        valor_produtos: 720.00,
        frete: 30.00,
        seguro: 0.00,
        outras_despesas: 0.00,
        desconto: 15.00,
        icms: 86.40,
        icms_st: 45.00,
        ipi: 0.00,
        ii: 0.00,
        pis: 11.88,
        cofins: 54.72,
        numero_nota: '77310',
        serie_nota: '1',
        fornecedor: 'Química & Higiene Nacional S.A.',
        cnpj_emit: '77.888.999/0001-33',
        chave_acesso: '35260877888999000133550010000773101789012345',
        arquivo_xml: 'demo_nfe_alcool.xml',
      }
    ];

    const initialUnidades = {
      'DEMO_01': 100,
      'DEMO_02': 12,
      'DEMO_03': 30,
      'DEMO_04': 6,
    };
    setUnidadesPorEmbalagem(initialUnidades);

    try {
      setIsProcessing(true);
      const calcResult = await calculateMetrics({
        produtos: demoProdutos,
        markup,
        custo_adicional_unitario: custoAdicional,
        impostos_selecionados: selectedTaxes,
        unidades_por_embalagem: initialUnidades,
      });

      setProdutos(calcResult.produtos);
      setResumo(calcResult.resumo);

      showToast('Dados de demonstração carregados com sucesso! Experimente ajustar embalagens e markup.', 'success');
      confetti({
        particleCount: 90,
        spread: 75,
        origin: { y: 0.6 },
        colors: ['#0c8de4', '#10b981', '#6366f1'],
      });
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Upload de arquivos XML
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
        const initialUnidades = {};
        res.produtos.forEach((p) => {
          initialUnidades[p.id] = 1.0;
        });
        setUnidadesPorEmbalagem(initialUnidades);

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

  // Incorporar produtos calculados ao estoque contínuo
  const handleIncorporarEstoque = async () => {
    if (produtos.length === 0) {
      showToast('Nenhum produto processado para incorporar ao estoque.', 'error');
      return;
    }
    try {
      const numeroNota = produtos[0]?.numero_nota || '';
      const res = await incorporarNfeAoEstoque({
        produtos,
        usuario_id: user?.id,
        usuario_nome: user?.nome,
        numero_nota: numeroNota,
      });

      showToast(res.message || 'Produtos incorporados ao estoque com sucesso!', 'success');
      confetti({
        particleCount: 100,
        spread: 80,
        origin: { y: 0.5 },
        colors: ['#10b981', '#6366f1', '#f59e0b'],
      });
      fetchAlertasEstoque();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Salvar preferências como padrão do perfil
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

  // Exportar CSV
  const handleExportCsv = async () => {
    if (produtos.length === 0) return;
    try {
      await downloadCalculatedCsv(produtos);
      showToast('Planilha CSV exportada com sucesso!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Auto-logout se a sessão expirar
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setProdutos([]);
      setResumo(null);
      showToast('Sessão expirada. Por favor, acesse novamente.', 'warning');
    };
    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, [showToast]);

  // Logout handler
  const handleLogout = async () => {
    if (user) {
      logAuditoriaFrontend({
        usuario_id: user.id,
        usuario_nome: user.nome,
        acao: 'LOGOUT',
        detalhes: `Usuário '${user.usuario}' encerrou a sessão.`,
      });
    }
    await logoutUser();
    setUser(null);
    setProdutos([]);
    setResumo(null);
    setActiveTab('pricing');
    showToast('Sessão encerrada com sucesso.', 'info');
  };

  // Se não autenticado, renderizar AuthPage
  if (!user) {
    return (
      <>
        <AuthPage onLoginSuccess={(u) => setUser(u)} showToast={showToast} />
        <Toast toast={toast} onClose={() => setToast(null)} />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-800 dark:text-slate-100 flex flex-col transition-colors duration-200">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={handleLogout}
        alertaEstoqueCount={alertaEstoqueCount}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'pricing' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            
            {/* Onboarding Welcome Guide */}
            {showGuide && (
              <WelcomeGuide
                onLoadDemo={handleLoadDemo}
                onDismiss={() => {
                  setShowGuide(false);
                  try {
                    localStorage.setItem('gestao_hide_guide', 'true');
                  } catch {
                    // silencioso
                  }
                }}
              />
            )}

            {/* Metric Summary Cards */}
            {resumo && <MetricCards resumo={resumo} />}

            {/* XML Upload Box */}
            <FileUpload
              onUpload={handleUploadXmls}
              isProcessing={isProcessing}
              onLoadDemo={produtos.length === 0 ? handleLoadDemo : undefined}
            />

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
                onIncorporarEstoque={handleIncorporarEstoque}
              />
            )}

            {/* Quick Charts */}
            {produtos.length > 0 && resumo && (
              <ChartsSection produtos={produtos} resumo={resumo} theme={theme} />
            )}

          </div>
        )}

        {activeTab === 'inventory' && (
          <InventoryPage
            user={user}
            showToast={showToast}
            onNavigateToReports={() => setActiveTab('reports')}
          />
        )}

        {activeTab === 'reports' && (
          <ReportsPage
            user={user}
            showToast={showToast}
          />
        )}

        {activeTab === 'history' && (
          <HistoryPage user={user} showToast={showToast} />
        )}

        {activeTab === 'audit' && (
          <AuditPage user={user} showToast={showToast} />
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


