import React, { useState, useRef } from 'react';
import { UploadCloud, FileCode, X, ArrowRight, Loader2, Sparkles } from 'lucide-react';

export default function FileUpload({ onUpload, isProcessing, onLoadDemo }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFiles = (fileList) => {
    const validFiles = Array.from(fileList).filter((f) =>
      f.name.toLowerCase().endsWith('.xml')
    );
    if (validFiles.length > 0) {
      setSelectedFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name));
        const newFiles = validFiles.filter((f) => !existingNames.has(f.name));
        return [...prev, ...newFiles];
      });
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = () => {
    if (selectedFiles.length === 0) return;
    onUpload(selectedFiles);
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200/80 dark:border-zinc-800/80 shadow-sm p-6 mb-6 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            Importar XMLs de NF-e
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Arraste ou selecione os arquivos XML das notas fiscais para processamento automático de custos.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onLoadDemo && selectedFiles.length === 0 && (
            <button
              onClick={onLoadDemo}
              className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 flex items-center gap-1 transition-colors px-2.5 py-1 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-500/10"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Carregar Demonstração
            </button>
          )}
          {selectedFiles.length > 0 && (
            <button
              onClick={() => setSelectedFiles([])}
              className="text-xs font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 transition-colors"
            >
              Limpar seleção
            </button>
          )}
        </div>
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragOver
            ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-500/10 scale-[1.005]'
            : 'border-slate-300 dark:border-zinc-700 hover:border-brand-400 dark:hover:border-brand-500/50 hover:bg-slate-50/50 dark:hover:bg-zinc-800/40'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".xml"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
          }}
        />
        <div className="w-14 h-14 mx-auto rounded-2xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center text-brand-600 dark:text-brand-400 mb-3 group-hover:scale-110 transition-transform">
          <FileCode className="w-7 h-7" />
        </div>
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">
          Clique para selecionar ou arraste seus arquivos XML aqui
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          Suporte a múltiplos arquivos simultâneos (.xml de NF-e)
        </p>
      </div>

      {/* Selected Files Badges */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2 flex items-center justify-between">
            <span>Arquivos selecionados ({selectedFiles.length}):</span>
          </div>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-1">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 px-3 py-1.5 rounded-lg text-xs text-slate-700 dark:text-slate-300 font-medium group"
              >
                <FileCode className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400 flex-shrink-0" />
                <span className="truncate max-w-[200px]">{file.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="text-slate-400 hover:text-rose-500 transition-colors ml-1 p-0.5 rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={isProcessing}
              className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white px-5 py-2.5 rounded-xl font-bold text-sm shadow-md shadow-brand-500/25 hover:shadow-lg transition-all duration-200 disabled:opacity-50 btn-press"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processando NF-e...
                </>
              ) : (
                <>
                  Processar {selectedFiles.length} Nota(s)
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

