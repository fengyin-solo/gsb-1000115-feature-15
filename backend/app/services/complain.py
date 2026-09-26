"""客户申诉业务规则：状态流转、字段校验、承办归属鉴权与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.security import Operator
from app.store import store

MODULE = "complain"
REQUIRED_FIELDS = ["申诉编号", "申诉单位", "涉及报告"]
OWNER_FIELD = "承办人"
STATUS_ORDER = ["待受理", "受理中", "已答复", "已撤诉", "升级仲裁"]
ACTION_RULES = {"受理申诉": "受理中", "提交答复": "已答复", "升级仲裁": "升级仲裁"}
NEGATIVE_ACTIONS = []


class PermissionError(Exception):
    """越权操作：当前账号对这条申诉记录没有承办权限，记录保持原样。"""


class ComplainService:
    def list_entries(
        self,
        *,
        operator: Operator,
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
        page_rows = rows[start:start + size]
        return [self.with_permissions(row, operator) for row in page_rows], total

    def get_entry(self, entry_id: int, operator: Operator) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return self.with_permissions(entry, operator)

    def create_entry(self, values: dict[str, Any], operator: Operator) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        # 承办人缺省时归到当前账号名下，避免出现谁都编辑不了的孤儿记录
        entry[OWNER_FIELD] = str(values.get(OWNER_FIELD) or "").strip() or operator.name
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self.with_permissions(entry, operator), []

    def run_action(self, entry_id: int, action: str, operator: Operator) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"申诉记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于客户申诉可执行范围"
        # 先鉴权再流转：越权请求直接抛错，记录一个字段都不动
        if not self.can_edit(entry, operator):
            owner = entry.get(OWNER_FIELD) or "未分配"
            raise PermissionError(
                f"申诉记录 {entry_id} 由「{owner}」承办，当前账号仅可只读查看，"
                f"如需处理请切换承办账号或管理员账号"
            )
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self.with_permissions(entry, operator), f"申诉记录已{action}"

    def can_edit(self, entry: dict[str, Any], operator: Operator) -> bool:
        """管理员全量可办；普通账号只能办自己名下的记录。"""
        if operator.is_admin:
            return True
        owner = str(entry.get(OWNER_FIELD) or "").strip()
        return bool(operator.name) and owner == operator.name

    def with_permissions(self, entry: dict[str, Any], operator: Operator) -> dict[str, Any]:
        """生成给前端看的行副本：附上承办归属与可执行动作，按钮和提示共用这一份口径。"""
        row = dict(entry)
        editable = self.can_edit(entry, operator)
        owner = str(entry.get(OWNER_FIELD) or "").strip() or "未分配"
        row["permissions"] = {
            "owner": owner,
            "editable": editable,
            "actions": list(ACTION_RULES) if editable else [],
            "hint": "当前账号可承办此记录" if editable else f"由「{owner}」承办，当前账号只读",
        }
        return row
