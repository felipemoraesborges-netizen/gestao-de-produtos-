import React, { useState, useRef } from 'react';
import { UploadCloud, FileCode, X, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';

export default function FileUpload({ onUpload, isProcessing }) {
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
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-brand-600" />
            Importar XMLs de NF-e
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Arraste ou selecione os arquivos XML das notas fiscais para processamento automático de custos.
          </p>
        </div>
        {selectedFiles.length > 0 && (
          <button
            type="button"
            onClick={() => setSelectedFiles([])}
            className="text-xs font-semibold text-rose-600 hover:text-rose-700 transition-colors"
          >
            Limpar seleção
          </button>
        )}
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
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') e.preventDefault();
        }}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragOver
            ? 'border-brand-500 bg-brand-50/50 scale-[1.005]'
            : 'border-slate-300 hover:border-brand-400 hover:bg-slate-50/50'
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
        <div className="w-14 h-14 mx-auto rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600 mb-3 group-hover:scale-110 transition-transform">
          <FileCode className="w-7 h-7" />
        </div>
        <p className="text-sm font-bold text-slate-700">
          Clique para selecionar ou arraste seus arquivos XML aqui
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Suporte a múltiplos arquivos simultâneos (.xml de NF-e)
        </p>
      </div>

      {/* Selected Files Badges */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-semibold text-slate-600 mb-2 flex items-center justify-between">
            <span>Arquivos selecionados ({selectedFiles.length}):</span>
          </div>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-1">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-lg text-xs text-slate-700 font-medium group"
              >
                <FileCode className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
                <span className="truncate max-w-[200px]">{file.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="text-slate-400 hover:text-rose-500 transition-colors ml-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isProcessing}
              className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white px-5 py-2.5 rounded-xl font-bold text-sm shadow-md shadow-brand-500/25 hover:shadow-lg transition-all duration-200 disabled:opacity-50"
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
