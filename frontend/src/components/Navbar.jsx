import React from 'react';
import { Package, BarChart3, FileText, User, LogOut, Sparkles, Building2 } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, user, onLogout }) {
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
              <p className="text-[11px] text-slate-400 font-medium">Precificação Inteligente & NF-e</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10">
            <button
              onClick={() => setActiveTab('pricing')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'pricing'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Precificação
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'dashboard'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === 'history'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Histórico de NF-e
            </button>
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
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
        <div className="flex md:hidden items-center justify-between pb-3 gap-1 overflow-x-auto">
          <button
            onClick={() => setActiveTab('pricing')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium text-center ${
              activeTab === 'pricing' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Precificação
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium text-center ${
              activeTab === 'dashboard' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium text-center ${
              activeTab === 'history' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Histórico
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium text-center ${
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
