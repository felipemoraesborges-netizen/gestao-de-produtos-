import React, { useState, useEffect, useCallback } from 'react';
import {
  Boxes,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  SlidersHorizontal,
  AlertTriangle,
  XCircle,
  Search,
  Trash2,
  Edit3,
  RotateCcw,
  History,
  X,
  Package,
  DollarSign,
  TrendingUp,
  Building2,
  FileSpreadsheet,
} from 'lucide-react';
import ConfirmModal from '../components/ConfirmModal';
import {
  getEstoque,
  saveEstoqueItem,
  deleteEstoqueItem,
  movimentarEstoque,
  getMovimentacoesEstoque,
} from '../services/api';

export default function InventoryPage({ user, showToast, onNavigateToReports }) {
  const [loading, setLoading] = useState(true);
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [filtroStatus, setFiltroStatus] = useState('todos');
  const [busca, setBusca] = useState('');

  // Modais
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteConfirmItem, setDeleteConfirmItem] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [itemForm, setItemForm] = useState({
    codigo: '',
    produto: '',
    unidade: 'UN',
    quantidade_atual: 0,
    estoque_minimo: 5,
    custo_unitario: 0,
    preco_venda: 0,
    fornecedor_ultimo: '',
    categoria: 'Geral',
  });

  const [movModalOpen, setMovModalOpen] = useState(false);
  const [selectedProductForMov, setSelectedProductForMov] = useState(null);
  const [movForm, setMovForm] = useState({
    tipo: 'ENTRADA',
    quantidade: 1,
    motivo: '',
    documento_ref: '',
  });

  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [selectedProductForHistory, setSelectedProductForHistory] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Carregar dados de estoque
  const fetchEstoque = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getEstoque(user?.id, filtroStatus, busca);
      setProdutos(data.produtos || []);
      setResumo(data.resumo || null);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [user?.id, filtroStatus, busca, showToast]);

  useEffect(() => {
    fetchEstoque();
  }, [fetchEstoque]);

  // Abertura do Modal de Cadastro / Edição
  const handleOpenNewItemModal = () => {
    setEditingItem(null);
    setItemForm({
      codigo: '',
      produto: '',
      unidade: 'UN',
      quantidade_atual: 0,
      estoque_minimo: 5,
      custo_unitario: 0,
      preco_venda: 0,
      fornecedor_ultimo: '',
      categoria: 'Geral',
    });
    setItemModalOpen(true);
  };

  const handleOpenEditModal = (item) => {
    setEditingItem(item);
    setItemForm({
      codigo: item.codigo,
      produto: item.produto,
      unidade: item.unidade || 'UN',
      quantidade_atual: item.quantidade_atual,
      estoque_minimo: item.estoque_minimo,
      custo_unitario: item.custo_unitario,
      preco_venda: item.preco_venda,
      fornecedor_ultimo: item.fornecedor_ultimo || '',
      categoria: item.categoria || 'Geral',
    });
    setItemModalOpen(true);
  };

  const handleSaveItem = async (e) => {
    e.preventDefault();
    if (!itemForm.codigo.trim() || !itemForm.produto.trim()) {
      showToast('Código e Nome do Produto são obrigatórios!', 'error');
      return;
    }
    try {
      await saveEstoqueItem({
        id: editingItem ? editingItem.id : null,
        codigo: itemForm.codigo.trim(),
        produto: itemForm.produto.trim(),
        unidade: itemForm.unidade.trim() || 'UN',
        quantidade_atual: parseFloat(itemForm.quantidade_atual) || 0,
        estoque_minimo: parseFloat(itemForm.estoque_minimo) || 0,
        custo_unitario: parseFloat(itemForm.custo_unitario) || 0,
        preco_venda: parseFloat(itemForm.preco_venda) || 0,
        fornecedor_ultimo: itemForm.fornecedor_ultimo.trim(),
        categoria: itemForm.categoria.trim() || 'Geral',
        usuario_id: user?.id,
        usuario_nome: user?.nome,
      });
      showToast(
        editingItem
          ? 'Produto atualizado com sucesso!'
          : 'Novo produto adicionado ao estoque!',
        'success'
      );
      setItemModalOpen(false);
      fetchEstoque();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteConfirmItem) return;
    try {
      setIsDeleting(true);
      await deleteEstoqueItem(deleteConfirmItem.id, user?.id, user?.nome);
      showToast('Produto excluído com sucesso do estoque!', 'success');
      setDeleteConfirmItem(null);
      fetchEstoque();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Movimentações (Entrada / Saída / Ajuste)
  const handleOpenMovModal = (item) => {
    setSelectedProductForMov(item);
    setMovForm({
      tipo: 'ENTRADA',
      quantidade: 1,
      motivo: '',
      documento_ref: '',
    });
    setMovModalOpen(true);
  };

  const handleSaveMovimentacao = async (e) => {
    e.preventDefault();
    if (!selectedProductForMov) return;
    const qtd = parseFloat(movForm.quantidade);
    if (isNaN(qtd) || (qtd <= 0 && movForm.tipo !== 'AJUSTE')) {
      showToast('Informe uma quantidade válida para a movimentação!', 'error');
      return;
    }
    try {
      await movimentarEstoque({
        produto_id: selectedProductForMov.id,
        tipo: movForm.tipo,
        quantidade: qtd,
        motivo: movForm.motivo.trim() || 'Movimentação manual',
        documento_ref: movForm.documento_ref.trim(),
        usuario_id: user?.id,
        usuario_nome: user?.nome,
      });
      showToast(`Movimentação de ${movForm.tipo} realizada com sucesso!`, 'success');
      setMovModalOpen(false);
      fetchEstoque();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Histórico de Movimentações
  const handleOpenHistory = async (item) => {
    setSelectedProductForHistory(item);
    setHistoryModalOpen(true);
    setLoadingHistory(true);
    try {
      const data = await getMovimentacoesEstoque(user?.id, item.id);
      setMovimentacoes(data || []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Helper de badge de status
  const renderStatusBadge = (item) => {
    if (item.status_estoque === 'zerado') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
          Esgotado
        </span>
      );
    }
    if (item.status_estoque === 'baixo') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          Estoque Baixo
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        Normal
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Header com Título e Ação Principal */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-800">
              📦 Gestão de Estoque & Controle
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand-100 text-brand-700 border border-brand-200">
              Tempo Real
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Controle de inventário, alertas de reposição mínima, histórico de entradas/saídas e valorização patrimonial.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onNavigateToReports && (
            <button
              onClick={onNavigateToReports}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 hover:text-slate-900 rounded-xl text-xs font-bold transition-all shadow-sm"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              Relatório de Reposição
            </button>
          )}

          <button
            onClick={handleOpenNewItemModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-lg shadow-brand-500/20 hover:shadow-brand-500/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Novo Produto
          </button>
        </div>
      </div>

      {/* KPI Cards de Resumo */}
      {resumo && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
          
          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Itens Cadastrados</span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Boxes className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-black text-slate-800 mt-2">
              {resumo.total_itens}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {resumo.itens_normais} em nível saudável
            </p>
          </div>

          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Estoque Baixo</span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-black text-amber-600 mt-2">
              {resumo.itens_baixos}
            </div>
            <p className="text-[11px] text-amber-700 font-medium mt-0.5">
              Necessitam de reposição
            </p>
          </div>

          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Produtos Zerados</span>
              <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
                <XCircle className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-black text-rose-600 mt-2">
              {resumo.itens_zerados}
            </div>
            <p className="text-[11px] text-rose-700 font-medium mt-0.5">
              Ruptura de estoque
            </p>
          </div>

          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Patrimônio (Custo)</span>
              <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="text-xl sm:text-2xl font-black text-slate-800 mt-2">
              R$ {resumo.valor_total_custo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Capital imobilizado
            </p>
          </div>

          <div className="bg-white rounded-2xl p-4 border border-emerald-100 bg-gradient-to-br from-white to-emerald-50/40 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-800">Projeção de Venda</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="text-xl sm:text-2xl font-black text-emerald-700 mt-2">
              R$ {resumo.valor_total_venda.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-emerald-600 font-medium mt-0.5">
              Margem média: {resumo.margem_media_pct}%
            </p>
          </div>

        </div>
      )}

      {/* Alerta de Produtos em Baixa se houver */}
      {resumo && (resumo.itens_baixos > 0 || resumo.itens_zerados > 0) && (
        <div className="bg-amber-50 border border-amber-200/80 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shadow-md shadow-amber-500/20 shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-amber-900">
                Atenção: Existem {resumo.itens_baixos + resumo.itens_zerados} produto(s) demandando reposição imediata!
              </h2>
              <p className="text-xs text-amber-800 mt-0.5">
                {resumo.itens_zerados > 0 && `${resumo.itens_zerados} item(ns) estão com estoque zerado e `}
                {resumo.itens_baixos} item(ns) atingiram ou estão abaixo da margem de segurança configurada.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            <button
              onClick={() => setFiltroStatus('baixo')}
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shadow transition-all"
            >
              Ver Itens em Baixa
            </button>
            {onNavigateToReports && (
              <button
                onClick={onNavigateToReports}
                className="px-3 py-1.5 bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 rounded-lg text-xs font-bold transition-all"
              >
                Gerar Ordem de Compra
              </button>
            )}
          </div>
        </div>
      )}

      {/* Barra de Filtros e Busca */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        
        {/* Filtros em Pílulas */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setFiltroStatus('todos')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              filtroStatus === 'todos'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Todos ({resumo ? resumo.total_itens : 0})
          </button>
          <button
            onClick={() => setFiltroStatus('baixo')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              filtroStatus === 'baixo'
                ? 'bg-amber-500 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Estoque Baixo ({resumo ? resumo.itens_baixos : 0})
          </button>
          <button
            onClick={() => setFiltroStatus('zerado')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              filtroStatus === 'zerado'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Zerados ({resumo ? resumo.itens_zerados : 0})
          </button>
          <button
            onClick={() => setFiltroStatus('normal')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              filtroStatus === 'normal'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Saudáveis ({resumo ? resumo.itens_normais : 0})
          </button>
        </div>

        {/* Input de Busca */}
        <div className="relative min-w-[260px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por código, produto ou fornecedor..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs text-slate-700 outline-none transition-all"
          />
          {busca && (
            <button
              onClick={() => setBusca('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

      </div>

      {/* Tabela de Produtos */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-400">
            <RotateCcw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-600" />
            <p className="text-sm font-medium">Carregando estoque...</p>
          </div>
        ) : produtos.length === 0 ? (
          <div className="py-16 text-center px-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <Boxes className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-800">Nenhum produto encontrado</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              {busca || filtroStatus !== 'todos'
                ? 'Nenhum resultado corresponde aos filtros aplicados.'
                : 'Seu estoque ainda está vazio. Cadastre mercadorias manualmente ou importe XMLs de NF-e na aba de Precificação!'}
            </p>
            {(!busca && filtroStatus === 'todos') && (
              <button
                onClick={handleOpenNewItemModal}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold transition-all shadow"
              >
                <Plus className="w-4 h-4" />
                Cadastrar Primeiro Produto
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Código</th>
                  <th className="py-3 px-4">Produto</th>
                  <th className="py-3 px-4 text-center">Unidade</th>
                  <th className="py-3 px-4 text-right">Estoque Atual</th>
                  <th className="py-3 px-4 text-right">Mínimo</th>
                  <th className="py-3 px-4 text-right">Custo Unit.</th>
                  <th className="py-3 px-4 text-right">Preço Venda</th>
                  <th className="py-3 px-4 text-right">Margem</th>
                  <th className="py-3 px-4 text-right">Total Investido</th>
                  <th className="py-3 px-4 text-center">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {produtos.map((item) => (
                  <tr
                    key={item.id}
                    className={`hover:bg-slate-50/70 transition-colors ${
                      item.status_estoque === 'zerado'
                        ? 'bg-rose-50/20'
                        : item.status_estoque === 'baixo'
                        ? 'bg-amber-50/20'
                        : ''
                    }`}
                  >
                    <td className="py-3 px-4 whitespace-nowrap">
                      {renderStatusBadge(item)}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-700 whitespace-nowrap">
                      {item.codigo}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      <div>{item.produto}</div>
                      {item.fornecedor_ultimo && (
                        <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Building2 className="w-3 h-3 text-slate-400" />
                          {item.fornecedor_ultimo}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-slate-600">
                      {item.unidade || 'UN'}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <span
                        className={`font-black text-sm ${
                          item.status_estoque === 'zerado'
                            ? 'text-rose-600'
                            : item.status_estoque === 'baixo'
                            ? 'text-amber-600'
                            : 'text-slate-800'
                        }`}
                      >
                        {item.quantidade_atual.toLocaleString('pt-BR')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500 font-semibold whitespace-nowrap">
                      {item.estoque_minimo.toLocaleString('pt-BR')}
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-slate-600 whitespace-nowrap">
                      R$ {item.custo_unitario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-800 whitespace-nowrap">
                      R$ {item.preco_venda.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                          item.margem_lucro_pct >= 30
                            ? 'bg-emerald-50 text-emerald-700'
                            : item.margem_lucro_pct > 0
                            ? 'bg-blue-50 text-blue-700'
                            : 'bg-rose-50 text-rose-700'
                        }`}
                      >
                        {item.margem_lucro_pct}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-700 whitespace-nowrap">
                      R$ {item.valor_total_custo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => handleOpenMovModal(item)}
                          title="Registrar Movimentação (Entrada/Saída)"
                          className="p-1.5 rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-700 transition-colors"
                        >
                          <SlidersHorizontal className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenHistory(item)}
                          title="Ver Histórico de Movimentações"
                          className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                        >
                          <History className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenEditModal(item)}
                          title="Editar Cadastro"
                          className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirmItem(item)}
                          title="Excluir Produto"
                          className="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 transition-colors btn-press"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL 1: Cadastrar / Editar Produto */}
      {itemModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center">
                  <Package className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-slate-800 text-base">
                  {editingItem ? 'Editar Produto de Estoque' : 'Cadastrar Novo Produto'}
                </h3>
              </div>
              <button
                onClick={() => setItemModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveItem} className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Código *
                  </label>
                  <input
                    type="text"
                    required
                    value={itemForm.codigo}
                    onChange={(e) => setItemForm({ ...itemForm, codigo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs font-mono outline-none"
                    placeholder="Ex: PROD01"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Nome do Produto *
                  </label>
                  <input
                    type="text"
                    required
                    value={itemForm.produto}
                    onChange={(e) => setItemForm({ ...itemForm, produto: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                    placeholder="Ex: Parafuso Sextavado 8mm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Unidade
                  </label>
                  <input
                    type="text"
                    value={itemForm.unidade}
                    onChange={(e) => setItemForm({ ...itemForm, unidade: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                    placeholder="UN, CX, KG"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Saldo {editingItem ? 'Atual' : 'Inicial'}
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={itemForm.quantidade_atual}
                    onChange={(e) => setItemForm({ ...itemForm, quantidade_atual: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Estoque Mínimo
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={itemForm.estoque_minimo}
                    onChange={(e) => setItemForm({ ...itemForm, estoque_minimo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none text-amber-600 font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Custo Unitário (R$)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={itemForm.custo_unitario}
                    onChange={(e) => setItemForm({ ...itemForm, custo_unitario: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Preço de Venda (R$)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={itemForm.preco_venda}
                    onChange={(e) => setItemForm({ ...itemForm, preco_venda: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none font-bold text-emerald-700"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Fornecedor Habitual
                  </label>
                  <input
                    type="text"
                    value={itemForm.fornecedor_ultimo}
                    onChange={(e) => setItemForm({ ...itemForm, fornecedor_ultimo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                    placeholder="Nome da distribuidora..."
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Categoria
                  </label>
                  <input
                    type="text"
                    value={itemForm.categoria}
                    onChange={(e) => setItemForm({ ...itemForm, categoria: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                    placeholder="Geral, Ferragens, Eletrônicos..."
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setItemModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow transition-all"
                >
                  {editingItem ? 'Salvar Alterações' : 'Cadastrar Mercadoria'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Registrar Movimentação de Estoque */}
      {movModalOpen && selectedProductForMov && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4 text-brand-600" />
                  Movimentação de Estoque
                </h3>
                <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">
                  {selectedProductForMov.produto} (Cód: {selectedProductForMov.codigo})
                </p>
              </div>
              <button
                onClick={() => setMovModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveMovimentacao} className="space-y-4">
              {/* Seleção do Tipo */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setMovForm({ ...movForm, tipo: 'ENTRADA' })}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                    movForm.tipo === 'ENTRADA'
                      ? 'bg-emerald-500 text-white border-emerald-600 shadow-sm'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  Entrada (+)
                </button>
                <button
                  type="button"
                  onClick={() => setMovForm({ ...movForm, tipo: 'SAIDA' })}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                    movForm.tipo === 'SAIDA'
                      ? 'bg-rose-500 text-white border-rose-600 shadow-sm'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <ArrowDownRight className="w-3.5 h-3.5" />
                  Saída (-)
                </button>
                <button
                  type="button"
                  onClick={() => setMovForm({ ...movForm, tipo: 'AJUSTE' })}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                    movForm.tipo === 'AJUSTE'
                      ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Balanço (=)
                </button>
              </div>

              {/* Quantidade */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  {movForm.tipo === 'AJUSTE' ? 'Novo Saldo Real:' : 'Quantidade a Movimentar:'}
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  value={movForm.quantidade}
                  onChange={(e) => setMovForm({ ...movForm, quantidade: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-sm font-black outline-none"
                  placeholder="0.00"
                />
              </div>

              {/* Preview de Saldo Resultante */}
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 text-xs flex items-center justify-between">
                <div>
                  <span className="text-slate-500">Saldo Atual:</span>
                  <span className="font-bold text-slate-700 ml-1.5">
                    {selectedProductForMov.quantidade_atual} {selectedProductForMov.unidade}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Novo Saldo:</span>
                  <span
                    className={`font-black ml-1.5 ${
                      movForm.tipo === 'ENTRADA'
                        ? 'text-emerald-600'
                        : movForm.tipo === 'SAIDA'
                        ? 'text-rose-600'
                        : 'text-indigo-600'
                    }`}
                  >
                    {movForm.tipo === 'ENTRADA'
                      ? selectedProductForMov.quantidade_atual + (parseFloat(movForm.quantidade) || 0)
                      : movForm.tipo === 'SAIDA'
                      ? selectedProductForMov.quantidade_atual - (parseFloat(movForm.quantidade) || 0)
                      : parseFloat(movForm.quantidade) || 0}{' '}
                    {selectedProductForMov.unidade}
                  </span>
                </div>
              </div>

              {/* Motivo */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Motivo / Justificativa
                </label>
                <input
                  type="text"
                  value={movForm.motivo}
                  onChange={(e) => setMovForm({ ...movForm, motivo: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none"
                  placeholder="Ex: Venda avulsa, Devolução, Perda/Avaria..."
                />
              </div>

              {/* Documento de referência */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Documento de Referência (Opcional)
                </label>
                <input
                  type="text"
                  value={movForm.documento_ref}
                  onChange={(e) => setMovForm({ ...movForm, documento_ref: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs outline-none font-mono"
                  placeholder="Ex: Pedido #1234, NF-e 450..."
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setMovModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow transition-all"
                >
                  Confirmar Movimentação
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Histórico de Movimentações do Produto */}
      {historyModalOpen && selectedProductForHistory && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                  <History className="w-4 h-4 text-brand-600" />
                  Histórico de Movimentações
                </h3>
                <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm">
                  {selectedProductForHistory.produto} (Cód: {selectedProductForHistory.codigo})
                </p>
              </div>
              <button
                onClick={() => setHistoryModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
              {loadingHistory ? (
                <div className="py-8 text-center text-slate-400">
                  <RotateCcw className="w-6 h-6 animate-spin mx-auto mb-1 text-brand-600" />
                  <p className="text-xs font-medium">Carregando histórico...</p>
                </div>
              ) : movimentacoes.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-xs">
                  Nenhuma movimentação registrada para este produto.
                </div>
              ) : (
                movimentacoes.map((m) => (
                  <div
                    key={m.id}
                    className="bg-slate-50 rounded-xl p-3 border border-slate-200 text-xs flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs ${
                          m.tipo === 'ENTRADA'
                            ? 'bg-emerald-100 text-emerald-700'
                            : m.tipo === 'SAIDA'
                            ? 'bg-rose-100 text-rose-700'
                            : 'bg-indigo-100 text-indigo-700'
                        }`}
                      >
                        {m.tipo === 'ENTRADA' ? '+' : m.tipo === 'SAIDA' ? '-' : '='}
                      </div>
                      <div>
                        <div className="font-bold text-slate-800">
                          {m.tipo} de {m.quantidade} {selectedProductForHistory.unidade}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {m.motivo || 'Sem justificativa'} {m.documento_ref && `• Ref: ${m.documento_ref}`}
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="font-mono text-[11px] font-bold text-slate-700">
                        {m.quantidade_anterior} ➔ {m.quantidade_nova}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {m.data_hora}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 border-t border-slate-100 text-right">
              <button
                onClick={() => setHistoryModalOpen(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL DE CONFIRMAÇÃO DE EXCLUSÃO */}
      <ConfirmModal
        isOpen={!!deleteConfirmItem}
        title="Remover Produto do Estoque"
        message={`Tem certeza que deseja remover permanentemente o item "${deleteConfirmItem?.produto}" (${deleteConfirmItem?.codigo}) do catálogo de estoque?`}
        confirmText={isDeleting ? 'Excluindo...' : 'Sim, Excluir'}
        cancelText="Cancelar"
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteConfirmItem(null)}
      />

    </div>
  );
}

