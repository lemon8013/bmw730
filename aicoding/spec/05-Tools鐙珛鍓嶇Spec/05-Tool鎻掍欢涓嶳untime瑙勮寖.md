# 05 Tool 插件与 Runtime 规范

## 核心对象

```text
ToolDefinition
ToolRegistry
ToolProvider
ToolRuntime
UsageReporter
```

## ToolDefinition

至少：

```ts
interface ToolDefinition {
  code: string
  name: string
  componentKey: string
  executionMode: 'FRONTEND' | 'BACKEND' | 'ASYNC'
  version?: string
}
```

完整字段以后端 API Contract 为准。

## Registry

```ts
registry.register('json-format', JsonFormatTool)
registry.register('base64-encode', Base64EncodeTool)
```

后端返回 `component_key` 后，只能从白名单 Registry 获取组件。

禁止：

```ts
import(componentKey)
```

## Runtime

统一负责：

1. Definition 检查
2. 输入验证
3. Access 处理
4. 执行
5. 错误标准化
6. duration
7. Usage 上报

## Tool Component

只负责自己的 UI 和业务计算，不自行实现全局认证、Quota、Usage、Trace。

## 执行模式

FRONTEND：JSON/XML/YAML/TOML/Base64/URL/UUID/时间/文本/Regex/基础图片。

BACKEND：HTTP/DNS/IP/第三方 API。

ASYNC：大文件、长耗时转换、批处理。

## 原则

不得用大型 `if/else` 判断 Tool；不得绕过统一 Runtime。
