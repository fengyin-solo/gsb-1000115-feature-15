/** 统一请求封装：拼后端地址、带当前账号头、抛网络错误、给页脚留一句可读的说明。 */
import { useSessionStore } from '@/stores/session'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export function request(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const session = useSessionStore()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session.operator) {
    // HTTP 头只能放 latin-1，中文姓名 percent-encode 后由后端解码还原
    headers['X-Operator-Name'] = encodeURIComponent(session.operator)
    headers['X-Operator-Role'] = session.role
  }
  return fetch(url, {
    headers,
    ...init,
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

/** 读取 FastAPI 错误体里的 detail，越权等场景要把后端原话展示给用户。 */
export async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json()
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  } catch {
    // 错误体不是 JSON 时使用兜底文案
  }
  return fallback
}
