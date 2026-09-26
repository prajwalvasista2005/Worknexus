/**
 * Formatting and utility helpers for WorkNexus
 */

/**
 * Format a number as percentage. If value is null, undefined, or NaN, returns fallback (default '—').
 * Never returns "NaN%".
 */
export function formatPercentage(
  value: number | string | null | undefined,
  fallback = '—',
  maxDecimals = 1
): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }

  // If number is already in 0-1 range (e.g. 0.85 for 85%), scale up if <= 1.0 and > 0,
  // or if already scaled e.g. 85, keep it.
  const displayNum = num > 0 && num <= 1 ? num * 100 : num;

  return `${displayNum.toFixed(maxDecimals).replace(/\.0$/, '')}%`;
}

/**
 * Format a numeric value or display fallback
 */
export function formatNumber(
  value: number | string | null | undefined,
  fallback = '—'
): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }

  return num.toLocaleString();
}

/**
 * Format ISO dates nicely
 */
export function formatDate(dateString?: string | null): string {
  if (!dateString) return '—';
  try {
    const d = new Date(dateString);
    if (Number.isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

/**
 * Normalize role strings for case-insensitive matching
 */
export function normalizeRole(role?: string | null): string {
  if (!role) return '';
  return role.trim().toLowerCase();
}

/**
 * Check if user has permission to access portal
 */
export function hasRoleAccess(userRole?: string | null, allowedRole?: string): boolean {
  if (!userRole) return false;
  const normalizedUserRole = normalizeRole(userRole);

  // Admin has universal portal access
  if (normalizedUserRole === 'admin') {
    return true;
  }

  if (!allowedRole) return true;
  return normalizedUserRole === normalizeRole(allowedRole);
}

/**
 * Get display label for role
 */
export function getRoleDisplayName(role?: string | null): string {
  if (!role) return 'User';
  const norm = normalizeRole(role);
  switch (norm) {
    case 'student':
      return 'Student';
    case 'employer':
      return 'Employer';
    case 'institute':
      return 'Institute';
    case 'trainer':
      return 'Trainer';
    case 'admin':
      return 'System Admin';
    default:
      return role;
  }
}
