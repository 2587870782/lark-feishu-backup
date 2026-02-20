import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

import requests

# ===== 必填配置 =====
APP_ID = "<YOUR_APP_ID>"
APP_SECRET = "<YOUR_APP_SECRET>"
REDIRECT_URI = "https://example.com/api/oauth/callback"
TOKEN_STORE_FILE = str(Path(__file__).resolve().parent / "token_store.json")

# 至少包含 offline_access，才能拿到 refresh_token
# 你也可以按需增减 scope（需先在飞书后台开通对应权限）
SCOPES = (
    "offline_access "
    "drive:drive drive:file:download docs:document:export drive:export:readonly "
    "wiki:node:retrieve wiki:wiki:readonly"
)


def fail(msg: str) -> None:
    print(f"[FATAL] {msg}", file=sys.stderr)
    sys.exit(1)


def build_auth_url() -> str:
    params = {
        "client_id": APP_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "get_refresh_token",
    }
    # 保持参数可读，避免手动拼接出错
    return "https://accounts.feishu.cn/open-apis/authen/v1/authorize?" + urlencode(params, quote_via=quote)


def parse_code(callback_url: str) -> str:
    query = parse_qs(urlparse(callback_url).query)
    if "error" in query:
        fail(f"授权失败: {query.get('error', ['unknown'])[0]}")
    codes = query.get("code", [])
    if not codes:
        fail("回调 URL 中未找到 code 参数")
    return codes[0]


def exchange_code_for_refresh_token(code: str) -> str:
    url = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        fail(f"换 token 失败: HTTP {resp.status_code}, body={resp.text[:200]}")

    data = resp.json()
    if data.get("code") != 0:
        msg = data.get("error_description") or data.get("msg") or data.get("error") or "unknown error"
        fail(f"换 token 失败: code={data.get('code')}, msg={msg}")

    refresh_token = data.get("refresh_token")
    if not refresh_token:
        fail("返回中没有 refresh_token。请检查 scope 是否包含 offline_access。")
    return refresh_token


def save_initial_refresh_token(refresh_token: str) -> Path:
    token_file = Path(TOKEN_STORE_FILE)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "refresh_token": refresh_token,
        "access_token": "",
        "expires_in": 0,
        "updated_at": int(time.time()),
    }
    token_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return token_file


def main() -> None:
    if APP_ID in {"", "<YOUR_APP_ID>"}:
        fail("请先填写 APP_ID")
    if APP_SECRET in {"", "<YOUR_APP_SECRET>"}:
        fail("请先填写 APP_SECRET")
    if REDIRECT_URI in {"", "https://example.com/api/oauth/callback"}:
        fail("请先填写 REDIRECT_URI（并在飞书后台安全设置中配置同一回调地址）")

    auth_url = build_auth_url()
    print("1) 打开这个授权链接，完成授权：")
    print(auth_url)
    print("\n2) 授权成功后，把浏览器地址栏完整回调 URL 粘贴到这里：")
    callback_url = input("> ").strip()

    code = parse_code(callback_url)
    refresh_token = exchange_code_for_refresh_token(code)
    token_file = save_initial_refresh_token(refresh_token)

    print("\n[OK] refresh_token 获取成功")
    print(f"已保存到: {token_file}")


if __name__ == "__main__":
    main()
