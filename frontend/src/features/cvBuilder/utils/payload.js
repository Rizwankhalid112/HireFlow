/*
 * DRF rejects '' for nullable IntegerField/DecimalField, so empty form inputs
 * have to be converted to null (not omitted — PUT needs the full object).
 */

export function toNullableInt(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export function toNullableDecimal(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export function toTrimmedString(value) {
  return typeof value === 'string' ? value.trim() : '';
}

/*
 * Django's URLField runs its own validator before the serializer's
 * validate_<field> hook, so the backend's normalize_profile_url never sees a
 * scheme-less value — "linkedin.com/in/you" 400s outright. Add the scheme here.
 */
export function toAbsoluteUrl(value) {
  const trimmed = toTrimmedString(value);
  if (!trimmed) {
    return '';
  }
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('//')) {
    return `https:${trimmed}`;
  }
  return `https://${trimmed}`;
}

/* Comma-separated input -> tech_stack list, deduped and capped by the caller. */
export function parseTechStack(value, max) {
  const items = String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  const unique = [...new Set(items)];
  return typeof max === 'number' ? unique.slice(0, max) : unique;
}
