/**
 * API layer.
 *
 * Phase 0 exposes the shared axios instance only. Tool, access and usage
 * clients are added by the phase that freezes the matching API contract.
 */
export {
  ApiEnvelopeError,
  ApiTransportError,
  apiBaseUrl,
  createApiClient,
  httpClient,
} from '@/api/client'
