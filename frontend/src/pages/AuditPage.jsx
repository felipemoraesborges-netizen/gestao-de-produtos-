import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Search,
  Download,
  RotateCcw,
  User,
  Clock,
  Globe,
  Filter,
  Activity,
  FileText,
  Boxes,
  Lock,
  ArrowRightLeft,
  X,
  FileSpreadsheet,
} from 'lucide-react';
import { getAuditoriaLogs, downloadAuditoriaCsv } from '../services/api';

export default function AuditPage({ user, showToast }) {
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [filtroAcao, setFiltroAcao] = useState('TODAS');
  const [busca, setBusca] = useState('');
  const [limite, setLimite] = useState(100);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await getAuditoriaLogs(user?.id, filtroAcao, busca, limite);
      setLogs(res.logs || []);
      setTotal(res.total || 0);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [user, filtroAcao, busca, limite]);

  const handleExportCsv = async () => {
    try {
      await downloadAuditoriaCsv(user?.id, filtroAcao, busca);
      showToast('Trilha de auditoria exportada em CSV com sucesso!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Helper para estilizar badges de acordo com a categoria de ação
  const getActionBadge = (acao) => {
    const act = (acao || '').toUpperCase();

    if (act.includes('LOGIN_SUCESSO') || act.includes('CADASTRO_SUCESSO')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Lock className="w-3 h-3" />
          Acesso Seguro
        </span>
      );
    }
    if (act.includes('LOGIN_FALHA') || act.includes('CADASTRO_FALHA')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <Lock className="w-3 h-3" />
          Falha de Acesso
        </span>
      );
    }
    if (act.includes('IMPORTACAO_NFE')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
          <FileText className="w-3 h-3" />
          NF-e Importada
        </span>
      );
    }
    if (act.includes('INCORPORACAO_ESTOQUE')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-brand-50 text-brand-700 border border-brand-200">
          <Boxes className="w-3 h-3" />
          Estoque NF-e
        </span>
      );
    }
    if (act.includes('MOVIMENTACAO_ENTRADA') || act.includes('CADASTRO_ESTOQUE')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Boxes className="w-3 h-3" />
          Entrada Estoque
        </span>
      );
    }
    if (act.includes('MOVIMENTACAO_SAIDA') || act.includes('EXCLUSAO')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <Boxes className="w-3 h-3" />
          Saída / Exclusão
        </span>
      );
    }
    if (act.includes('MOVIMENTACAO_AJUSTE') || act.includes('EDICAO')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
          <ArrowRightLeft className="w-3 h-3" />
          Ajuste de Saldo
        </span>
      );
    }
    if (act.includes('EXPORTACAO')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-cyan-50 text-cyan-700 border border-cyan-200">
          <FileSpreadsheet className="w-3 h-3" />
          Exportação
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
        <Activity className="w-3 h-3" />
        {acao}
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Header com Título e Ação de Exportar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-800">
              🛡️ Trilha de Auditoria & Compliance
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
              Imutável
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Monitoramento detalhado e rastreabilidade de todas as atividades executadas por usuários no sistema.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchLogs}
            title="Atualizar Registros"
            className="p-2.5 bg-white border border-slate-200 hover:border-slate-300 text-slate-600 rounded-xl transition-all shadow-sm"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold transition-all shadow shadow-brand-500/20"
          >
            <Download className="w-4 h-4" />
            Exportar Logs (CSV)
          </button>
        </div>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        
        {/* Pílulas de filtro por tipo de ação */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs">
          {[
            { id: 'TODAS', label: 'Todas' },
            { id: 'LOGIN', label: 'Acessos' },
            { id: 'IMPORTACAO_NFE', label: 'NF-e' },
            { id: 'ESTOQUE', label: 'Estoque' },
            { id: 'MOVIMENTACAO', label: 'Movimentações' },
            { id: 'EXPORTACAO', label: 'Exportações' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setFiltroAcao(cat.id)}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all whitespace-nowrap ${
                filtroAcao === cat.id
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Input de Busca */}
        <div className="relative min-w-[280px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Pesquisar por usuário, ação ou detalhe..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full pl-9 pr-8 py-1.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-xl text-xs text-slate-700 outline-none transition-all"
          />
          {busca && (
            <button
              onClick={() => setBusca('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

      </div>

      {/* Tabela de Trilha de Auditoria */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-slate-400">
            <RotateCcw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-600" />
            <p className="text-sm font-medium">Carregando trilha de auditoria...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center px-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-800">Nenhum registro de auditoria encontrado</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Não há eventos cadastrados correspondentes aos filtros selecionados.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Data / Hora</th>
                  <th className="py-3.5 px-4">Usuário</th>
                  <th className="py-3.5 px-4">Categoria / Ação</th>
                  <th className="py-3.5 px-4">Detalhes da Operação</th>
                  <th className="py-3.5 px-4 text-right">Endereço IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    
                    {/* Timestamp */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-slate-700 font-mono font-medium">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {log.data_hora}
                      </div>
                    </td>

                    {/* Usuário */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">
                          {log.usuario_nome ? log.usuario_nome.charAt(0).toUpperCase() : 'U'}
                        </div>
                        <span className="font-bold text-slate-800">
                          {log.usuario_nome || 'Sistema'}
                        </span>
                      </div>
                    </td>

                    {/* Badge de Ação */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {getActionBadge(log.acao)}
                    </td>

                    {/* Detalhes */}
                    <td className="py-3.5 px-4 text-slate-600 font-normal">
                      <div className="max-w-xl break-words">
                        {log.detalhes}
                      </div>
                    </td>

                    {/* IP */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap text-slate-400 font-mono text-[11px]">
                      <span className="inline-flex items-center gap-1">
                        <Globe className="w-3 h-3 text-slate-400" />
                        {log.ip || '127.0.0.1'}
                      </span>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Rodapé da tabela com totalizadores */}
        <div className="bg-slate-50 px-4 py-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>
            Exibindo <strong>{logs.length}</strong> de <strong>{total}</strong> registro(s) auditados
          </span>
          {total > limite && (
            <button
              onClick={() => setLimite((prev) => prev + 100)}
              className="px-3 py-1 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 rounded-lg font-semibold text-xs transition-all shadow-sm"
            >
              Carregar Mais (+100)
            </button>
          )}
        </div>

      </div>

    </div>
  );
}
