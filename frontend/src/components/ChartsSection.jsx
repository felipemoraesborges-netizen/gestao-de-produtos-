import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { PieChart, BarChart2, TrendingUp, Sparkles } from 'lucide-react';

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
);

export default function ChartsSection({ produtos, resumo }) {
  if (!produtos || produtos.length === 0 || !resumo) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
        <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-300" />
        <p className="text-sm font-semibold">Envie arquivos XML para visualizar os gráficos e métricas analíticas.</p>
      </div>
    );
  }

  // 1. Dados para o Gráfico de Rosca: Composição dos Custos
  const totalBaseProdutos = produtos.reduce((acc, p) => acc + (p.valor_produtos || 0), 0);
  const totalFrete = produtos.reduce((acc, p) => acc + (p.frete || 0), 0);
  const totalImpostos = resumo.total_impostos || 0;
  const totalOutros = produtos.reduce((acc, p) => acc + ((p.seguro || 0) + (p.outras_despesas || 0)), 0);
  const totalCustosExtras = produtos.reduce((acc, p) => acc + (p.custo_adicional_total || 0), 0);

  const costBreakdownData = {
    labels: ['Valor Base dos Produtos', 'Impostos Incluídos', 'Frete Rateado', 'Seguro / Despesas', 'Custos Adicionais'],
    datasets: [
      {
        data: [totalBaseProdutos, totalImpostos, totalFrete, totalOutros, totalCustosExtras],
        backgroundColor: [
          '#0270c3', // Brand Blue
          '#6366f1', // Indigo
          '#f59e0b', // Amber
          '#8b5cf6', // Purple
          '#10b981', // Emerald
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  // 2. Dados para o Gráfico de Barras: Top 5 Produtos mais Lucrativos
  const topLucro = [...produtos]
    .sort((a, b) => (b.lucro_total || 0) - (a.lucro_total || 0))
    .slice(0, 6);

  const topProfitData = {
    labels: topLucro.map((p) => (p.produto.length > 20 ? p.produto.substring(0, 20) + '...' : p.produto)),
    datasets: [
      {
        label: 'Lucro Total (R$)',
        data: topLucro.map((p) => p.lucro_total || 0),
        backgroundColor: '#10b981',
        borderRadius: 8,
      },
      {
        label: 'Custo Total (R$)',
        data: topLucro.map((p) => p.custo_final || 0),
        backgroundColor: '#94a3b8',
        borderRadius: 8,
      },
    ],
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* Gráfico 1: Composição dos Custos */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-brand-600" />
            <h3 className="text-sm font-bold text-slate-800">Composição Estrutural de Custos</h3>
          </div>
          <span className="text-xs font-semibold text-slate-400">Total: R$ {resumo.total_custo?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
        </div>
        <div className="h-64 flex items-center justify-center">
          <Doughnut
            data={costBreakdownData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom',
                  labels: {
                    boxWidth: 12,
                    font: { size: 11, family: 'Inter' },
                    padding: 12,
                  },
                },
              },
            }}
          />
        </div>
      </div>

      {/* Gráfico 2: Top Produtos mais Lucrativos */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-800">Top Itens: Lucro vs Custo</h3>
          </div>
          <span className="text-xs font-semibold text-emerald-600">Top 6 Lucratividade</span>
        </div>
        <div className="h-64 flex items-center justify-center">
          <Bar
            data={topProfitData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom',
                  labels: {
                    boxWidth: 12,
                    font: { size: 11, family: 'Inter' },
                  },
                },
              },
              scales: {
                x: {
                  grid: { display: false },
                  ticks: { font: { size: 10 } },
                },
                y: {
                  grid: { color: '#f1f5f9' },
                  ticks: { font: { size: 10 } },
                },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
}
