<template>
  <section class="page detail-page" data-module="complain-detail">
    <header class="page-head">
      <div>
        <h2>申诉记录详情</h2>
        <p class="page-desc">查看申诉明细、承办归属与处理进展；可编辑范围按当前账号的承办归属判定。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/complain">返回列表</RouterLink>
      </div>
    </header>

    <p v-if="row" class="scope-banner" :class="{ readonly: !row.permissions.editable }">
      <span>{{ row.承办归属 }}</span>
      <span class="scope-reason">{{ row.permissions.reason }}</span>
    </p>

    <article v-if="row" class="detail-card">
      <dl class="detail-grid">
        <template v-for="field in detailFields" :key="field">
          <dt>{{ field }}</dt>
          <dd>{{ row[field] || '—' }}</dd>
        </template>
        <dt>承办人</dt>
        <dd>{{ row.承办人 }}（{{ row.承办部门 }}）</dd>
      </dl>

      <div class="detail-actions">
        <button
          v-for="{ action } in actionItems"
          :key="action"
          class="btn"
          :class="{ primary: canRunAction(row, action) }"
          type="button"
          :disabled="!canRunAction(row, action)"
          :title="canRunAction(row, action) ? action : row.permissions.reason"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>
      <p v-if="!row.permissions.editable" class="readonly-note">
        当前为只读状态：该申诉不由你承办，受理申诉、提交答复、升级仲裁仅承办人或管理员可执行。
      </p>
      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    </article>

    <p v-else-if="errorMessage" class="error-text detail-empty">{{ errorMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import { ACTION_PERMISSION, canRunAction, type ComplainAction, type ComplainField, type ComplainRow } from '@/views/complain/types'

const ENDPOINT = '/api/complain'
const detailFields: ComplainField[] = ['申诉编号', '申诉单位', '涉及报告', '申诉内容', '申诉状态', '受理日期', '处理结果', '回复日期']
const actionItems = ACTION_PERMISSION

const route = useRoute()
const session = useSessionStore()
const row = ref<ComplainRow | null>(null)
const errorMessage = ref('')

const entryId = () => Number(route.params.id)

watch(() => route.params.id, () => {
  void loadDetail()
})

// 反复切换账号时不离开页面也要重算权限：归属提示与按钮同源于本次响应，天然一致。
watch(() => session.accountId, () => {
  void loadDetail()
})

async function runAction(action: ComplainAction) {
  if (!row.value || !canRunAction(row.value, action)) {
    return
  }
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId()}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      const message = await readErrorDetail(response, '客户申诉动作未生效')
      // 越权或权限已变化时，用服务端最新记录覆盖当前展示，保留原记录状态。
      await loadDetail()
      throw new Error(message)
    }
    await loadDetail()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '客户申诉操作失败'
  }
}

async function loadDetail() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId()}`)
    if (!response.ok) {
      row.value = null
      throw new Error(await readErrorDetail(response, '申诉明细读取失败'))
    }
    row.value = (await response.json()) as ComplainRow
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '申诉明细读取失败'
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.scope-banner {
  display: flex;
  gap: 12px;
  align-items: baseline;
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  background: #eef4ff;
  border: 1px solid #b9d3ff;
  color: #1f4fb0;
}
.scope-banner.readonly {
  background: #f4f5f7;
  border-color: var(--border);
  color: #334155;
}
.scope-reason {
  color: var(--muted);
}
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
}
.detail-grid {
  display: grid;
  grid-template-columns: 110px 1fr 110px 1fr;
  gap: 10px 14px;
  margin: 0;
}
.detail-grid dt {
  color: var(--muted);
  font-size: 13px;
}
.detail-grid dd {
  margin: 0;
  font-size: 13px;
}
.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}
.btn:disabled {
  color: #9aa4b2;
  cursor: not-allowed;
  background: #f4f5f7;
}
.readonly-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}
.detail-empty {
  margin-top: 24px;
}
</style>
