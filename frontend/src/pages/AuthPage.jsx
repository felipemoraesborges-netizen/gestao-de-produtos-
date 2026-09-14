import React, { useState } from 'react';
import { Package, Lock, User, Mail, Building2, Briefcase, ArrowRight, Sparkles, CheckCircle2, Shield } from 'lucide-react';
import { loginUser, registerUser } from '../services/api';

export default function AuthPage({ onLoginSuccess, showToast }) {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);

  // Form states
  const [identificador, setIdentificador] = useState('');
  const [senha, setSenha] = useState('');

  const [nome, setNome] = useState('');
  const [usuario, setUsuario] = useState('');
  const [email, setEmail] = useState('');
  const [empresa, setEmpresa] = useState('');
  const [cargo, setCargo] = useState('');
  const [senhaCad, setSenhaCad] = useState('');
  const [senhaConf, setSenhaConf] = useState('');

  // Password criteria
  const hasMinLen = senhaCad.length >= 10;
  const hasUpper = /[A-Z]/.test(senhaCad);
  const hasLower = /[a-z]/.test(senhaCad);
  const hasNumber = /[0-9]/.test(senhaCad);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(senhaCad);
  const isSenhaForte = hasMinLen && hasUpper && hasLower && hasNumber && hasSpecial;

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!identificador || !senha) {
      showToast('Preencha seu usuário/e-mail e senha.', 'error');
      return;
    }
    try {
      setLoading(true);
      const user = await loginUser(identificador, senha);
      showToast(`Bem-vindo de volta, ${user.nome}!`, 'success');
      onLoginSuccess(user);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const cleanUser = usuario.trim().toLowerCase();
    if (!nome || !cleanUser || !email || !senhaCad) {
      showToast('Por favor, preencha todos os campos obrigatórios (*).', 'error');
      return;
    }
    if (!/^[a-zA-Z0-9_\.\-]+$/.test(cleanUser)) {
      showToast('Nome de usuário inválido. Não utilize espaços, acentos ou símbolos como @.', 'error');
      return;
    }
    if (!isSenhaForte) {
      showToast('A senha precisa cumprir todos os requisitos: 10+ caracteres, maiúscula, minúscula, número e caractere especial (@, #, $...).', 'error');
      return;
    }
    if (senhaCad !== senhaConf) {
      showToast('A confirmação de senha não confere.', 'error');
      return;
    }

    try {
      setLoading(true);
      const res = await registerUser({
        nome: nome.trim(),
        usuario: cleanUser,
        email: email.trim().toLowerCase(),
        senha: senhaCad,
        empresa: empresa.trim(),
        cargo: cargo.trim(),
      });
      showToast('Conta criada com sucesso! Faça login para continuar.', 'success');
      setIsLogin(true);
      setIdentificador(cleanUser);
      setSenha(senhaCad);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-navy-900 to-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      
      {/* Background glowing orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header Logo */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center z-10">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 via-brand-500 to-cyan-400 flex items-center justify-center shadow-xl shadow-brand-500/25 text-white mx-auto mb-4 border border-white/20">
          <Package className="w-8 h-8" />
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Gestão de Produtos
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Precificação Automática de NF-e, Rateio de Custos & Formação de Margens
        </p>
      </div>

      {/* Auth Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0 z-10">
        <div className="bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
          
          {/* Switcher Tab */}
          <div className="flex bg-white/5 p-1 rounded-2xl border border-white/10 mb-6">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                isLogin
                  ? 'bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Entrar na Conta
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                !isLogin
                  ? 'bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Criar Nova Conta
            </button>
          </div>

          {/* Login Form */}
          {isLogin ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Usuário ou E-mail
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    placeholder="Seu usuário ou e-mail"
                    value={identificador}
                    onChange={(e) => setIdentificador(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Senha
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 mt-2 bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white font-bold rounded-xl shadow-lg shadow-brand-500/25 transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? 'Entrando...' : 'Acessar o Sistema'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          ) : (
            /* Register Form */
            <form onSubmit={handleRegister} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Nome Completo *
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: Felipe Moraes"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-semibold text-slate-300">
                      Nome de Usuário *
                    </label>
                  </div>
                  <input
                    type="text"
                    required
                    placeholder="ex: felipe.moraes"
                    value={usuario}
                    onChange={(e) => setUsuario(e.target.value.toLowerCase().replace(/\s+/g, ''))}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <span className="text-[10px] text-slate-400 block mt-0.5">Sem espaços ou acentos</span>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    E-mail *
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="seu.email@empresa.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Empresa (Opcional)
                  </label>
                  <input
                    type="text"
                    placeholder="Nome da empresa"
                    value={empresa}
                    onChange={(e) => setEmpresa(e.target.value)}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Cargo / Função
                  </label>
                  <input
                    type="text"
                    placeholder="ex: Gestor de Compras"
                    value={cargo}
                    onChange={(e) => setCargo(e.target.value)}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Senha *
                  </label>
                  <input
                    type="password"
                    required
                    placeholder="Ex: Minha@Senha2026"
                    value={senhaCad}
                    onChange={(e) => setSenhaCad(e.target.value)}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Confirmar Senha *
                  </label>
                  <input
                    type="password"
                    required
                    placeholder="Repita a senha"
                    value={senhaConf}
                    onChange={(e) => setSenhaConf(e.target.value)}
                    className="w-full px-3.5 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              {/* Checklist de requisitos de segurança */}
              {senhaCad && (
                <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-xs space-y-1">
                  <div className="font-semibold text-slate-300 mb-1 flex items-center justify-between">
                    <span>Requisitos da Senha:</span>
                    {senhaConf && (
                      <span className={senhaCad === senhaConf ? "text-emerald-400 font-semibold" : "text-amber-400"}>
                        {senhaCad === senhaConf ? "✓ Senhas conferem" : "✗ Senhas diferentes"}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[11px]">
                    <span className={hasMinLen ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {hasMinLen ? "✓" : "○"} 10+ caracteres
                    </span>
                    <span className={hasUpper ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {hasUpper ? "✓" : "○"} Letra maiúscula (A-Z)
                    </span>
                    <span className={hasLower ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {hasLower ? "✓" : "○"} Letra minúscula (a-z)
                    </span>
                    <span className={hasNumber ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {hasNumber ? "✓" : "○"} Número (0-9)
                    </span>
                    <span className={hasSpecial ? "text-emerald-400 font-medium col-span-2" : "text-slate-400 col-span-2"}>
                      {hasSpecial ? "✓" : "○"} Símbolo (@, #, $, %, !, *, etc.)
                    </span>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 mt-3 bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white font-bold rounded-xl shadow-lg shadow-brand-500/25 transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? 'Cadastrando...' : 'Criar Minha Conta'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Security footnote */}
          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>Autenticação criptografada com Argon2id & JWT</span>
          </div>

        </div>
      </div>
    </div>
  );
}
