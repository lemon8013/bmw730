import { toolRegistry } from '@/tools/registry'

import { ToolRuntime } from '@/tools/runtime/ToolRuntime'

export {
  ToolExecutionModeError,
  ToolNotFoundError,
  ToolRuntime,
  ToolRuntimeError,
} from '@/tools/runtime/ToolRuntime'
export type {
  ToolExecutionResult,
  ToolExecutor,
  ToolRuntimeContext,
} from '@/tools/runtime/ToolRuntime'

/** Application level runtime instance bound to the application registry. */
export const toolRuntime = new ToolRuntime(toolRegistry)
export { registerBuiltinExecutors } from '@/tools/runtime/executors'
export type { WorkbenchInput } from '@/tools/runtime/executors'
