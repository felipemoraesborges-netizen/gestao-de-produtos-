import React from 'react';
import { Sliders, Percent, DollarSign, ShieldCheck, BookmarkCheck, Check, HelpCircle } from 'lucide-react';

const IMPOSTOS_DESCRICAO = {
  'ICMS': 'Imposto estadual sobre circulação de mercadorias',
  'ICMS ST': 'Substituição Tributária recolhida na origem pelo fornecedor',
  'FCP': 'Fundo de Combate à Pobreza estadual',
  'FCP ST': 'FCP retido por Substituição Tributária',
  'IPI': 'Imposto federal sobre produtos industrializados',
  'II': 'Imposto de importação (caso aplicável)',
  'PIS': 'Contribuição para o Programa de Integração Social',
  'COFINS': 'Contribuição para o Financiamento da Seguridade Social',
};

const TODOS_IMPOSTOS = Object.keys(IMPOSTOS_DESCRICAO);

export default function ConfigPanel({
  markup,
  setMarkup,
  custoAdicional,
  setCustoAdicional,
  selectedTaxes,
  setSelectedTaxes,
  onSaveAsDefault,
  isSavingDefault,
}) {
  const toggleTax = (tax) => {
    if (selectedTaxes.includes(tax)) {
      setSelectedTaxes(selectedTaxes.filter((t) => t !== tax));
    } else {
      setSelectedTaxes([...selectedTaxes, tax]);
    }
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200/80 dark:border-zinc-800/80 shadow-sm p-6 mb-6 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100 dark:border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-500/10 text-brand-600 dark:text-brand-400 flex items-center justify-center font-bold">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-white">Parâmetros de Cálculo & Margens</h3>
            <p className="text-xs text-slate-400 dark:text-slate-500">Ajuste em tempo real com recálculo instantâneo</p>
          </div>
        </div>

        <button
          onClick={onSaveAsDefault}
          disabled={isSavingDefault}
          className="flex items-center gap-2 text-xs font-bold text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-500/10 hover:bg-brand-100 dark:hover:bg-brand-500/20 border border-brand-200 dark:border-brand-500/30 px-3.5 py-2 rounded-xl transition-all disabled:opacity-50 self-start sm:self-auto btn-press"
        >
          <BookmarkCheck className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          {isSavingDefault ? 'Salvando...' : 'Salvar como meu Padrão'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* 1. Markup */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Percent className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              Markup sobre o Custo (%)
              <span
                title="Percentual adicionado ao custo total final para formar o preço de revenda sugerido."
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-help"
              >
                <HelpCircle className="w-3.5 h-3.5" />
              </span>
            </label>
            <span className="text-sm font-extrabold text-brand-700 dark:text-brand-400 font-mono">
              {Number(markup).toFixed(1)}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="300"
            step="1"
            value={markup}
            onChange={(e) => setMarkup(parseFloat(e.target.value) || 0)}
            className="w-full h-2 bg-slate-200 dark:bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-brand-600"
          />
          <div className="flex items-center gap-1.5 pt-1 flex-wrap">
            {[30, 50, 60, 80, 100, 120].map((val) => (
              <button
                key={val}
                onClick={() => setMarkup(val)}
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border transition-all btn-press ${
                  markup === val
                    ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                    : 'bg-slate-50 dark:bg-zinc-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-zinc-700 hover:bg-slate-100 dark:hover:bg-zinc-700'
                }`}
              >
                {val}%
              </button>
            ))}
          </div>
        </div>

        {/* 2. Custo Adicional Unitário */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <DollarSign className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              Custo Adicional por Unidade (R$)
              <span
                title="Despesa extra fixa por item (embalagem individual, selos, sacola, adesivos)."
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-help"
              >
                <HelpCircle className="w-3.5 h-3.5" />
              </span>
            </label>
          </div>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 dark:text-slate-500">
              R$
            </span>
            <input
              type="number"
              min="0"
              step="0.05"
              value={custoAdicional}
              onChange={(e) => setCustoAdicional(parseFloat(e.target.value) || 0)}
              placeholder="0.00"
              className="w-full pl-9 pr-3 py-2 text-sm font-semibold rounded-xl border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono"
            />
          </div>
          <p className="text-[11px] text-slate-400 dark:text-slate-500">
            Aplicado a cada unidade real de venda avulsa
          </p>
        </div>

        {/* 3. Impostos Considerados */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              Impostos no Custo ({selectedTaxes.length})
              <span
                title="Selecione quais tributos da NF-e devem ser incorporados ao custo dos produtos."
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-help"
              >
                <HelpCircle className="w-3.5 h-3.5" />
              </span>
            </label>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {TODOS_IMPOSTOS.map((tax) => {
              const isSelected = selectedTaxes.includes(tax);
              const descricao = IMPOSTOS_DESCRICAO[tax];
              return (
                <button
                  key={tax}
                  onClick={() => toggleTax(tax)}
                  type="button"
                  title={descricao}
                  className={`text-xs font-bold px-2.5 py-1 rounded-lg border transition-all duration-150 flex items-center gap-1 btn-press ${
                    isSelected
                      ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600 shadow-sm'
                      : 'bg-slate-50 dark:bg-zinc-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-zinc-700 hover:bg-slate-100 dark:hover:bg-zinc-700 hover:text-slate-700 dark:hover:text-slate-200'
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3 text-cyan-400" />}
                  {tax}
                </button>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}

