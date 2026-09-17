import React from 'react';
import { DollarSign, TrendingUp, Percent, Layers, HelpCircle } from 'lucide-react';

export default function MetricCards({ resumo }) {
  if (!resumo) return null;

  const formatBRL = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
  };

  const cards = [
    {
      title: 'Faturamento Estimado',
      value: formatBRL(resumo.total_faturamento),
      subtitle: `${resumo.total_itens || 0} produto(s) no cálculo`,
      icon: DollarSign,
      gradient: 'from-blue-600 to-cyan-500',
      textLight: 'text-blue-700 dark:text-blue-400',
      badge: 'Projeção',
      info: 'Receita bruta estimada com a venda de todas as unidades calculadas.',
    },
    {
      title: 'Lucro Bruto Estimado',
      value: formatBRL(resumo.total_lucro),
      subtitle: `Margem média de ${resumo.margem_media_pct || 0}%`,
      icon: TrendingUp,
      gradient: 'from-emerald-600 to-teal-500',
      textLight: 'text-emerald-700 dark:text-emerald-400',
      badge: 'Ganho Líquido',
      info: 'Diferença entre o faturamento projetado e o custo total com impostos e frete.',
    },
    {
      title: 'Custo Total Acumulado',
      value: formatBRL(resumo.total_custo),
      subtitle: `Impostos: ${formatBRL(resumo.total_impostos)}`,
      icon: Layers,
      gradient: 'from-slate-700 to-slate-900 dark:from-zinc-700 dark:to-zinc-900',
      textLight: 'text-slate-800 dark:text-slate-200',
      badge: 'Compra + Taxas',
      info: 'Custo total de aquisição somando produtos, impostos rateados e despesas acessórias.',
    },
    {
      title: 'Margem de Lucro Média',
      value: `${resumo.margem_media_pct || 0}%`,
      subtitle: `Frete total: ${formatBRL(resumo.total_frete)}`,
      icon: Percent,
      gradient: 'from-violet-600 to-indigo-500',
      textLight: 'text-violet-700 dark:text-violet-400',
      badge: 'Rentabilidade',
      info: 'Percentual médio de lucro sobre o preço de venda final sugerido.',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="bg-white dark:bg-zinc-900 rounded-2xl p-5 border border-slate-200/80 dark:border-zinc-800/80 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-zinc-700 transition-all duration-200 relative overflow-hidden group"
          >
            {/* Top Accent Line */}
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${card.gradient}`} />
            
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-500 dark:text-slate-400 tracking-wide uppercase">
                  {card.title}
                </span>
                <span title={card.info} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-help">
                  <HelpCircle className="w-3.5 h-3.5" />
                </span>
              </div>
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white shadow-md shadow-slate-200 dark:shadow-none transition-transform group-hover:scale-105`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="flex flex-col">
              <span className={`text-2xl font-extrabold tracking-tight font-mono ${card.textLight}`}>
                {card.value}
              </span>
              <span className="text-xs font-medium text-slate-400 dark:text-slate-500 mt-1 flex items-center gap-1">
                {card.subtitle}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

