import React, { useState } from 'react';
import { User, Building2, Briefcase, Mail, Sliders, ShieldCheck, Lock, BookmarkCheck, Check, KeyRound } from 'lucide-react';
import { updateUserProfile, changeUserPassword } from '../services/api';

const TODOS_IMPOSTOS = ['ICMS', 'ICMS ST', 'FCP', 'FCP ST', 'IPI', 'II', 'PIS', 'COFINS'];

export default function ProfilePage({ user, onUserUpdated, showToast }) {
  // Form de Dados Cadastrais & Preferências
  const [nome, setNome] = useState(user.nome || '');
  const [email, setEmail] = useState(user.email || '');
  const [empresa, setEmpresa] = useState(user.empresa || '');
  const [cargo, setCargo] = useState(user.cargo || '');
  const [markupPadrao, setMarkupPadrao] = useState(user.markup_padrao ?? 60.0);
  const [custoAdicionalPadrao, setCustoAdicionalPadrao] = useState(user.custo_adicional_padrao ?? 0.0);
  const [impostosPadrao, setImpostosPadrao] = useState(user.impostos_padrao || ['ICMS ST', 'FCP ST', 'IPI', 'II']);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Form de Troca de Senha
  const [senhaAtual, setSenhaAtual] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmaNovaSenha, setConfirmaNovaSenha] = useState('');
  const [loadingPassword, setLoadingPassword] = useState(false);

  const toggleTax = (tax) => {
    if (impostosPadrao.includes(tax)) {
      setImpostosPadrao(impostosPadrao.filter((t) => t !== tax));
    } else {
      setImpostosPadrao([...impostosPadrao, tax]);
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!nome || !email) {
      showToast('Nome e e-mail são obrigatórios.', 'error');
      return;
    }
    try {
      setLoadingProfile(true);
      const res = await updateUserProfile({
        usuario_id: user.id,
        nome,
        email,
        empresa,
        cargo,
        markup_padrao: parseFloat(markupPadrao) || 0,
        custo_adicional_padrao: parseFloat(custoAdicionalPadrao) || 0,
        impostos_padrao: impostosPadrao,
      });
      showToast(res.message || 'Perfil e preferências atualizados com sucesso!', 'success');
      onUserUpdated(res.user);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!senhaAtual || !novaSenha) {
      showToast('Preencha a senha atual e a nova senha.', 'error');
      return;
    }
    if (novaSenha.length < 6) {
      showToast('A nova senha deve ter no mínimo 6 caracteres.', 'error');
      return;
    }
    if (novaSenha !== confirmaNovaSenha) {
      showToast('A nova senha e a confirmação não coincidem.', 'error');
      return;
    }

    try {
      setLoadingPassword(true);
      const res = await changeUserPassword({
        usuario_id: user.id,
        senha_atual: senhaAtual,
        nova_senha: novaSenha,
      });
      showToast(res.message || 'Senha alterada com sucesso!', 'success');
      setSenhaAtual('');
      setNovaSenha('');
      setConfirmaNovaSenha('');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingPassword(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-slate-800 flex items-center gap-2.5">
          <User className="w-7 h-7 text-brand-600" />
          Meu Perfil & Preferências Padrão
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Personalize seus dados de cadastro e defina os parâmetros padrão que serão carregados em todas as suas sessões.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: User Card & Avatar */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 text-center">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-brand-600 via-brand-500 to-cyan-400 flex items-center justify-center text-white text-2xl font-extrabold shadow-xl shadow-brand-500/20 mx-auto mb-4 border-2 border-white">
              {user.nome ? user.nome.charAt(0).toUpperCase() : 'U'}
            </div>
            <h2 className="text-lg font-bold text-slate-800">{user.nome}</h2>
            <p className="text-xs text-brand-600 font-semibold font-mono">@{user.usuario}</p>
            <p className="text-xs text-slate-400 mt-1">{user.cargo || 'Gestor'} • {user.empresa || 'Empresa'}</p>
            <span className="inline-flex mt-3 rounded-full bg-brand-50 border border-brand-100 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-brand-700">
              Nível: {user.nivel_acesso || 'operador'}
            </span>

            <div className="mt-6 pt-4 border-t border-slate-100 text-left text-xs space-y-2">
              <div className="flex justify-between text-slate-500">
                <span>Membro desde:</span>
                <span className="font-semibold text-slate-700">{user.criado_em || '-'}</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Último login:</span>
                <span className="font-semibold text-slate-700">{user.ultimo_login || '-'}</span>
              </div>
            </div>
          </div>

          {/* Quick Info Box */}
          <div className="bg-gradient-to-br from-brand-50 to-cyan-50/50 rounded-2xl border border-brand-100 p-5 text-xs text-slate-600">
            <div className="flex items-center gap-2 font-bold text-brand-900 mb-1.5">
              <BookmarkCheck className="w-4 h-4 text-brand-600" />
              Preferências Automáticas
            </div>
            <p className="leading-relaxed text-slate-600">
              Ao salvar suas preferências aqui, sempre que você importar XMLs na aba de Precificação, o markup de <b>{markupPadrao}%</b> e os impostos selecionados já virão ativados automaticamente.
            </p>
          </div>
        </div>

        {/* Right Column: Forms */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Form 1: Dados & Preferências */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4 pb-3 border-b border-slate-100 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-brand-600" />
              Dados Cadastrais & Preferências de Precificação
            </h3>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Nome Completo *</label>
                  <input
                    type="text"
                    required
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">E-mail *</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Empresa</label>
                  <input
                    type="text"
                    value={empresa}
                    onChange={(e) => setEmpresa(e.target.value)}
                    placeholder="Nome da sua empresa"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Cargo / Função</label>
                  <input
                    type="text"
                    value={cargo}
                    onChange={(e) => setCargo(e.target.value)}
                    placeholder="Seu cargo na empresa"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Preferências Padrão */}
              <div className="pt-4 border-t border-slate-100">
                <h4 className="text-xs font-extrabold text-brand-900 uppercase tracking-wider mb-3">
                  Configurações Padrão de Precificação
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Markup Padrão (%)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={markupPadrao}
                      onChange={(e) => setMarkupPadrao(parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-mono font-bold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Custo Adicional Padrão (R$)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={custoAdicionalPadrao}
                      onChange={(e) => setCustoAdicionalPadrao(parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-mono font-bold focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-2">Impostos Padrão Incluídos no Custo</label>
                  <div className="flex flex-wrap gap-1.5">
                    {TODOS_IMPOSTOS.map((tax) => {
                      const isSelected = impostosPadrao.includes(tax);
                      return (
                        <button
                          key={tax}
                          type="button"
                          onClick={() => toggleTax(tax)}
                          className={`text-xs font-bold px-3 py-1.5 rounded-lg border transition-all duration-150 flex items-center gap-1.5 ${
                            isSelected
                              ? 'bg-navy-800 text-white border-navy-800 shadow-sm'
                              : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100 hover:text-slate-700'
                          }`}
                        >
                          {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                          {tax}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="pt-3 flex justify-end">
                <button
                  type="submit"
                  disabled={loadingProfile}
                  className="bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md shadow-brand-500/20 transition-all duration-200 disabled:opacity-50"
                >
                  {loadingProfile ? 'Salvando...' : 'Salvar Alterações do Perfil'}
                </button>
              </div>
            </form>
          </div>

          {/* Form 2: Alteração de Senha */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4 pb-3 border-b border-slate-100 flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-amber-600" />
              Segurança & Troca de Senha
            </h3>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Senha Atual *</label>
                <input
                  type="password"
                  required
                  placeholder="Sua senha atual"
                  value={senhaAtual}
                  onChange={(e) => setSenhaAtual(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Nova Senha (mín. 6 dígitos) *</label>
                  <input
                    type="password"
                    required
                    placeholder="Nova senha"
                    value={novaSenha}
                    onChange={(e) => setNovaSenha(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Confirmar Nova Senha *</label>
                  <input
                    type="password"
                    required
                    placeholder="Repita a nova senha"
                    value={confirmaNovaSenha}
                    onChange={(e) => setConfirmaNovaSenha(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={loadingPassword}
                  className="bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all duration-200 disabled:opacity-50"
                >
                  {loadingPassword ? 'Atualizando...' : 'Atualizar Senha'}
                </button>
              </div>
            </form>
          </div>

        </div>

      </div>

    </div>
  );
}
