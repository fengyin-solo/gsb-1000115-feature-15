"""客户申诉接口：维护申诉记录，覆盖受理申诉、提交答复、升级仲裁等动作。

所有读写接口都要求携带登录身份（X-Account-Id），编辑类动作在服务层按承办归属
二次鉴权，越权一律 403 且不改动原记录。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.accounts import Account, ForbiddenError, current_account
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.complain import ComplainService

router = APIRouter(prefix="/api/complain", tags=["客户申诉"])

service = ComplainService()

LIST_FIELDS = ["申诉编号", "申诉单位", "涉及报告", "申诉内容", "受理日期", "处理结果", "回复日期", "申诉状态"]
STATUSES = ["待受理", "受理中", "已答复", "已撤诉", "升级仲裁"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按申诉编号检索"),
    status: str | None = Query(default=None, description="待受理、受理中、已答复、已撤诉、升级仲裁"),
    page: int = 1,
    size: int = 20,
    account: Account = Depends(current_account),
) -> PageResult[dict]:
    """按申诉编号与状态过滤客户申诉列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(account, keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出客户申诉清单：仅用于文件导出，不携带权限信息，不提供动作入口。"""
    from app.store import store

    rows = store.rows("complain")
    return {
        "module": "complain",
        "total": len(rows),
        "items": [
            {
                "申诉编号": row.get("申诉编号"),
                "申诉单位": row.get("申诉单位"),
                "涉及报告": row.get("涉及报告"),
                "申诉状态": row.get("status"),
            }
            for row in rows
        ],
    }


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int, account: Account = Depends(current_account)) -> dict:
    """读取单条申诉记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id, account)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"申诉记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload, account: Account = Depends(current_account)) -> ActionResult:
    """登记一条申诉记录，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values, account)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="申诉记录已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(
    entry_id: int,
    payload: EntryPayload,
    account: Account = Depends(current_account),
) -> ActionResult:
    """对单条申诉执行受理申诉、提交答复、升级仲裁；越权访问返回 403，记录保持原状。"""
    action = str(payload.values.get("action") or "").strip()
    try:
        entry, message = service.run_action(entry_id, action, account)
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
