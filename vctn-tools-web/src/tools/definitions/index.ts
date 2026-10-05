import type { ToolDefinition } from '@/types/tool'

/**
 * Built-in tool components.
 *
 * One entry per `component_key` the backend runtime can execute — catalogue
 * rows only select which registered component runs, so this list must stay in
 * sync with `vctn-api/app/tools/runtime/providers.py::build_default_registry`.
 *
 * Registration happens in code at build time, never from remote input; a
 * catalogue row whose `component_key` is not registered cannot run.
 */
export const toolDefinitions: readonly ToolDefinition[] = [
  {
    key: 'json.format',
    mode: 'BACKEND',
    componentKey: 'json.format',
    output: 'text',
    fields: [
      {
        name: 'input',
        label: 'JSON 文本',
        kind: 'textarea',
        required: true,
        placeholder: '{"hello": "world"}',
      },
      {
        name: 'mode',
        label: '处理方式',
        kind: 'select',
        defaultValue: 'pretty',
        options: [
          { label: '格式化（缩进 2）', value: 'pretty' },
          { label: '压缩（单行）', value: 'minify' },
          { label: '格式化并按键排序', value: 'sort' },
        ],
      },
    ],
  },
  {
    key: 'xml.format',
    mode: 'BACKEND',
    componentKey: 'xml.format',
    output: 'text',
    fields: [
      {
        name: 'input',
        label: 'XML 文本',
        kind: 'textarea',
        required: true,
        placeholder: '<root><item>hello</item></root>',
      },
    ],
  },
  {
    key: 'toml.parse',
    mode: 'BACKEND',
    componentKey: 'toml.parse',
    output: 'json',
    fields: [
      {
        name: 'input',
        label: 'TOML 文本',
        kind: 'textarea',
        required: true,
        placeholder: 'title = "demo"\n[owner]\nname = "VCTN"',
      },
    ],
  },
  {
    key: 'base64.codec',
    mode: 'BACKEND',
    componentKey: 'base64.codec',
    output: 'text',
    fields: [
      { name: 'input', label: '文本', kind: 'textarea', required: true, placeholder: 'Hello VCTN' },
      {
        name: 'mode',
        label: '方向',
        kind: 'select',
        defaultValue: 'encode',
        options: [
          { label: '编码', value: 'encode' },
          { label: '解码', value: 'decode' },
        ],
      },
      { name: 'urlsafe', label: 'URL 安全变体', kind: 'switch', defaultValue: false },
    ],
  },
  {
    key: 'url.codec',
    mode: 'BACKEND',
    componentKey: 'url.codec',
    output: 'text',
    fields: [
      {
        name: 'input',
        label: '文本',
        kind: 'textarea',
        required: true,
        placeholder: 'https://example.com/?q=中文',
      },
      {
        name: 'mode',
        label: '方向',
        kind: 'select',
        defaultValue: 'encode',
        options: [
          { label: '编码', value: 'encode' },
          { label: '解码', value: 'decode' },
        ],
      },
      {
        name: 'safe',
        label: '保留字符',
        kind: 'text',
        placeholder: '不转义的字符，默认无',
        showWhen: { field: 'mode', equals: ['encode'] },
      },
    ],
  },
  {
    key: 'uuid.generate',
    mode: 'BACKEND',
    componentKey: 'uuid.generate',
    output: 'values',
    fields: [
      { name: 'count', label: '生成数量', kind: 'number', defaultValue: 1, min: 1, max: 100 },
      { name: 'uppercase', label: '大写输出', kind: 'switch', defaultValue: false },
    ],
  },
  {
    key: 'ulid.generate',
    mode: 'BACKEND',
    componentKey: 'ulid.generate',
    output: 'values',
    fields: [
      { name: 'count', label: '生成数量', kind: 'number', defaultValue: 1, min: 1, max: 100 },
    ],
  },
  {
    key: 'hash.digest',
    mode: 'BACKEND',
    componentKey: 'hash.digest',
    output: 'digest',
    fields: [
      { name: 'input', label: '文本', kind: 'textarea', required: true, placeholder: 'Hello VCTN' },
      {
        name: 'algorithm',
        label: '算法',
        kind: 'select',
        defaultValue: 'sha256',
        options: [
          { label: 'MD5', value: 'md5' },
          { label: 'SHA-1', value: 'sha1' },
          { label: 'SHA-256', value: 'sha256' },
          { label: 'SHA-512', value: 'sha512' },
        ],
      },
    ],
  },
  {
    key: 'regex.test',
    mode: 'BACKEND',
    componentKey: 'regex.test',
    output: 'regex',
    fields: [
      { name: 'pattern', label: '正则表达式', kind: 'text', required: true, placeholder: '\\d+' },
      {
        name: 'text',
        label: '被测文本',
        kind: 'textarea',
        required: true,
        placeholder: '订单 1001、1002、1003',
      },
    ],
  },
  {
    key: 'jwt.parse',
    mode: 'BACKEND',
    componentKey: 'jwt.parse',
    output: 'jwt',
    fields: [
      {
        name: 'token',
        label: 'JWT（不校验签名）',
        kind: 'textarea',
        required: true,
        placeholder: 'eyJhbGciOi...',
        help: '仅解码 header 与 payload；签名不会被回显也不会进入日志。',
      },
    ],
  },
  {
    key: 'text.stats',
    mode: 'BACKEND',
    componentKey: 'text.stats',
    output: 'stats',
    fields: [
      {
        name: 'input',
        label: '文本',
        kind: 'textarea',
        required: true,
        placeholder: '粘贴要统计的文本',
      },
    ],
  },
  {
    key: 'datetime.convert',
    mode: 'BACKEND',
    componentKey: 'datetime.convert',
    output: 'datetime',
    fields: [
      {
        name: 'mode',
        label: '转换方向',
        kind: 'select',
        defaultValue: 'now',
        options: [
          { label: '当前时间', value: 'now' },
          { label: '时间戳 → 时间', value: 'from_epoch' },
          { label: 'ISO 8601 → 时间戳', value: 'from_iso' },
        ],
      },
      {
        name: 'value',
        label: '输入值',
        kind: 'text',
        placeholder: '时间戳（秒/毫秒）或 ISO 8601 字符串',
        showWhen: { field: 'mode', equals: ['from_epoch', 'from_iso'] },
      },
    ],
  },
  {
    key: 'random.string',
    mode: 'BACKEND',
    componentKey: 'random.string',
    output: 'text',
    fields: [
      { name: 'length', label: '长度', kind: 'number', defaultValue: 16, min: 1, max: 256 },
      {
        name: 'alphabet',
        label: '字符集（留空用默认）',
        kind: 'text',
        placeholder: 'abcdefghijklmnopqrstuvwxyz…0123456789',
      },
    ],
  },
  {
    key: 'password.generate',
    mode: 'BACKEND',
    componentKey: 'password.generate',
    output: 'values',
    fields: [
      { name: 'length', label: '密码长度', kind: 'number', defaultValue: 16, min: 4, max: 128 },
      { name: 'count', label: '生成数量', kind: 'number', defaultValue: 5, min: 1, max: 50 },
      { name: 'lowercase', label: '包含小写字母 a-z', kind: 'switch', defaultValue: true },
      { name: 'uppercase', label: '包含大写字母 A-Z', kind: 'switch', defaultValue: true },
      { name: 'digits', label: '包含数字 0-9', kind: 'switch', defaultValue: true },
      {
        name: 'symbols',
        label: '包含特殊字符',
        kind: 'switch',
        defaultValue: true,
        help: '默认字符集：!@#$%^&*()-_=+[]{};:,.?/',
      },
      {
        name: 'exclude',
        label: '排除的字符',
        kind: 'text',
        placeholder: '例如 0O1lI，逐个按字符排除',
        help: '至少保留一种字符类别，否则无法生成。',
      },
      {
        name: 'exclude_ambiguous',
        label: '排除易混淆字符（0O1lI 等）',
        kind: 'switch',
        defaultValue: false,
        help: '用于需要人工抄写或口述的场景。',
      },
    ],
  },
  {
    key: 'unicode.inspect',
    mode: 'BACKEND',
    componentKey: 'unicode.inspect',
    output: 'codepoints',
    fields: [
      {
        name: 'input',
        label: '文本',
        kind: 'textarea',
        required: true,
        placeholder: '中文 ABC 123',
      },
    ],
  },
  {
    key: 'markdown.render',
    mode: 'BACKEND',
    componentKey: 'markdown.render',
    output: 'markdown',
    fields: [
      {
        name: 'input',
        label: 'Markdown',
        kind: 'textarea',
        required: true,
        placeholder: '# 标题\n\n- 列表项\n\n**加粗**',
        help: '后端渲染并做白名单净化后返回 HTML。',
      },
    ],
  },
  {
    key: 'frontend.echo',
    mode: 'FRONTEND',
    componentKey: 'frontend.echo',
    output: 'echo',
    fields: [
      {
        name: 'input',
        label: '文本（浏览器本地处理）',
        kind: 'textarea',
        required: true,
        placeholder: '这段文本只在浏览器内处理，不会上传内容',
      },
    ],
  },
  {
    key: 'async.job',
    mode: 'ASYNC',
    componentKey: 'async.job',
    output: 'job',
    fields: [
      {
        name: 'input',
        label: '任务载荷（JSON）',
        kind: 'textarea',
        required: true,
        placeholder: '{"anything": "goes here"}',
        help: '异步工具不会内联执行：提交后返回一个任务，可用任务 ID 查询状态。',
      },
    ],
  },
]
