import React from 'react';
import { Sliders, Percent, DollarSign, ShieldCheck, BookmarkCheck, Check } from 'lucide-react';

const TODOS_IMPOSTOS = ['ICMS', 'ICMS ST', 'FCP', 'FCP ST', 'IPI', 'II', 'PIS', 'COFINS'];

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
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center font-bold">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Parâmetros de Cálculo & Margens</h3>
            <p className="text-xs text-slate-400">Ajuste em tempo real sem necessidade de recarregar a tela</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onSaveAsDefault}
          disabled={isSavingDefault}
          className="flex items-center gap-2 text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 px-3.5 py-2 rounded-xl transition-all duration-200 disabled:opacity-50 self-start sm:self-auto"
        >
          <BookmarkCheck className="w-4 h-4 text-brand-600" />
          {isSavingDefault ? 'Salvando...' : 'Salvar como meu Padrão'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* 1. Markup */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <Percent className="w-3.5 h-3.5 text-brand-600" />
              Markup sobre o Custo (%)
            </label>
            <span className="text-sm font-extrabold text-brand-700 font-mono">
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
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
          />
          <div className="flex items-center gap-2 pt-1">
            {[30, 50, 60, 80, 100].map((val) => (
              <button
                key={val}
                onClick={() => setMarkup(val)}
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border transition-colors ${
                  markup === val
                    ? 'bg-brand-600 text-white border-brand-600'
                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
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
            <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
              Custo Adicional por Unidade (R$)
            </label>
          </div>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
              R$
            </span>
            <input
              type="number"
              min="0"
              step="0.05"
              value={custoAdicional}
              onChange={(e) => setCustoAdicional(parseFloat(e.target.value) || 0)}
              placeholder="0.00"
              className="w-full pl-9 pr-3 py-2 text-sm font-semibold rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono"
            />
          </div>
          <p className="text-[11px] text-slate-400">
            Aplicado a cada unidade real de venda (embalagens, etiquetas, etc.)
          </p>
        </div>

        {/* 3. Impostos Considerados */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
              Impostos no Custo ({selectedTaxes.length} selecionados)
            </label>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {TODOS_IMPOSTOS.map((tax) => {
              const isSelected = selectedTaxes.includes(tax);
              return (
                <button
                  key={tax}
                  onClick={() => toggleTax(tax)}
                  type="button"
                  className={`text-xs font-bold px-2.5 py-1 rounded-lg border transition-all duration-150 flex items-center gap-1 ${
                    isSelected
                      ? 'bg-navy-800 text-white border-navy-800 shadow-sm'
                      : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100 hover:text-slate-700'
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
