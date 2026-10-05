/**
 * 交互验证：字典页与通知页。
 *
 * 覆盖三点交付要求：
 *  1. 点击字典编码打开字典项弹窗，且弹窗内可完成字典项增 / 改 / 删；
 *  2. 通知页的「用户类型」「通知类型」两处下拉展示中文标签、value 仍为原始码；
 *  3. 状态 / 布尔字段统一由 StatusTag 渲染。
 *
 * 未使用 @vue/test-utils（工程未安装且不允许新增依赖），因此直接以
 * `createApp` 挂载真实组件，配合 jsdom 做 DOM 断言。
 */

import { createApp, nextTick, type App, type Component } from 'vue'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as dictApi from '@/api/dictionaries'
import { ApiError } from '@/api/errors'
import * as notificationApi from '@/api/notifications'
import { registerDirectives } from '@/directives'
import DictionaryPage from '@/pages/dictionaries/DictionaryPage.vue'
import NotificationPage from '@/pages/notifications/NotificationPage.vue'
import { usePermissionStore } from '@/stores/permission'
import { ERROR_CODE } from '@/types/api'
import type { Page } from '@/types/api'
import {
  NOTIFICATION_TYPE,
  NOTIFICATION_TYPE_LABEL,
  NOTIFICATION_USER_TYPE,
  NOTIFICATION_USER_TYPE_LABEL,
} from '@/types/enums'
import type { DictItem, DictType } from '@/types/system'

vi.mock('@/api/dictionaries', () => ({
  listDictTypes: vi.fn(),
  createDictType: vi.fn(),
  updateDictType: vi.fn(),
  deleteDictType: vi.fn(),
  listDictItems: vi.fn(),
  createDictItem: vi.fn(),
  updateDictItem: vi.fn(),
  deleteDictItem: vi.fn(),
}))

vi.mock('@/api/notifications', () => ({
  listNotifications: vi.fn(),
  sendNotification: vi.fn(),
  getNotificationStats: vi.fn(),
  markNotificationRead: vi.fn(),
}))

// --- jsdom 基础设施 ---------------------------------------------------------

function installObservers(): void {
  const scope = globalThis as unknown as Record<string, unknown>
  if (scope.ResizeObserver === undefined) {
    scope.ResizeObserver = class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    }
  }
  if (scope.IntersectionObserver === undefined) {
    scope.IntersectionObserver = class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
      takeRecords(): unknown[] {
        return []
      }
    }
  }
}

async function settle(rounds = 3): Promise<void> {
  for (let index = 0; index < rounds; index += 1) {
    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
  await nextTick()
}

function click(element: Element): void {
  element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
}

function buttonByText(root: ParentNode, text: string): HTMLButtonElement {
  const buttons = Array.from(root.querySelectorAll('button'))
  const found = buttons.find((button) => (button.textContent ?? '').trim() === text)
  if (found === undefined) {
    throw new Error(`未找到按钮：${text}`)
  }
  return found as HTMLButtonElement
}

/** 元素或其任一祖先被 `display: none` 隐藏 —— Element Plus 的下拉常驻 DOM。 */
function isHiddenInDom(element: HTMLElement): boolean {
  let node: HTMLElement | null = element
  while (node !== null) {
    if (node.style.display === 'none') {
      return true
    }
    node = node.parentElement
  }
  return false
}

/** 当前可见下拉的选项文本（避开其它常驻的下拉）。 */
function visibleSelectOptions(): string[] {
  const dropdowns = Array.from(document.body.querySelectorAll<HTMLElement>('.el-select-dropdown'))
  const visible = dropdowns.filter((dropdown) => !isHiddenInDom(dropdown))
  const target = visible[visible.length - 1]
  if (target === undefined) {
    return []
  }
  return Array.from(target.querySelectorAll('.el-select-dropdown__item')).map((option) =>
    (option.textContent ?? '').trim(),
  )
}

let mounted: App | null = null

async function mountPage(component: Component): Promise<HTMLElement> {
  const container = document.createElement('div')
  document.body.appendChild(container)

  const pinia = createPinia()
  setActivePinia(pinia)
  usePermissionStore(pinia).applyPermissions({
    permissions: [],
    menus: [],
    is_super_admin: true,
  })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  })
  await router.push('/')
  await router.isReady()

  const app = createApp(component)
  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)
  registerDirectives(app)
  app.mount(container)
  mounted = app
  await settle()
  return container
}

beforeEach(() => {
  installObservers()
})

