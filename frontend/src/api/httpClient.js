import { API_BASE_URL } from '../config/env';

export class ApiError extends Error {
  constructor({ code, message, retryable = false, status = 0, fields = null, requestId = null }) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.retryable = retryable;
    this.status = status;
    this.fields = fields;
    this.requestId = requestId;
  }
}

export const isAbortError = (error) => error?.name === 'AbortError';

/** Merges the caller's abort signal with a timeout; the cause is distinguishable afterwards. */
function withTimeout(signal, timeoutMs) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', onAbort, { once: true });
  }
  return {
    signal: controller.signal,
    didTimeOut: () => timedOut,
    cleanup: () => {
      clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
    },
  };
}

async function readErrorBody(response) {
  try {
    const body = await response.json();
    return body?.error || null;
  } catch {
    return null;
  }
}

export async function request(path, { method = 'GET', body, signal, timeoutMs = 30000 } = {}) {
  const guard = withTimeout(signal, timeoutMs);
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: guard.signal,
    });
  } catch (error) {
    if (guard.didTimeOut()) {
      throw new ApiError({
        code: 'CLIENT_TIMEOUT',
        message: 'The request took too long. Please try again.',
        retryable: true,
      });
    }
    if (isAbortError(error)) throw error; // intentional cancellation, not a failure
    throw new ApiError({
      code: 'NETWORK_ERROR',
      message: 'Could not reach the server. Check your connection and try again.',
      retryable: true,
    });
  } finally {
    guard.cleanup();
  }

  if (!response.ok) {
    const apiError = await readErrorBody(response);
    throw new ApiError({
      code: apiError?.code || 'HTTP_ERROR',
      message: apiError?.message || `The server responded with an error (${response.status}).`,
      retryable: apiError?.retryable ?? response.status >= 500,
      status: response.status,
      fields: apiError?.details?.fields || null,
      requestId: apiError?.request_id || null,
    });
  }

  try {
    return await response.json();
  } catch {
    throw new ApiError({
      code: 'BAD_RESPONSE',
      message: 'The server returned an unreadable response.',
      retryable: true,
      status: response.status,
    });
  }
}
