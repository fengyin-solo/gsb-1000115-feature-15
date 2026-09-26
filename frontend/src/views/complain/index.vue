<template>
  <section class="page" data-module="complain">
    <header class="page-head">
      <div>
        <h2>客户申诉管理</h2>
        <p class="page-desc">维护申诉记录，围绕申诉编号、申诉单位、涉及报告、申诉内容做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记申诉记录</button>
        <button class="btn" type="button" @click="exportRows">导出客户申诉清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>归属提示</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td>
            <span class="hint" :class="{ readonly: !row.permissions?.editable }">
              {{ row.permissions?.hint ?? '—' }}
            </span>
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
            <button
              v-for="action in row.permissions?.actions ?? []"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
            <span v-if="!row.permissions?.actions?.length" class="hint readonly">只读</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无客户申诉数据，可先登记申诉记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条客户申诉记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="createVisible" class="drawer-mask" @click.self="closeCreate">
      <form class="drawer" @submit.prevent="submitCreate">
        <h3>登记申诉记录</h3>
        <label v-for="field in createFields" :key="field" class="drawer-field">
          <span>{{ field }}<em v-if="requiredCreateFields.includes(field)">*</em></span>
          <input v-model="createForm[field]" :placeholder="`请输入${field}`" />
        </label>
        <p class="hint">承办人留空时归当前账号承办；普通账号登记他人承办的记录后，自己将只能只读查看。</p>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="drawer-actions">
          <button class="btn primary" type="submit">提交登记</button>
          <button class="btn ghost" type="button" @click="closeCreate">取消</button>
        </div>
      </form>
    </div>

    <div v-if="detail" class="drawer-mask" @click.self="closeDetail">
      <section class="drawer">
        <h3>申诉详情 · {{ detail['申诉编号'] }}</h3>
        <dl class="detail-grid">
          <template v-for="column in detailColumns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detail[column] ?? '—' }}</dd>
          </template>
        </dl>
        <p class="hint" :class="{ readonly: !detail.permissions?.editable }">
          {{ detail.permissions?.hint }}
        </p>
        <div class="drawer-actions">
          <button
            v-for="action in detail.permissions?.actions ?? []"
            :key="action"
            class="btn primary"
            type="button"
            @click="runAction(action, detail)"
          >
            {{ action }}
          </button>
          <span v-if="!detail.permissions?.actions?.length" class="hint readonly">当前账号对此记录只读</span>
          <button class="btn ghost" type="button" @click="closeDetail">返回列表</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { errorDetail, request } from '@/api/client'

interface Permissions {
  owner: string
  editable: boolean
  actions: string[]
  hint: string
}

type Row = Record<string, string | number | null> & { id: number; permissions?: Permissions }

const ENDPOINT = '/api/complain'
const columns = ["申诉编号", "申诉单位", "涉及报告", "申诉内容", "受理日期", "处理结果", "回复日期", "申诉状态", "承办人"]
const detailColumns = columns
const requiredCreateFields = ["申诉编号", "申诉单位", "涉及报告"]
const createFields = [...requiredCreateFields, "承办人"]
const stats = [{"label": "待受理申诉", "value": 0}, {"label": "受理中申诉", "value": 0}, {"label": "已答复申诉", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const detail = ref<Row | null>(null)
const createVisible = ref(false)
const createForm = ref<Record<string, string>>({})
const createError = ref('')

function resetFilters() {
  filters.value = {}
  void reload()
}

async function exportRows() {
  // 导出也要带当前账号头，保证清单里的归属口径与页面一致
  try {
    const response = await request(`${ENDPOINT}/export`)
    if (!response.ok) {
      throw new Error(await errorDetail(response, '客户申诉清单导出失败'))
    }
    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = '客户申诉清单.json'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉清单导出失败'
  }
}

function openCreate() {
  createForm.value = {}
  createError.value = ''
  createVisible.value = true
}

function closeCreate() {
  createVisible.value = false
}

async function submitCreate() {
  createError.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createForm.value }),
    })
    if (!response.ok) {
      throw new Error(await errorDetail(response, '申诉记录登记失败'))
    }
    const payload = await response.json()
    if (!payload.ok) {
      createError.value = payload.message
      return
    }
    createVisible.value = false
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '申诉记录登记失败'
  }
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) {
      throw new Error(await errorDetail(response, '申诉详情读取失败'))
    }
    detail.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '申诉详情读取失败'
  }
}

function closeDetail() {
  detail.value = null
  // 从详情返回时重新拉列表，归属提示与按钮始终与当前账号口径一致
  void reload()
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      // 越权等被拦下的请求：展示后端原话，并刷新列表确认原记录未被改动
      const message = await errorDetail(response, '客户申诉动作未生效，请稍后重试')
      await reload()
      throw new Error(message)
    }
    const payload = await response.json()
    if (!payload.ok) {
      throw new Error(payload.message || '客户申诉动作未生效，请稍后重试')
    }
    if (detail.value && detail.value.id === row.id && payload.entry) {
      detail.value = payload.entry
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error(await errorDetail(response, '申诉记录列表读取失败'))
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉列表读取失败'
  }
}

onMounted(reload)
</script>
