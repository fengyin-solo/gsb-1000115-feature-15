"""客户申诉接口：维护申诉记录，覆盖受理申诉、提交答复、升级仲裁等动作。

可编辑范围按承办归属区分：管理员可处理全部记录，普通账号只能处理自己承办的记录，
其余记录只读；越权请求返回 403，原记录保持不变。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.security import Operator, current_operator
from app.services.complain import ComplainService, PermissionError

router = APIRouter(prefix="/api/complain", tags=["客户申诉"])

service = ComplainService()

LIST_FIELDS = ["申诉编号", "申诉单位", "涉及报告", "申诉内容", "受理日期", "处理结果", "回复日期", "申诉状态"]
STATUSES = ["待受理", "受理中", "已答复", "已撤诉", "升级仲裁"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    operator: Operator = Depends(current_operator),
    keyword: str | None = Query(default=None, description="按申诉编号检索"),
    status: str | None = Query(default=None, description="待受理、受理中、已答复、已撤诉、升级仲裁"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按申诉编号与状态过滤客户申诉列表；每行附带当前账号的承办权限说明。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(operator=operator, keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(operator: Operator = Depends(current_operator)) -> dict[str, Any]:
    """导出客户申诉清单：返回当前过滤条件下的全量数据（含承办权限口径）。"""
    items, total = service.list_entries(operator=operator, page=1, size=10000)
    return {"module": "complain", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int, operator: Operator = Depends(current_operator)) -> dict:
    """读取单条申诉记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id, operator)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"申诉记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload, operator: Operator = Depends(current_operator)) -> ActionResult:
    """登记一条申诉记录，缺字段时说明原因而不是静默丢弃；承办人缺省归当前账号。"""
    entry, missing = service.create_entry(payload.values, operator)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="申诉记录已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(
    entry_id: int,
    payload: EntryPayload,
    operator: Operator = Depends(current_operator),
) -> ActionResult:
    """对单条申诉记录执行受理申诉、提交答复、升级仲裁；越权或不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    try:
        entry, message = service.run_action(entry_id, action, operator)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
