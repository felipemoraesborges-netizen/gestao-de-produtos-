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
    if (!nome || !usuario || !email || !senhaCad) {
      showToast('Por favor, preencha todos os campos obrigatórios (*).', 'error');
      return;
    }
    if (senhaCad.length < 6) {
      showToast('A senha deve conter no mínimo 6 caracteres.', 'error');
      return;
    }
    if (senhaCad !== senhaConf) {
      showToast('A confirmação de senha não confere.', 'error');
      return;
    }

    try {
      setLoading(true);
      const res = await registerUser({
        nome,
        usuario,
        email,
        senha: senhaCad,
        empresa,
        cargo,
      });
      showToast('Conta criada com sucesso! Faça login para continuar.', 'success');
      setIsLogin(true);
      setIdentificador(usuario);
      setSenha(senhaCad);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell min-h-screen flex flex-col justify-center py-10 px-4 relative overflow-hidden">
      
      {/* Background glowing orbs */}
      <div className="auth-orb auth-orb-primary pointer-events-none" />
      <div className="auth-orb auth-orb-secondary pointer-events-none" />

      {/* Header Logo */}
      <div className="auth-heading z-10">
        <div className="auth-logo">
          <Package className="w-7 h-7" strokeWidth={2.2} />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Gestão de Produtos
        </h1>
        <p className="auth-subtitle">
          Precificação Automática de NF-e, Rateio de Custos & Formação de Margens
        </p>
      </div>

      {/* Auth Card */}
      <div className="auth-card-wrap z-10">
        <div className="auth-card">
          
          {/* Switcher Tab */}
          <div className="auth-tabs">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                isLogin
                  ?                   'auth-tab-active'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Entrar na Conta
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                !isLogin
                  ?                   'auth-tab-active'
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
                    className="auth-input w-full pl-10 pr-4 py-2.5 text-sm text-white transition-all"
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
                    className="auth-input w-full pl-10 pr-4 py-2.5 text-sm text-white transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="auth-submit w-full py-3 mt-2 text-white font-bold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
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
                  className="auth-input w-full px-3.5 py-2 text-sm text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Nome de Usuário *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="ex: felipe"
                    value={usuario}
                    onChange={(e) => setUsuario(e.target.value)}
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    E-mail *
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="felipe@empresa.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
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
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
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
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
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
                    placeholder="Mínimo 6 dígitos"
                    value={senhaCad}
                    onChange={(e) => setSenhaCad(e.target.value)}
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
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
                    className="auth-input w-full px-3.5 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="auth-submit w-full py-3 mt-3 text-white font-bold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? 'Cadastrando...' : 'Criar Minha Conta'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Security footnote */}
          <div className="auth-security mt-6 pt-4 flex items-center justify-center gap-1.5 text-[11px]">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>Autenticação criptografada com PBKDF2-HMAC-SHA256</span>
          </div>

        </div>
      </div>
    </div>
  );
}
