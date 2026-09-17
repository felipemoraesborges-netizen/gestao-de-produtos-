import React, { useState, useEffect, useCallback } from 'react';
import { FileText, Search, Building2, DollarSign } from 'lucide-react';
import { getInvoiceHistory } from '../services/api';

export default function HistoryPage({ user, showToast }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getInvoiceHistory(user.id);
      setInvoices(data || []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [user.id, showToast]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const formatBRL = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
  };

  const filteredInvoices = invoices.filter((inv) => {
    const term = searchTerm.toLowerCase();
    return (
      (inv.numero || '').toLowerCase().includes(term) ||
      (inv.fornecedor || '').toLowerCase().includes(term) ||
      (inv.cnpj_emit || '').toLowerCase().includes(term) ||
      (inv.chave_acesso || '').toLowerCase().includes(term)
    );
  });

  const totalValor = invoices.reduce((acc, inv) => acc + (inv.valor_total || 0), 0);
  const uniqueSuppliers = new Set(invoices.map((inv) => inv.fornecedor)).size;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-brand-600" />
            Histórico de Notas Fiscais
          </h1>
          <p className="text-sm text-slate-500 dark:text-zinc-400 mt-1">
            Consulte todas as notas fiscais processadas e vinculadas à sua conta.
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por número, fornecedor ou CNPJ..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2.5 bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 w-full sm:w-80 shadow-sm text-slate-700 dark:text-zinc-200 placeholder:text-slate-400 dark:placeholder:text-zinc-500"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-zinc-900 p-5 rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wider">Total de Notas</span>
            <div className="text-2xl font-extrabold tabular-nums text-slate-800 dark:text-white">{invoices.length}</div>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 p-5 rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wider">Valor Total Faturado</span>
            <div className="text-2xl font-extrabold tabular-nums text-emerald-700 dark:text-emerald-400">{formatBRL(totalValor)}</div>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 p-5 rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wider">Fornecedores Distintos</span>
            <div className="text-2xl font-extrabold tabular-nums text-indigo-700 dark:text-indigo-400">{uniqueSuppliers}</div>
          </div>
        </div>
      </div>

      {/* Invoices List */}
      {loading ? (
        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200 dark:border-zinc-800 p-12 text-center text-slate-400">
          <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm font-semibold dark:text-zinc-400">Carregando notas fiscais...</p>
        </div>
      ) : filteredInvoices.length === 0 ? (
        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200 dark:border-zinc-800 p-12 text-center">
          <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300 dark:text-zinc-600" />
          <h3 className="text-base font-bold text-slate-700 dark:text-zinc-300 mb-1">Nenhuma nota fiscal encontrada</h3>
          <p className="text-xs text-slate-400 dark:text-zinc-500">
            {searchTerm ? 'Nenhum resultado corresponde à sua pesquisa.' : 'Importe novos XMLs na aba de Precificação.'}
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-zinc-800/70 text-slate-600 dark:text-zinc-400 font-bold border-b border-slate-200 dark:border-zinc-700">
                <tr>
                  <th className="py-3.5 px-4">NF-e / Série</th>
                  <th className="py-3.5 px-4">Fornecedor / Emitente</th>
                  <th className="py-3.5 px-4">CNPJ</th>
                  <th className="py-3.5 px-4">Emissão</th>
                  <th className="py-3.5 px-4 text-right">Valor Total</th>
                  <th className="py-3.5 px-4">Importado Em</th>
                  <th className="py-3.5 px-4">Arquivo Original</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                {filteredInvoices.map((inv, idx) => (
                  <tr key={inv.chave_acesso || idx} className="hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-800 dark:text-zinc-100 text-sm">
                        Nº {inv.numero || 'S/N'}
                      </div>
                      <div className="text-[11px] text-slate-400 dark:text-zinc-500 font-mono">
                        Série {inv.serie || '1'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="font-bold text-slate-800 dark:text-zinc-100 truncate">{inv.fornecedor}</div>
                      <div className="text-[10px] text-slate-400 dark:text-zinc-500 font-mono truncate">
                        Chave: {inv.chave_acesso}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-zinc-400">
                      {inv.cnpj_emit || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 dark:text-zinc-400 font-medium">
                      {inv.data_emissao || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-extrabold tabular-nums text-brand-700 dark:text-brand-400 text-sm">
                      {formatBRL(inv.valor_total)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-zinc-400 font-medium">
                      {inv.data_importacao || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-zinc-500 font-mono truncate max-w-[150px]">
                      {inv.arquivo_original || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
