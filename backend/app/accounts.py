"""账号与权限：客户申诉按承办归属区分可编辑范围。

骨架项目没有接入真实登录，这里用内存账号表 + 请求头 X-Account-Id 标识当前身份，
便于在演示环境反复切换账号验证权限；权限判定一律以后端为准，前端只做展示。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    role: str
    department: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "is_admin": self.is_admin,
        }


# 一个管理员 + 两个普通账号；种子申诉记录分别归属到两个普通账号，方便交叉验证只读。
ACCOUNTS: dict[str, Account] = {
    "admin": Account("admin", "系统管理员", ROLE_ADMIN, "质量管理部"),
    "u1001": Account("u1001", "王敏", ROLE_STAFF, "客服一组"),
    "u1002": Account("u1002", "李强", ROLE_STAFF, "客服二组"),
}

DEFAULT_ACCOUNT_ID = "admin"


class ForbiddenError(Exception):
    """业务层检出越权操作时抛出，由路由层转成 403，且不得改动原记录。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def current_account(x_account_id: str | None = Header(default=None, alias="X-Account-Id")) -> Account:
    """从请求头解析当前账号；申诉相关接口必须显式携带身份，缺失或无法识别时按未登录处理（401）。"""
    account_id = (x_account_id or "").strip()
    account = ACCOUNTS.get(account_id) if account_id else None
    if account is None:
        raise HTTPException(status_code=401, detail="未获取到登录账号，请重新选择账号后再操作")
    return account


def get_account(account_id: str | None) -> Account | None:
    if not account_id:
        return None
    return ACCOUNTS.get(str(account_id).strip())
