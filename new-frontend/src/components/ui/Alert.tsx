import React from 'react';
import { AlertCircle, CheckCircle2, AlertTriangle, Info } from 'lucide-react';

interface AlertProps {
  type?: 'error' | 'success' | 'warning' | 'info';
  title?: string;
  message: string;
  className?: string;
  onRetry?: () => void;
}

export const Alert: React.FC<AlertProps> = ({
  type = 'error',
  title,
  message,
  className = '',
  onRetry,
}) => {
  const isError = type === 'error';
  const isSuccess = type === 'success';
  const isWarning = type === 'warning';

  return (
    <div
      role="alert"
      className={`p-4 rounded-xl border flex items-start gap-3 text-sm ${
        isError
          ? 'bg-red-50/70 border-red-200 text-red-800'
          : isSuccess
          ? 'bg-emerald-50/70 border-emerald-200 text-emerald-800'
          : isWarning
          ? 'bg-amber-50/70 border-amber-200 text-amber-800'
          : 'bg-indigo-50/70 border-indigo-200 text-indigo-800'
      } ${className}`}
    >
      <div className="shrink-0 mt-0.5">
        {isError && <AlertCircle className="w-5 h-5 text-red-600" />}
        {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
        {isWarning && <AlertTriangle className="w-5 h-5 text-amber-600" />}
        {!isError && !isSuccess && !isWarning && <Info className="w-5 h-5 text-indigo-600" />}
      </div>
      <div className="flex-1 min-w-0">
        {title && <h4 className="font-semibold text-slate-900 mb-0.5">{title}</h4>}
        <p className="leading-relaxed">{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-2 text-xs font-semibold underline hover:no-underline text-current cursor-pointer"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
};
