import React from 'react';
import { DollarSign, TrendingUp, PackageCheck, Percent, Layers, Truck } from 'lucide-react';

export default function MetricCards({ resumo }) {
  if (!resumo) return null;

  const formatBRL = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
  };

  const cards = [
    {
      title: 'Faturamento Total Estimado',
      value: formatBRL(resumo.total_faturamento),
      subtitle: `${resumo.total_itens || 0} produto(s) no cálculo`,
      icon: DollarSign,
      gradient: 'from-blue-600 to-cyan-500',
      bgLight: 'bg-blue-50/70',
      borderLight: 'border-blue-100',
      textColor: 'text-blue-700',
    },
    {
      title: 'Lucro Bruto Estimado',
      value: formatBRL(resumo.total_lucro),
      subtitle: `Margem média de ${resumo.margem_media_pct || 0}%`,
      icon: TrendingUp,
      gradient: 'from-emerald-600 to-teal-500',
      bgLight: 'bg-emerald-50/70',
      borderLight: 'border-emerald-100',
      textColor: 'text-emerald-700',
    },
    {
      title: 'Custo Total Acumulado',
      value: formatBRL(resumo.total_custo),
      subtitle: `Impostos: ${formatBRL(resumo.total_impostos)}`,
      icon: Layers,
      gradient: 'from-slate-700 to-slate-900',
      bgLight: 'bg-slate-50/70',
      borderLight: 'border-slate-200',
      textColor: 'text-slate-800',
    },
    {
      title: 'Margem de Lucro Média',
      value: `${resumo.margem_media_pct || 0}%`,
      subtitle: `Frete total: ${formatBRL(resumo.total_frete)}`,
      icon: Percent,
      gradient: 'from-violet-600 to-indigo-500',
      bgLight: 'bg-violet-50/70',
      borderLight: 'border-violet-100',
      textColor: 'text-violet-700',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-all duration-200 relative overflow-hidden group"
          >
            {/* Top Accent Line */}
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${card.gradient}`} />
            
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-500 tracking-wide uppercase">
                {card.title}
              </span>
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white shadow-md shadow-slate-200`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="flex flex-col">
              <span className={`text-2xl font-extrabold tracking-tight ${card.textColor}`}>
                {card.value}
              </span>
              <span className="text-xs font-medium text-slate-400 mt-1 flex items-center gap-1">
                {card.subtitle}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
