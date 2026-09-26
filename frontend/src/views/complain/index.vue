<template>
  <section class="page" data-module="complain">
    <header class="page-head">
      <div>
        <h2>客户申诉管理</h2>
        <p class="page-desc">维护申诉记录，围绕申诉编号、申诉单位、涉及报告、申诉内容做登记、筛选与状态流转；按承办归属区分编辑范围。</p>
      </div>
      <div class="page-actions">
        <button v-if="session.isAdmin" class="btn primary" type="button" @click="openCreate">登记申诉记录</button>
        <button class="btn" type="button" @click="exportRows">导出客户申诉清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <p class="scope-tip" :class="{ readonly: !session.isAdmin }">
      当前账号：{{ session.operator }}（{{ session.isAdmin ? '管理员，可处理全部申诉' : '普通账号，仅可处理本人承办的申诉，他人记录只读' }}）
    </p>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>申诉编号</span>
        <input v-model="keyword" placeholder="按申诉编号检索" />
      </label>
      <label class="filter-item">
        <span>申诉状态</span>
        <select v-model="status">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>承办归属 / 可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
          <td class="row-actions">
            <div class="owner-cell">
              <span class="owner-tag" :class="{ mine: row.permissions.editable && !session.isAdmin }">
                {{ row.承办归属 }}
              </span>
              <span class="owner-reason">{{ row.permissions.reason }}</span>
              <span class="action-line">
                <RouterLink class="link" :to="`/complain/${row.id}`">查看详情</RouterLink>
                <button
                  v-for="{ action } in actionItems"
                  :key="action"
                  class="link"
                  type="button"
                  :disabled="!canRunAction(row, action)"
                  :title="canRunAction(row, action) ? action : row.permissions.reason"
                  @click="runAction(action, row)"
                >
                  {{ action }}
                </button>
              </span>
            </div>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无客户申诉数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条客户申诉记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="creating" class="modal-mask" @click.self="creating = false">
      <form class="modal-card" @submit.prevent="submitCreate">
        <h3>登记申诉记录</h3>
        <p class="modal-tip">管理员登记的申诉需指定承办账号，后续由承办人或管理员处理。</p>
        <label v-for="field in createFields" :key="field.key" class="modal-field">
          <span>{{ field.label }}</span>
          <input v-model="createForm[field.key]" :placeholder="`请输入${field.label}`" />
        </label>
        <label class="modal-field">
          <span>承办账号</span>
          <select v-model="createForm.owner_id">
            <option value="" disabled>请选择承办人</option>
            <option v-for="account in staffAccounts" :key="account.id" :value="account.id">
              {{ account.name }}（{{ account.department }}）
            </option>
          </select>
        </label>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="creating = false">取消</button>
          <button class="btn primary" type="submit">确认登记</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore, type Account } from '@/stores/session'
import { ACTION_PERMISSION, canRunAction, type ComplainAction, type ComplainField, type ComplainRow } from '@/views/complain/types'

const ENDPOINT = '/api/complain'
const columns: ComplainField[] = ['申诉编号', '申诉单位', '涉及报告', '申诉内容', '受理日期', '处理结果', '回复日期', '申诉状态']
const actionItems = ACTION_PERMISSION
const statuses = ['待受理', '受理中', '已答复', '已撤诉', '升级仲裁']

const session = useSessionStore()
const rows = ref<ComplainRow[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const status = ref('')

const creating = ref(false)
const createError = ref('')
const createForm = reactive({ 申诉编号: '', 申诉单位: '', 涉及报告: '', 申诉内容: '', owner_id: '' })
const createFields = [
  { key: '申诉编号', label: '申诉编号' },
  { key: '申诉单位', label: '申诉单位' },
  { key: '涉及报告', label: '涉及报告' },
  { key: '申诉内容', label: '申诉内容' },
] as const

const staffAccounts = computed<Account[]>(() => session.accounts.filter((account) => !account.is_admin))

const stats = computed(() => [
  { label: '待受理申诉', value: rows.value.filter((row) => row.申诉状态 === '待受理').length },
  { label: '受理中申诉', value: rows.value.filter((row) => row.申诉状态 === '受理中').length },
  { label: '我承办的申诉', value: rows.value.filter((row) => row.owner_id === session.accountId).length },
])

watch(() => session.accountId, () => {
  void reload()
})

function resetFilters() {
  keyword.value = ''
  status.value = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  createError.value = ''
  Object.assign(createForm, { 申诉编号: '', 申诉单位: '', 涉及报告: '', 申诉内容: '', owner_id: '' })
  creating.value = true
}

async function submitCreate() {
  createError.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm } }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '申诉记录登记失败')
    }
    creating.value = false
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '申诉记录登记失败'
  }
}

async function runAction(action: ComplainAction, row: ComplainRow) {
  errorMessage.value = ''
  // 按钮虽已按后端权限禁用，仍再拦一道，避免过期权限状态下发出越权请求。
  if (!canRunAction(row, action)) {
    errorMessage.value = row.permissions.reason
    return
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      // 403：越权已被后端挡住，记录未改动；重新拉取以服务端权限为准，消除界面矛盾。
      const message = await readErrorDetail(response, '客户申诉动作未生效，请稍后重试')
      await reload()
      throw new Error(message)
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (keyword.value) {
    query.set('keyword', keyword.value)
  }
  if (status.value) {
    query.set('status', status.value)
  }
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '申诉记录列表读取失败'))
    }
    const payload = (await response.json()) as { items?: ComplainRow[]; total?: number }
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.scope-tip {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  background: #eef4ff;
  border: 1px solid #b9d3ff;
  color: #1f4fb0;
}
.scope-tip.readonly {
  background: #f4f5f7;
  border-color: var(--border);
  color: var(--muted);
}
.owner-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.owner-tag {
  font-size: 12px;
  color: var(--muted);
}
.owner-tag.mine {
  color: #1f6feb;
  font-weight: 600;
}
.owner-reason {
  font-size: 12px;
  color: var(--muted);
}
.action-line {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.link:disabled {
  color: #9aa4b2;
  cursor: not-allowed;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal-card {
  width: 420px;
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
}
.modal-card h3 {
  margin: 0 0 4px;
}
.modal-tip {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--muted);
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
  font-size: 13px;
}
.modal-field input,
.modal-field select {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
