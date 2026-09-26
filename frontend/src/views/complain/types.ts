/** 客户申诉模块的接口类型；权限以后端下发为准，前端不自行推断。 */

export interface ComplainPermissions {
  editable: boolean
  can_accept: boolean
  can_reply: boolean
  can_escalate: boolean
  /** 只读/可编辑的归属说明，保证按钮状态与提示文案口径一致。 */
  reason: string
}

export interface ComplainRow {
  id: number
  status: string
  申诉编号: string
  申诉单位: string
  涉及报告: string
  申诉内容: string
  受理日期: string
  处理结果: string
  回复日期: string
  申诉状态: string
  承办人: string
  承办部门: string
  承办归属: string
  owner_id: string | null
  permissions: ComplainPermissions
}

export type ComplainAction = '受理申诉' | '提交答复' | '升级仲裁'

/** 列表与详情可直接展示的文本字段。 */
export type ComplainField =
  | '申诉编号'
  | '申诉单位'
  | '涉及报告'
  | '申诉内容'
  | '受理日期'
  | '处理结果'
  | '回复日期'
  | '申诉状态'

/** 动作与后端权限字段的映射，供列表与详情页共用，避免两处口径不一致。 */
export const ACTION_PERMISSION: { action: ComplainAction; permission: keyof Omit<ComplainPermissions, 'editable' | 'reason'> }[] = [
  { action: '受理申诉', permission: 'can_accept' },
  { action: '提交答复', permission: 'can_reply' },
  { action: '升级仲裁', permission: 'can_escalate' },
]

export function canRunAction(row: ComplainRow, action: ComplainAction): boolean {
  const mapping = ACTION_PERMISSION.find((item) => item.action === action)
  return Boolean(mapping && row.permissions[mapping.permission])
}