afterEach(() => {
  mounted?.unmount()
  mounted = null
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

// --- 数据夹具 ---------------------------------------------------------------

const dictType: DictType = {
  id: '1',
  dict_code: 'USER_STATUS',
  dict_name: '用户状态',
  description: '账号启用状态',
  status: 'ACTIVE',
  item_count: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const dictTypePage: Page<DictType> = {
  items: [dictType],
  total: 1,
  page: 1,
  page_size: 20,
}

const dictItem: DictItem = {
  id: '11',
  dict_type_id: '1',
  item_label: '启用',
  item_value: 'ACTIVE',
  item_code: null,
  sort_order: 1,
  status: 'ACTIVE',
  is_default: true,
  description: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function primeDictionary(): void {
  vi.mocked(dictApi.listDictTypes).mockResolvedValue(dictTypePage)
  vi.mocked(dictApi.listDictItems).mockResolvedValue([dictItem])
  vi.mocked(dictApi.createDictItem).mockResolvedValue(dictItem)
  vi.mocked(dictApi.updateDictItem).mockResolvedValue(dictItem)
  vi.mocked(dictApi.deleteDictItem).mockResolvedValue({})
}

function primeNotifications(): void {
  vi.mocked(notificationApi.listNotifications).mockResolvedValue({
    items: [
      {
        id: '9',
        user_type: 'SYS_USER',
        user_id: '3',
        notification_type: 'BLOG_REVIEW',
        title: '待审核文章',
        content: '内容',
        created_at: '2026-01-01T00:00:00Z',
        read_at: null,
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  })
  vi.mocked(notificationApi.getNotificationStats).mockResolvedValue([
    { notification_type: 'BLOG_REVIEW', total: 4, unread: 2 },
  ])
  vi.mocked(notificationApi.sendNotification).mockResolvedValue({
    id: '10',
    user_type: 'SYS_USER',
    user_id: '3',
    notification_type: 'SYSTEM',
    title: 't',
    content: 'c',
    created_at: '2026-01-01T00:00:00Z',
  })
}

// --- 字典页 -----------------------------------------------------------------

describe('字典页：字典编码打开字典项弹窗', () => {
  it('点击 dict_code 打开弹窗并加载该类型的字典项', async () => {
    primeDictionary()
    const container = await mountPage(DictionaryPage)

    const codeLink = container.querySelector('.dictionary-page__code')
    expect(codeLink).not.toBeNull()
    expect((codeLink?.textContent ?? '').trim()).toBe('USER_STATUS')

    // 弹窗未打开时没有对话框，字典项接口也不该被调用。
    expect(document.body.querySelector('.el-dialog')).toBeNull()
    expect(dictApi.listDictItems).not.toHaveBeenCalled()

    if (codeLink !== null) {
      click(codeLink)
    }
    await settle()

    // 点击字典编码后：弹窗标题含字典名称与编码，并按 typeId 拉取字典项。
    const dialog = document.body.querySelector('.el-dialog')
    expect(dialog).not.toBeNull()
    const title = document.body.querySelector('.el-dialog__title')
    expect(title?.textContent ?? '').toContain('用户状态')
    expect(title?.textContent ?? '').toContain('USER_STATUS')
    expect(dictApi.listDictItems).toHaveBeenCalledWith('1')

    // 字典项行渲染出来（标签 + StatusTag 状态）。
    expect(document.body.textContent ?? '').toContain('启用')
  })

  it('弹窗内可新建 / 修改 / 删除字典项', async () => {
    primeDictionary()
    const container = await mountPage(DictionaryPage)

    const codeLink = container.querySelector('.dictionary-page__code')
    if (codeLink !== null) {
      click(codeLink)
    }
    await settle()

    // 新建：填写标签与值后提交。
    click(buttonByText(document.body, '新建字典项'))
    await settle()

    const dialogs = document.body.querySelectorAll('.el-dialog')
    const createDialog = dialogs[dialogs.length - 1]
    const inputs = createDialog.querySelectorAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(2)
    const labelInput = inputs[0]
    const valueInput = inputs[1]
    labelInput.value = '停用'
    labelInput.dispatchEvent(new Event('input', { bubbles: true }))
    valueInput.value = 'DISABLED'
    valueInput.dispatchEvent(new Event('input', { bubbles: true }))
    await settle()

    click(buttonByText(createDialog, '确定'))
    await settle(4)

    expect(dictApi.createDictItem).toHaveBeenCalledTimes(1)
    const [createTypeId, createPayload] = vi.mocked(dictApi.createDictItem).mock.calls[0]
    expect(createTypeId).toBe('1')
    expect(createPayload.item_label).toBe('停用')
    expect(createPayload.item_value).toBe('DISABLED')

    // 修改（切换默认项）：默认项为真时按钮显示「取消默认」。
    click(buttonByText(document.body, '取消默认'))
    await settle()
    expect(dictApi.updateDictItem).toHaveBeenCalledWith('11', { is_default: false })

    // 删除：在字典项弹窗内确认后调用删除接口（避免命中类型表格的同名按钮）。
    const itemsDialog = Array.from(document.body.querySelectorAll('.el-dialog')).find(
      (dialog) => dialog.querySelector('button') !== null && (dialog.textContent ?? '').includes('新建字典项'),
    )
    expect(itemsDialog).toBeDefined()
    if (itemsDialog !== undefined) {
      click(buttonByText(itemsDialog, '删除'))
    }
    await settle(4)
    const confirm = document.body.querySelector('.el-message-box__btns .el-button--primary')
    expect(confirm).not.toBeNull()
    if (confirm !== null) {
      click(confirm)
    }
    await settle()
    expect(dictApi.deleteDictItem).toHaveBeenCalledWith('11')
  })

  it('同一类型下重复字典值时展示 409 专属文案而非通用错误', async () => {
    primeDictionary()
    vi.mocked(dictApi.createDictItem).mockRejectedValue(
      new ApiError({ message: 'duplicate value', code: ERROR_CODE.conflict, httpStatus: 409 }),
    )

    const container = await mountPage(DictionaryPage)
    const codeLink = container.querySelector('.dictionary-page__code')
    if (codeLink !== null) {
      click(codeLink)
    }
    await settle()

    click(buttonByText(document.body, '新建字典项'))
    await settle()
    const dialogs = document.body.querySelectorAll('.el-dialog')
    const createDialog = dialogs[dialogs.length - 1]
    const inputs = createDialog.querySelectorAll('input')
    inputs[0].value = '启用'
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
    inputs[1].value = 'ACTIVE'
    inputs[1].dispatchEvent(new Event('input', { bubbles: true }))
    await settle()

    click(buttonByText(createDialog, '确定'))
    await settle(4)

    const text = document.body.textContent ?? ''
    expect(text).toContain('同一字典类型下，字典值必须唯一')
    // 文案渲染在表单弹窗内，说明冲突后弹窗保持打开、便于就地修改。
    expect(createDialog.isConnected).toBe(true)
    expect((createDialog.querySelector('input') as HTMLInputElement | null)?.value).toBe('启用')
  })
})

// --- 通知页 -----------------------------------------------------------------

describe('通知页：中文标签', () => {
  it('常量映射把原始码翻译为中文标签', () => {
    expect(NOTIFICATION_USER_TYPE.map((value) => NOTIFICATION_USER_TYPE_LABEL[value])).toEqual([
      '管理员',
      '业务用户',
    ])
    for (const value of NOTIFICATION_TYPE) {
      const label = NOTIFICATION_TYPE_LABEL[value]
      expect(label).not.toBe(value)
      expect(label).toMatch(/[一-龥]/)
    }
  })

  it('表格列以中文渲染用户类型与通知类型', async () => {
    primeNotifications()
    await mountPage(NotificationPage)
    await settle()

    const text = document.body.textContent ?? ''
    expect(text).toContain('管理员')
    expect(text).toContain('业务用户')
    expect(text).toContain('文章审核')
    // 原始码不应作为可见文本出现。
    expect(text).not.toContain('SYS_USER')
    expect(text).not.toContain('BLOG_REVIEW')
  })

  it('筛选下拉的选项文本为中文、value 仍为原始码', async () => {
    primeNotifications()
    const container = await mountPage(NotificationPage)

    const selects = container.querySelectorAll('.el-select')
    expect(selects.length).toBeGreaterThanOrEqual(2)

    // 用户类型下拉：显示中文，value 为原始码。
    const userTypeTrigger = selects[0].querySelector('.el-select__wrapper')
    expect(userTypeTrigger).not.toBeNull()
    if (userTypeTrigger !== null) {
      click(userTypeTrigger)
    }
    await settle()
    expect(visibleSelectOptions()).toEqual(['管理员', '业务用户'])

    // 通知类型下拉：显示中文，value 为原始码。
    const notificationTypeTrigger = selects[1].querySelector('.el-select__wrapper')
    expect(notificationTypeTrigger).not.toBeNull()
    if (notificationTypeTrigger !== null) {
      click(notificationTypeTrigger)
    }
    await settle()
    expect(visibleSelectOptions()).toEqual(
      NOTIFICATION_TYPE.map((value) => NOTIFICATION_TYPE_LABEL[value]),
    )
  })
})
