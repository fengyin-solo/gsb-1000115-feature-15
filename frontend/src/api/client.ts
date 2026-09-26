/** 统一请求封装：拼后端地址、带当前账号身份头、抛网络错误、给页脚留一句可读的说明。 */
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

/** 当前账号 ID 的本地持久化键；账号切换后所有接口请求都会带上对应身份。 */
export const ACCOUNT_STORAGE_KEY = 'lab.account-id'

export function request(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const accountId = typeof localStorage === 'undefined' ? '' : localStorage.getItem(ACCOUNT_STORAGE_KEY) ?? ''
  return fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(accountId ? { 'X-Account-Id': accountId } : {}),
      ...(init?.headers ?? {}),
    },
  }).catch((error: unknown) => {
    const detail = error instanceof Error ? error.message : '请求未送达'
    throw new Error(`接口请求失败：${detail}`)
  })
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(`接口返回 ${response.status}，数据未更新`)
  }
  return (await response.json()) as T
}

/** 读取失败响应里的 detail 文案，供页面展示越权/校验原因。 */
export async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail) {
      return payload.detail
    }
  } catch {
    // 响应体不是 JSON 时退回通用文案
  }
  return fallback
}
