import { defineStore } from 'pinia'

import { ACCOUNT_STORAGE_KEY, request } from '@/api/client'

export type AccountRole = 'admin' | 'staff'

export interface Account {
  id: string
  name: string
  role: AccountRole
  department: string
  is_admin: boolean
}

const FALLBACK_ACCOUNT: Account = {
  id: 'admin',
  name: '系统管理员',
  role: 'admin',
  department: '质量管理部',
  is_admin: true,
}

function readStoredId(): string {
  if (typeof localStorage === 'undefined') {
    return FALLBACK_ACCOUNT.id
  }
  return localStorage.getItem(ACCOUNT_STORAGE_KEY) || FALLBACK_ACCOUNT.id
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    accounts: [] as Account[],
    accountId: readStoredId(),
    shiftLabel: '白班 08:00-20:00',
    scope: '实验室样品检测管理平台',
    loaded: false,
  }),
  getters: {
    currentAccount(state): Account {
      return state.accounts.find((item) => item.id === state.accountId) ?? {
        ...FALLBACK_ACCOUNT,
        id: state.accountId,
      }
    },
    operator(): string {
      return this.currentAccount.name
    },
    isAdmin(): boolean {
      return this.currentAccount.is_admin
    },
    canOperate(): boolean {
      return this.accountId.length > 0
    },
  },
  actions: {
    /** 拉取可切换账号；若本地保存的身份已失效，回退到管理员，避免一直带着非法头发请求。 */
    async loadAccounts() {
      try {
        const response = await request('/api/session/accounts')
        if (!response.ok) {
          throw new Error('账号列表读取失败')
        }
        const payload = (await response.json()) as { items: Account[] }
        this.accounts = payload.items ?? []
        if (!this.accounts.some((item) => item.id === this.accountId)) {
          this.switchAccount(FALLBACK_ACCOUNT.id)
        }
      } finally {
        this.loaded = true
      }
    },
    switchAccount(accountId: string) {
      this.accountId = accountId
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(ACCOUNT_STORAGE_KEY, accountId)
      }
    },
    setShift(label: string) {
      this.shiftLabel = label
    },
  },
})
