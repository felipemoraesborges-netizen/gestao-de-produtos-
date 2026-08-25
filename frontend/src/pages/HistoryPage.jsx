import React, { useState, useEffect } from 'react';
import { FileText, Search, Building2, Calendar, DollarSign, Layers, CheckCircle2, Download, AlertCircle } from 'lucide-react';
import { getInvoiceHistory } from '../services/api';

export default function HistoryPage({ user, showToast }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await getInvoiceHistory(user.id);
      setInvoices(data || []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [user.id]);

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
          <h1 className="text-2xl font-extrabold text-slate-800 flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-brand-600" />
            Histórico de Notas Fiscais
          </h1>
          <p className="text-sm text-slate-500 mt-1">
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
            className="pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 w-full sm:w-80 shadow-sm"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center font-bold">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase">Total de Notas</span>
            <div className="text-2xl font-extrabold text-slate-800">{invoices.length}</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase">Valor Total Faturado</span>
            <div className="text-2xl font-extrabold text-emerald-700">{formatBRL(totalValor)}</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase">Fornecedores Distintos</span>
            <div className="text-2xl font-extrabold text-indigo-700">{uniqueSuppliers}</div>
          </div>
        </div>
      </div>

      {/* Invoices List */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm font-semibold">Carregando notas fiscais...</p>
        </div>
      ) : filteredInvoices.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <h3 className="text-base font-bold text-slate-700 mb-1">Nenhuma nota fiscal encontrada</h3>
          <p className="text-xs text-slate-400">
            {searchTerm ? 'Nenhum resultado corresponde à sua pesquisa.' : 'Importe novos XMLs na aba de Precificação.'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
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
              <tbody className="divide-y divide-slate-100">
                {filteredInvoices.map((inv, idx) => (
                  <tr key={inv.chave_acesso || idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-800 text-sm">
                        Nº {inv.numero || 'S/N'}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Série {inv.serie || '1'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="font-bold text-slate-800 truncate">{inv.fornecedor}</div>
                      <div className="text-[10px] text-slate-400 font-mono truncate">
                        Chave: {inv.chave_acesso}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {inv.cnpj_emit || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-medium">
                      {inv.data_emissao || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-extrabold text-brand-700 text-sm">
                      {formatBRL(inv.valor_total)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 font-medium">
                      {inv.data_importacao || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 font-mono truncate max-w-[150px]">
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
