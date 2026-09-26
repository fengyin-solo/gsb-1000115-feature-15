"""当前操作人上下文：从请求头还原账号与角色，供各模块做归属鉴权。

骨架阶段没有登录体系，账号信息由前端放在请求头里带上来：
- X-Operator-Name：账号姓名，如「张伟」；HTTP 头只能放 latin-1，
  中文姓名由前端 percent-encode 后传输，这里负责解码还原
- X-Operator-Role：角色，admin（管理员）或 staff（普通账号）

请求头缺失时按未知名普通账号处理：能看列表，但任何归属校验都不会通过。
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

from fastapi import Header

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"


@dataclass(frozen=True)
class Operator:
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def current_operator(
    x_operator_name: str | None = Header(default=None),
    x_operator_role: str | None = Header(default=None),
) -> Operator:
    """FastAPI 依赖：解析请求头里的操作人，角色只认白名单，其余一律按普通账号。"""
    name = unquote((x_operator_name or "").strip())
    role = (x_operator_role or "").strip().lower()
    if role not in {ROLE_ADMIN, ROLE_STAFF}:
        role = ROLE_STAFF
    return Operator(name=name, role=role)
