"""客户申诉业务规则：承办归属、状态流转、字段校验与筛选口径都收在这里。

编辑权限口径：
- 管理员可对全部申诉执行受理申诉、提交答复、升级仲裁；
- 普通账号仅能操作承办人为自己的记录，他人记录只读；
- 越权时抛 ForbiddenError，路由层转 403，且在任何写入之前拦截，原记录保持不变。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.accounts import Account, ForbiddenError, get_account
from app.store import store

MODULE = "complain"
REQUIRED_FIELDS = ["申诉编号", "申诉单位", "涉及报告"]
STATUS_ORDER = ["待受理", "受理中", "已答复", "已撤诉", "升级仲裁"]
ACTION_RULES = {"受理申诉": "受理中", "提交答复": "已答复", "升级仲裁": "升级仲裁"}
NEGATIVE_ACTIONS = []


class ComplainService:
    # ---- 权限与展示 -------------------------------------------------

    def _owner(self, entry: dict[str, Any]) -> Account | None:
        return get_account(entry.get("owner_id"))

    def can_edit(self, entry: dict[str, Any], account: Account) -> bool:
        if account.is_admin:
            return True
        return str(entry.get("owner_id") or "") == account.id

    def _permits(self, entry: dict[str, Any], account: Account) -> dict[str, Any]:
        """给每条记录下发权限与归属说明，前端按钮和提示一律以此为准，避免前后端口径不一致。"""
        owner = self._owner(entry)
        editable = self.can_edit(entry, account)
        if editable:
            reason = "管理员可处理全部申诉" if account.is_admin else "该申诉由你承办，可执行处理动作"
        else:
            owner_name = owner.name if owner else f"账号 {entry.get('owner_id') or '未分配'}"
            reason = f"当前申诉承办人为{owner_name}，普通账号对他人记录仅可查看"
        return {
            "can_accept": editable,
            "can_reply": editable,
            "can_escalate": editable,
            "editable": editable,
            "reason": reason,
        }

    def present(self, entry: dict[str, Any], account: Account) -> dict[str, Any]:
        """对外输出：补齐承办归属展示字段与当前账号下的权限标记。"""
        owner = self._owner(entry)
        result = dict(entry)
        result["申诉状态"] = entry.get("status")
        result["承办人"] = owner.name if owner else "未分配"
        result["承办部门"] = owner.department if owner else "—"
        result["承办归属"] = f"{result['承办人']}（{result['承办部门']}）"
        result["owner_id"] = entry.get("owner_id")
        result["permissions"] = self._permits(entry, account)
        return result

    # ---- 查询 -------------------------------------------------------

    def list_entries(
        self,
        account: Account,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("申诉编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = [self.present(row, account) for row in rows[start:start + size]]
        return page_rows, total

    def get_entry(self, entry_id: int, account: Account) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return self.present(entry, account)

    # ---- 写入 -------------------------------------------------------

    def create_entry(self, values: dict[str, Any], account: Account) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        # 普通账号登记的申诉强制归属本人；管理员可指定承办账号。owner_id 一律由服务端赋值。
        owner_id = account.id
        if account.is_admin and str(values.get("承办账号") or "").strip():
            target = get_account(str(values["承办账号"]).strip())
            if target is None or target.is_admin:
                return None, ["承办账号不存在，请选择有效的承办人"]
            owner_id = target.id
        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["申诉内容"] = values.get("申诉内容", "")
        entry["owner_id"] = owner_id
        entry["status"] = STATUS_ORDER[0]
        entry["受理日期"] = ""
        entry["处理结果"] = ""
        entry["回复日期"] = ""
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self.present(entry, account), []

    def run_action(self, entry_id: int, action: str, account: Account) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"申诉记录 {entry_id} 不存在或已归档"
        # 先鉴权再做任何状态变更：越权请求必须被挡住，原记录保持不变。
        if not self.can_edit(entry, account):
            owner = self._owner(entry)
            owner_name = owner.name if owner else "其他承办人"
            raise ForbiddenError(f"该申诉由{owner_name}承办，{account.name} 无权代为处理")
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于客户申诉可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        today = date.today().isoformat()
        if action == "受理申诉" and not entry.get("受理日期"):
            entry["受理日期"] = today
        if action == "提交答复":
            entry["回复日期"] = today
            entry["处理结果"] = "已向申诉单位提交书面答复"
        return self.present(entry, account), f"申诉记录已{action}"
