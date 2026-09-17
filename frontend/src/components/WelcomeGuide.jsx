import React from 'react';
import { Sparkles, UploadCloud, Sliders, Boxes, ArrowRight, X, HelpCircle, FileSpreadsheet } from 'lucide-react';

export default function WelcomeGuide({ onLoadDemo, onDismiss }) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-900/90 via-navy-900 to-slate-900 dark:from-zinc-900 dark:via-zinc-950 dark:to-black text-white p-6 sm:p-7 border border-brand-500/20 dark:border-zinc-800 shadow-xl mb-6">
      {/* Decorative Glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/15 dark:bg-brand-600/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
      <div className="absolute bottom-0 left-1/3 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Dismiss button */}
      {onDismiss && (
        <button
          onClick={onDismiss}
          title="Ocultar guia"
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-500 to-cyan-400 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold tracking-tight text-white">
                Como Funciona a Precificação Inteligente
              </h2>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-500/25 text-brand-300 border border-brand-400/30 uppercase tracking-wider">
                Guia Rápido
              </span>
            </div>
            <p className="text-xs text-slate-300 dark:text-slate-400 mt-0.5">
              Descubra seu custo real por unidade e forme preços lucrativos em 3 passos simples.
            </p>
          </div>
        </div>

        {/* Action Button: Load Demo */}
        {onLoadDemo && (
          <button
            onClick={onLoadDemo}
            className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-slate-950 dark:text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-emerald-500/20 transition-all btn-press shrink-0"
          >
            <Sparkles className="w-4 h-4 text-slate-900" />
            Carregar Exemplo de Demonstração
          </button>
        )}
      </div>

      {/* 3 Steps */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
        
        {/* Step 1 */}
        <div className="bg-white/5 dark:bg-white/[0.03] backdrop-blur-sm rounded-xl p-4 border border-white/10 dark:border-white/5 hover:border-brand-500/40 transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-lg bg-brand-500/20 text-brand-300 flex items-center justify-center text-xs font-bold font-mono">
              1
            </div>
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <UploadCloud className="w-3.5 h-3.5 text-brand-400" />
              Importe seus XMLs
            </h3>
          </div>
          <p className="text-[11px] text-slate-300 dark:text-slate-400 leading-relaxed">
            Arraste um ou mais arquivos XML de NF-e. O sistema lê produtos, alíquotas de ICMS, ST, IPI, PIS, COFINS e frete automaticamente.
          </p>
        </div>

        {/* Step 2 */}
        <div className="bg-white/5 dark:bg-white/[0.03] backdrop-blur-sm rounded-xl p-4 border border-white/10 dark:border-white/5 hover:border-brand-500/40 transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-xs font-bold font-mono">
              2
            </div>
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              Fardos, Caixas & Margem
            </h3>
          </div>
          <p className="text-[11px] text-slate-300 dark:text-slate-400 leading-relaxed">
            Se comprou uma caixa com 12 ou 24 unidades, basta alterar as <strong>Unidades por Embalagem</strong>. O custo unitário real é recalculado na hora.
          </p>
        </div>

        {/* Step 3 */}
        <div className="bg-white/5 dark:bg-white/[0.03] backdrop-blur-sm rounded-xl p-4 border border-white/10 dark:border-white/5 hover:border-brand-500/40 transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center text-xs font-bold font-mono">
              3
            </div>
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Boxes className="w-3.5 h-3.5 text-emerald-400" />
              Estoque & Exportação
            </h3>
          </div>
          <p className="text-[11px] text-slate-300 dark:text-slate-400 leading-relaxed">
            Com 1 clique no botão <strong>Incorporar ao Estoque</strong>, seu catálogo permanente é abastecido. Ou exporte para planilha CSV/Excel.
          </p>
        </div>

      </div>
    </div>
  );
}
