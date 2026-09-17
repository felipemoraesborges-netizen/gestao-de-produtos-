import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        onClose();
      }, 4500);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose]);

  if (!toast) return null;

  const isSuccess = toast.type === 'success';
  const isError = toast.type === 'error';
  const isWarning = toast.type === 'warning';

  return (
    <div className="fixed bottom-5 right-5 z-50 max-w-md animate-in slide-in-from-bottom-5 duration-300">
      <div className={`flex items-start gap-3 p-4 rounded-2xl shadow-2xl border backdrop-blur-xl ${
        isSuccess
          ? 'bg-emerald-950/90 dark:bg-emerald-950/95 border-emerald-500/30 text-emerald-100 shadow-emerald-950/40'
          : isError
          ? 'bg-rose-950/90 dark:bg-rose-950/95 border-rose-500/30 text-rose-100 shadow-rose-950/40'
          : isWarning
          ? 'bg-amber-950/90 dark:bg-amber-950/95 border-amber-500/30 text-amber-100 shadow-amber-950/40'
          : 'bg-slate-900/90 dark:bg-zinc-900/95 border-slate-700/80 dark:border-zinc-800 text-slate-100 shadow-black/40'
      }`}>
        <div className="flex-shrink-0 mt-0.5">
          {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          {isError && <AlertCircle className="w-5 h-5 text-rose-400" />}
          {isWarning && <AlertCircle className="w-5 h-5 text-amber-400" />}
          {!isSuccess && !isError && !isWarning && <Info className="w-5 h-5 text-cyan-400" />}
        </div>
        <div className="flex-1 pr-2">
          <p className="text-xs sm:text-sm font-medium leading-relaxed">{toast.message}</p>
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 text-slate-400 hover:text-white transition-colors p-0.5 rounded-lg"
          aria-label="Fechar notificação"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

