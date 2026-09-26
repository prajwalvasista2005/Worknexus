import React from 'react';

interface CircularProgressProps {
  score: number; // 0-100 or 0-1
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  score,
  size = 180,
  strokeWidth = 14,
  label = 'Readiness',
  sublabel,
}) => {
  // Normalize score to 0-100
  const normalizedScore = Math.max(
    0,
    Math.min(100, score <= 1 && score > 0 ? Math.round(score * 100) : Math.round(score))
  );

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  // Determine indicator color based on score thresholds
  let strokeColor = '#4F46E5'; // Primary Indigo
  let badgeColor = 'text-indigo-600 bg-indigo-50 border-indigo-200';
  let statusText = 'Moderate Match';

  if (normalizedScore >= 80) {
    strokeColor = '#059669'; // Emerald
    badgeColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
    statusText = 'High Readiness';
  } else if (normalizedScore >= 60) {
    strokeColor = '#4F46E5'; // Indigo
    badgeColor = 'text-indigo-700 bg-indigo-50 border-indigo-200';
    statusText = 'Role Prepared';
  } else if (normalizedScore >= 40) {
    strokeColor = '#D97706'; // Amber
    badgeColor = 'text-amber-700 bg-amber-50 border-amber-200';
    statusText = 'Gap Identified';
  } else {
    strokeColor = '#DC2626'; // Danger Red
    badgeColor = 'text-red-700 bg-red-50 border-red-200';
    statusText = 'Critical Gap';
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
        >
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#E2E8F0"
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeLinecap="round"
          />
          {/* Progress Indicator */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-2">
          <span className="text-3xl font-bold tracking-tight text-slate-900 tabular-nums">
            {normalizedScore}%
          </span>
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider mt-0.5">
            {label}
          </span>
          {sublabel && (
            <span className="text-[11px] text-slate-400 mt-0.5 max-w-[100px] truncate">
              {sublabel}
            </span>
          )}
        </div>
      </div>

      <div className={`mt-3 px-3 py-1 rounded-full border text-xs font-medium ${badgeColor}`}>
        {statusText}
      </div>
    </div>
  );
};
