import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Printer,
  RotateCcw,
  FileSpreadsheet,
  Boxes,
  ShieldCheck,
  Download,
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { getDesempenhoRelatorio, downloadReposicaoCsv } from '../services/api';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

export default function ReportsPage({ user, showToast }) {
  const [activeSubTab, setActiveSubTab] = useState('desempenho');
  const [loading, setLoading] = useState(true);
  const [dados, setDados] = useState(null);

  const fetchDados = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getDesempenhoRelatorio(user?.id);
      setDados(res);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [user?.id, showToast]);

  useEffect(() => {
    fetchDados();
  }, [fetchDados]);


  const handleExportCsv = async () => {
    try {
      await downloadReposicaoCsv(user?.id);
      showToast('Relatório de reposição exportado em CSV com sucesso!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <RotateCcw className="w-10 h-10 animate-spin text-brand-600 mx-auto mb-3" />
        <p className="text-slate-600 font-semibold text-sm">Gerando inteligência analítica e relatórios...</p>
      </div>
    );
  }

  const metricas = dados?.metricas || {};
  const topLucrativos = dados?.top_lucrativos || [];
  const topCapital = dados?.top_capital || [];
  const reposicao = dados?.reposicao_sugerida || [];

  // Gráfico 1: Saúde do Estoque (Doughnut)
  const healthChartData = {
    labels: ['Saudável / Normal', 'Estoque Baixo', 'Esgotado'],
    datasets: [
      {
        data: [
          metricas.itens_normais || 0,
          metricas.itens_baixo_estoque || 0,
          metricas.itens_esgotados || 0,
        ],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      },
    ],
  };

  // Gráfico 2: Top Mais Lucrativos (Bar)
  const profitChartData = {
    labels: topLucrativos.map((p) => (p.produto.length > 18 ? p.produto.slice(0, 18) + '...' : p.produto)),
    datasets: [
      {
        label: 'Lucro Unitário (R$)',
        data: topLucrativos.map((p) => p.lucro_unitario),
        backgroundColor: 'rgba(14, 165, 233, 0.85)',
        borderRadius: 8,
      },
      {
        label: 'Custo Unitário (R$)',
        data: topLucrativos.map((p) => p.custo_unitario),
        backgroundColor: 'rgba(203, 213, 225, 0.8)',
        borderRadius: 8,
      },
    ],
  };

  // Gráfico 3: Capital Imobilizado (Horizontal Bar)
  const capitalChartData = {
    labels: topCapital.map((p) => (p.produto.length > 18 ? p.produto.slice(0, 18) + '...' : p.produto)),
    datasets: [
      {
        label: 'Valor Total em Estoque (R$)',
        data: topCapital.map((p) => p.valor_investido),
        backgroundColor: 'rgba(99, 102, 241, 0.85)',
        borderRadius: 8,
      },
    ],
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 print:p-0">
      
      {/* Header com Navegação de Sub-Abas e Ações de Exportação */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-800">
              📊 Painéis de Análise & Relatórios
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
              Gerencial
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Métricas estratégicas de patrimônio, rentabilidade por produto e ordens inteligentes de compra.
          </p>
        </div>

        {/* Botoes de Ação */}
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDados}
            title="Atualizar Dados"
            className="p-2.5 bg-white border border-slate-200 hover:border-slate-300 text-slate-600 rounded-xl transition-all shadow-sm"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-3.5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow shadow-emerald-600/20"
          >
            <Download className="w-4 h-4" />
            Exportar Reposição (CSV)
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition-all shadow"
          >
            <Printer className="w-4 h-4" />
            Imprimir / Salvar PDF
          </button>
        </div>
      </div>

      {/* Sub-Aba Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 print:hidden">
        <button
          onClick={() => setActiveSubTab('desempenho')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'desempenho'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Visão Geral & Gráficos
        </button>
        <button
          onClick={() => setActiveSubTab('reposicao')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'reposicao'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Necessidade de Reposição ({reposicao.length})
        </button>
        <button
          onClick={() => setActiveSubTab('ranking')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'ranking'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Ranking de Rentabilidade
        </button>
      </div>

      {/* KPI Cards Executivos (Visíveis em todos os modos e na impressão) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Patrimônio em Estoque</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-brand-600 flex items-center justify-center">
              <Boxes className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-800 mt-2">
            R$ {(metricas.valor_total_custo || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Total de {(metricas.total_unidades || 0).toLocaleString('pt-BR')} unidades cadastradas
          </p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Faturamento Estimado</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-700 mt-2">
            R$ {(metricas.valor_total_venda || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-emerald-600 font-semibold mt-1">
            Margem de Lucro Média: {metricas.margem_media_pct || 0}%
          </p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Lucro Potencial</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-indigo-600 mt-2">
            R$ {(metricas.lucro_potencial || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Retorno líquido previsto sobre o estoque
          </p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-amber-200 bg-amber-50/40 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">Orçamento de Reposição</span>
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-700 mt-2">
            R$ {(metricas.total_custo_reposicao || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-amber-800 font-medium mt-1">
            Para abastecer {metricas.itens_reposicao_qtd || 0} produto(s) em baixa
          </p>
        </div>

      </div>

      {/* ABA 1: VISÃO GERAL & GRÁFICOS */}
      {activeSubTab === 'desempenho' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Gráfico de Distribuição da Saúde */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-slate-800 text-sm">Distribuição da Saúde do Estoque</h3>
                <p className="text-xs text-slate-400 mt-0.5">Classificação do volume de produtos</p>
              </div>
              <div className="h-56 flex items-center justify-center py-4">
                <Doughnut
                  data={healthChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    },
                    cutout: '68%',
                  }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100 text-center text-xs">
                <div>
                  <div className="font-black text-emerald-600 text-sm">{metricas.itens_normais || 0}</div>
                  <div className="text-[10px] text-slate-400">Saudáveis</div>
                </div>
                <div>
                  <div className="font-black text-amber-600 text-sm">{metricas.itens_baixo_estoque || 0}</div>
                  <div className="text-[10px] text-slate-400">Em Baixa</div>
                </div>
                <div>
                  <div className="font-black text-rose-600 text-sm">{metricas.itens_esgotados || 0}</div>
                  <div className="text-[10px] text-slate-400">Esgotados</div>
                </div>
              </div>
            </div>

            {/* Gráfico de Top 10 Produtos por Lucro Unitário */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-sm">Top 10 Produtos por Rentabilidade Unitária</h3>
                  <p className="text-xs text-slate-400 mt-0.5">Comparativo entre Custo de Compra e Lucro Líquido</p>
                </div>
                <span className="text-[11px] font-bold text-brand-600 bg-brand-50 px-2.5 py-1 rounded-lg">
                  Maior Margem
                </span>
              </div>
              <div className="h-64">
                <Bar
                  data={profitChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
                    },
                    scales: {
                      x: { grid: { display: false } },
                      y: { grid: { color: '#f1f5f9' } },
                    },
                  }}
                />
              </div>
            </div>

          </div>

          {/* Gráfico de Capital Imobilizado */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-800 text-sm">Top 10 Produtos com Maior Capital Imobilizado</h3>
                <p className="text-xs text-slate-400 mt-0.5">Produtos que concentram o maior valor monetário investido em estoque</p>
              </div>
              <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-lg">
                Patrimônio Ativo
              </span>
            </div>
            <div className="h-64">
              <Bar
                data={capitalChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  indexAxis: 'y',
                  plugins: {
                    legend: { display: false },
                  },
                  scales: {
                    x: { grid: { color: '#f1f5f9' } },
                    y: { grid: { display: false } },
                  },
                }}
              />
            </div>
          </div>

        </div>
      )}

      {/* ABA 2: RELATÓRIO DE REPOSIÇÃO & COMPRAS */}
      {activeSubTab === 'reposicao' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-slate-800 flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                Ordem de Reposição & Compras Sugeridas
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Cálculo automatizado para atingir 150% do estoque mínimo de segurança para cada item crítico.
              </p>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-400">Total Previsto de Compra:</span>
              <div className="text-xl font-black text-emerald-600">
                R$ {(metricas.total_custo_reposicao || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {reposicao.length === 0 ? (
            <div className="py-12 text-center text-slate-400">
              <ShieldCheck className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
              <h3 className="font-bold text-slate-700 text-sm">Estoque 100% Saudável!</h3>
              <p className="text-xs text-slate-500 mt-1">Nenhum produto atingiu o nível de estoque mínimo no momento.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-3 px-3">Código</th>
                    <th className="py-3 px-3">Produto</th>
                    <th className="py-3 px-3">Fornecedor</th>
                    <th className="py-3 px-3 text-center">Unidade</th>
                    <th className="py-3 px-3 text-right">Estoque Atual</th>
                    <th className="py-3 px-3 text-right">Mínimo</th>
                    <th className="py-3 px-3 text-right">Qtd Sugerida</th>
                    <th className="py-3 px-3 text-right">Custo Unit.</th>
                    <th className="py-3 px-3 text-right">Total Previsto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {reposicao.map((item) => (
                    <tr key={item.id} className="hover:bg-amber-50/20">
                      <td className="py-3 px-3 font-mono font-bold text-slate-700">
                        {item.codigo}
                      </td>
                      <td className="py-3 px-3 font-medium text-slate-800">
                        {item.produto}
                      </td>
                      <td className="py-3 px-3 text-slate-500">
                        {item.fornecedor}
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-slate-600">
                        {item.unidade}
                      </td>
                      <td className="py-3 px-3 text-right font-black text-rose-600">
                        {item.quantidade_atual}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-500">
                        {item.estoque_minimo}
                      </td>
                      <td className="py-3 px-3 text-right font-black text-amber-600 bg-amber-50/50">
                        {item.quantidade_sugerida}
                      </td>
                      <td className="py-3 px-3 text-right text-slate-600">
                        R$ {item.custo_unitario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-800">
                        R$ {item.custo_total_estimado.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-50 font-bold text-xs border-t-2 border-slate-200">
                    <td colSpan={6} className="py-3 px-3 text-slate-700">
                      Total ({reposicao.length} itens a repor)
                    </td>
                    <td className="py-3 px-3 text-right text-amber-700">
                      {reposicao.reduce((acc, r) => acc + r.quantidade_sugerida, 0).toLocaleString('pt-BR')} un
                    </td>
                    <td></td>
                    <td className="py-3 px-3 text-right text-emerald-700 text-sm font-black">
                      R$ {(metricas.total_custo_reposicao || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

        </div>
      )}

      {/* ABA 3: RANKING DE RENTABILIDADE */}
      {activeSubTab === 'ranking' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-extrabold text-slate-800 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-brand-600" />
              Ranking de Lucratividade Unitária por Mercadoria
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Identifique rapidamente os carros-chefe do seu portfólio para campanhas comerciais e negociação com fornecedores.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Posição</th>
                  <th className="py-3 px-4">Código</th>
                  <th className="py-3 px-4">Produto</th>
                  <th className="py-3 px-4 text-right">Custo Unitário</th>
                  <th className="py-3 px-4 text-right">Preço de Venda</th>
                  <th className="py-3 px-4 text-right">Lucro Unitário</th>
                  <th className="py-3 px-4 text-right">Margem de Lucro</th>
                  <th className="py-3 px-4 text-right">Faturamento Projetado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {topLucrativos.map((item, index) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-bold text-slate-400">
                      #{index + 1}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-700">
                      {item.codigo}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      {item.produto}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-600">
                      R$ {item.custo_unitario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-800">
                      R$ {item.preco_venda.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right font-black text-emerald-600">
                      + R$ {item.lucro_unitario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="inline-block px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700">
                        {item.margem_pct}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-800">
                      R$ {item.faturamento_projetado.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
