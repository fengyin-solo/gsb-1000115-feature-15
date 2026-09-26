"""会话接口：提供可切换的账号列表与当前身份信息。

骨架项目用账号切换模拟登录：前端把所选账号放在 X-Account-Id 请求头里，
后端各业务接口据此鉴权。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.accounts import ACCOUNTS, Account, current_account

router = APIRouter(prefix="/api/session", tags=["会话"])


@router.get("/accounts")
def list_accounts() -> dict[str, object]:
    """返回可用于切换的账号（管理员与普通承办账号）。"""
    return {"items": [account.public() for account in ACCOUNTS.values()]}


@router.get("/me")
def get_me(account: Account = Depends(current_account)) -> dict[str, object]:
    """根据请求头返回当前账号，供前端校验本地保存的身份是否仍有效。"""
    return account.public()
