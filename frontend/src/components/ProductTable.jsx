import React, { useState } from 'react';
import {
  Search,
  Download,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  FileSpreadsheet,
  Package,
  Layers,
  Info,
} from 'lucide-react';

export default function ProductTable({
  produtos,
  unidadesPorEmbalagem,
  onUpdateUnidade,
  onExportCsv,
  onIncorporarEstoque,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('produto');
  const [sortAsc, setSortAsc] = useState(true);
  const [expandedRow, setExpandedRow] = useState(null);

  const formatBRL = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  // Filtragem por busca
  const filteredProducts = produtos.filter((p) => {
    const term = searchTerm.toLowerCase();
    return (
      (p.codigo || '').toLowerCase().includes(term) ||
      (p.produto || '').toLowerCase().includes(term) ||
      (p.fornecedor || '').toLowerCase().includes(term) ||
      (p.arquivo_xml || '').toLowerCase().includes(term)
    );
  });

  // Ordenação
  const sortedProducts = [...filteredProducts].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (typeof valA === 'string') {
      valA = valA.toLowerCase();
      valB = (valB || '').toLowerCase();
    }

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
      {/* Table Header Controls */}
      <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <Package className="w-5 h-5 text-brand-600" />
            Produtos Processados ({produtos.length})
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Ajuste as unidades por embalagem para recálculo instantâneo de custo real e preço de revenda.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por código ou descrição..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 w-48 sm:w-56 transition-all"
            />
          </div>

          {/* Incorporar ao Estoque */}
          {onIncorporarEstoque && (
            <button
              onClick={onIncorporarEstoque}
              className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-700 hover:to-indigo-700 text-white text-xs font-bold px-3.5 py-2 rounded-xl shadow-md shadow-brand-500/20 transition-all duration-200"
            >
              <Package className="w-4 h-4" />
              Incorporar ao Estoque
            </button>
          )}

          {/* Export Button */}
          <button
            onClick={onExportCsv}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-3.5 py-2 rounded-xl shadow-sm transition-all duration-200"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
            <tr>
              <th className="py-3 px-4 w-8"></th>
              <th
                onClick={() => handleSort('codigo')}
                className="py-3 px-4 cursor-pointer hover:text-brand-600 transition-colors"
              >
                <div className="flex items-center gap-1">
                  Código <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort('produto')}
                className="py-3 px-4 cursor-pointer hover:text-brand-600 transition-colors"
              >
                <div className="flex items-center gap-1">
                  Descrição do Produto <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3 px-4 text-center">Un. Orig.</th>
              <th className="py-3 px-4 text-center bg-brand-50/50 text-brand-900">
                Unid. / Emb.
              </th>
              <th className="py-3 px-4 text-right">Qtd Real</th>
              <th
                onClick={() => handleSort('custo_unitario_final')}
                className="py-3 px-4 text-right cursor-pointer hover:text-brand-600 transition-colors"
              >
                <div className="flex items-center justify-end gap-1">
                  Custo Unit. Final <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort('preco_revenda_unitario')}
                className="py-3 px-4 text-right cursor-pointer hover:text-brand-600 transition-colors bg-blue-50/30 font-extrabold text-brand-800"
              >
                <div className="flex items-center justify-end gap-1">
                  Preço Sugerido <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort('lucro_total')}
                className="py-3 px-4 text-right cursor-pointer hover:text-brand-600 transition-colors text-emerald-700 font-bold"
              >
                <div className="flex items-center justify-end gap-1">
                  Lucro Total <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {sortedProducts.map((p, index) => {
              const isExpanded = expandedRow === p.id;
              const currentUnidade = unidadesPorEmbalagem[p.id] ?? p.unidades_por_embalagem ?? 1.0;

              return (
                <React.Fragment key={p.id || index}>
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    {/* Expand/Collapse */}
                    <td className="py-3 px-3 text-center">
                      <button
                        onClick={() => setExpandedRow(isExpanded ? null : p.id)}
                        className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors"
                        title="Ver detalhes de impostos e frete"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </td>

                    {/* Código */}
                    <td className="py-3 px-4 font-mono font-semibold text-slate-600">
                      {p.codigo}
                    </td>

                    {/* Descrição */}
                    <td className="py-3 px-4 max-w-xs sm:max-w-md">
                      <div className="font-bold text-slate-800 line-clamp-1">{p.produto}</div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span>NF-e: {p.numero_nota || 'S/N'}</span>
                        <span>•</span>
                        <span className="truncate max-w-[200px]">{p.fornecedor}</span>
                      </div>
                    </td>

                    {/* Unidade Original */}
                    <td className="py-3 px-4 text-center">
                      <span className="bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded text-[11px]">
                        {p.unidade} ({p.quantidade})
                      </span>
                    </td>

                    {/* Unidades por Embalagem (EDITÁVEL INLINE) */}
                    <td className="py-3 px-4 text-center bg-brand-50/30">
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={currentUnidade}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value) || 1;
                          onUpdateUnidade(p.id, val);
                        }}
                        className="w-16 text-center font-bold text-xs py-1 px-1.5 rounded-lg border border-brand-300 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 text-brand-900 font-mono shadow-inner"
                      />
                    </td>

                    {/* Quantidade Real */}
                    <td className="py-3 px-4 text-right font-mono font-semibold text-slate-700">
                      {p.quantidade_real}
                    </td>

                    {/* Custo Unitário Final */}
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-800">
                      {formatBRL(p.custo_unitario_final)}
                    </td>

                    {/* Preço de Revenda Sugerido */}
                    <td className="py-3 px-4 text-right font-mono font-extrabold text-brand-700 bg-blue-50/30 text-sm">
                      {formatBRL(p.preco_revenda_unitario)}
                    </td>

                    {/* Lucro Total */}
                    <td className="py-3 px-4 text-right font-mono font-extrabold text-emerald-600">
                      {formatBRL(p.lucro_total)}
                      <span className="block text-[10px] text-emerald-500 font-normal">
                        ({p.margem_lucro_pct}% margem)
                      </span>
                    </td>
                  </tr>

                  {/* Detalhes Expandidos (Detalhamento Completo de Custos e Impostos) */}
                  {isExpanded && (
                    <tr className="bg-slate-50/90 border-t border-b border-slate-200">
                      <td colSpan={9} className="p-4">
                        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 text-[11px]">
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">Valor Prod.</span>
                            <span className="font-bold text-slate-700">{formatBRL(p.valor_produtos)}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">Frete Rateado</span>
                            <span className="font-bold text-slate-700">{formatBRL(p.frete)}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">Seguro / Outras</span>
                            <span className="font-bold text-slate-700">{formatBRL((p.seguro || 0) + (p.outras_despesas || 0))}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">Desconto NF</span>
                            <span className="font-bold text-rose-600">-{formatBRL(p.desconto)}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">ICMS + ST</span>
                            <span className="font-bold text-slate-700">{formatBRL((p.icms || 0) + (p.icms_st || 0))}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">IPI + II</span>
                            <span className="font-bold text-slate-700">{formatBRL((p.ipi || 0) + (p.ii || 0))}</span>
                          </div>
                          <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                            <span className="text-slate-400 block font-medium">PIS + COFINS</span>
                            <span className="font-bold text-slate-700">{formatBRL((p.pis || 0) + (p.cofins || 0))}</span>
                          </div>
                          <div className="bg-emerald-50 p-2.5 rounded-xl border border-emerald-200">
                            <span className="text-emerald-600 block font-bold">Lucro Unitário</span>
                            <span className="font-extrabold text-emerald-700">{formatBRL(p.lucro_unitario)}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
