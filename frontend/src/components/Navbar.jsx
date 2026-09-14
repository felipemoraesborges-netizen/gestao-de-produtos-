import React from 'react';
import {
  Package,
  BarChart3,
  FileText,
  User,
  LogOut,
  Sparkles,
  Building2,
  Boxes,
  ShieldCheck,
  FileSpreadsheet,
  AlertTriangle,
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, user, onLogout, alertaEstoqueCount = 0 }) {
  return (
    <header className="sticky top-0 z-40 bg-navy-900/95 backdrop-blur-md border-b border-white/10 shadow-lg text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-brand-500/20 text-white font-bold">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-brand-300 bg-clip-text text-transparent">
                  Gestão de Produtos
                </span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  PRO
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Estoque, Precificação & Auditoria</p>
            </div>
          </div>

          {/* Navigation Tabs (Desktop) */}
          <nav className="hidden lg:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10">
            <button
              onClick={() => setActiveTab('pricing')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'pricing'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Precificação
            </button>

            <button
              onClick={() => setActiveTab('inventory')}
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'inventory'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Boxes className="w-3.5 h-3.5" />
              Estoque
              {alertaEstoqueCount > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] font-black bg-amber-500 text-slate-900 animate-pulse">
                  {alertaEstoqueCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('reports')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'reports'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Relatórios & Análise
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'history'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Histórico NF-e
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'audit'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Auditoria
            </button>

            <button
              onClick={() => setActiveTab('profile')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'profile'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              Meu Perfil
            </button>
          </nav>

          {/* User Profile Badge & Logout */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('profile')}
              className="flex items-center gap-2.5 bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-xl border border-white/10 transition-all text-left group"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-sm">
                {user.nome ? user.nome.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="hidden sm:block">
                <div className="text-xs font-semibold text-white group-hover:text-brand-300 transition-colors">
                  {user.nome}
                </div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  <Building2 className="w-2.5 h-2.5" />
                  {user.empresa || 'Minha Empresa'}
                </div>
              </div>
            </button>

            <button
              onClick={onLogout}
              title="Sair do sistema"
              className="p-2 rounded-xl bg-white/5 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-white/10 hover:border-rose-500/30 transition-all"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

        </div>

        {/* Mobile Tab Bar */}
        <div className="flex lg:hidden items-center justify-between pb-3 gap-1 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveTab('pricing')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'pricing' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Precificação
          </button>
          <button
            onClick={() => setActiveTab('inventory')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap flex items-center gap-1 ${
              activeTab === 'inventory' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Estoque
            {alertaEstoqueCount > 0 && (
              <span className="px-1 rounded-full text-[9px] font-bold bg-amber-500 text-slate-900">
                {alertaEstoqueCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'reports' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Relatórios
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'history' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Histórico
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'audit' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Auditoria
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`py-1.5 px-2.5 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'profile' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Perfil
          </button>
        </div>
      </div>
    </header>
  );
}

