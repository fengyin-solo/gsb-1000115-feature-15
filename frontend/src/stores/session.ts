import { defineStore } from 'pinia'

export type Role = 'admin' | 'staff'

export interface Account {
  name: string
  role: Role
}

/** 可切换的演示账号：一个管理员 + 两个分别承办不同申诉的普通账号。 */
export const ACCOUNTS: Account[] = [
  { name: '值班管理员', role: 'admin' },
  { name: '张伟', role: 'staff' },
  { name: '李娜', role: 'staff' },
]

const STORAGE_KEY = 'complain.session'

function loadAccount(): Account {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const saved = JSON.parse(raw) as Partial<Account>
      const matched = ACCOUNTS.find((item) => item.name === saved.name && item.role === saved.role)
      if (matched) {
        return matched
      }
    }
  } catch {
    // localStorage 不可用时回落到默认管理员账号
  }
  return ACCOUNTS[0]
}

export const useSessionStore = defineStore('session', {
  state: () => {
    const account = loadAccount()
    return {
      operator: account.name,
      role: account.role as Role,
      shiftLabel: '白班 08:00-20:00',
      scope: '实验室样品检测管理平台',
    }
  },
  getters: {
    canOperate: (state) => state.operator.length > 0,
    roleLabel: (state) => (state.role === 'admin' ? '管理员' : '普通账号'),
  },
  actions: {
    setShift(label: string) {
      this.shiftLabel = label
    },
    switchAccount(account: Account) {
      // 账号与角色同时落盘，刷新、重新打开都保持同一个身份，避免归属提示与按钮对不上
      this.operator = account.name
      this.role = account.role
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(account))
      } catch {
        // 持久化失败只影响下次打开，不阻断本次切换
      }
    },
  },
})
