const DEFAULT_MESSAGE = 'Something went wrong. Please try again.';

function collectMessages(value, messages = []) {
  if (!value) {
    return messages;
  }

  if (typeof value === 'string') {
    messages.push(value);
    return messages;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectMessages(item, messages));
    return messages;
  }

  if (typeof value === 'object') {
    Object.values(value).forEach((item) => collectMessages(item, messages));
  }

  return messages;
}

export function extractApiError(error, fallback = DEFAULT_MESSAGE) {
  const data = error?.response?.data;

  if (!data) {
    return error?.message || fallback;
  }

  const messages = collectMessages(data);
  return messages[0] || fallback;
}
