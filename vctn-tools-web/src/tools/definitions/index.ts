import type { ToolDefinition } from '@/types/tool'

/**
 * Built-in tool catalogue.
 *
 * Phase 0 deliberately registers no tool. JSON formatting, minify, validate,
 * base64, UUID, timestamp, URL, diff and every other concrete tool are
 * implemented in later phases, each behind the frozen registry contract.
 */
export const toolDefinitions: readonly ToolDefinition[] = []
