# token_store.json 约定

## 文件路径
- `code/token_store.json`

## 数据结构
```json
{
  "refresh_token": "<redacted>",
  "access_token": "<redacted or empty>",
  "expires_in": 7200,
  "updated_at": 1771160428
}
```

## 最小有效条件（基于现有脚本）
- JSON 可解析。
- `refresh_token` 非空字符串。
- `refresh_token` 形态满足 JWT 风格（包含两个 `.`，共三段）。

## 失效信号
- `code/main.py` 刷新 token 时返回 invalid refresh token 类错误码：
  - `20026`
  - `20037`
  - `20064`
  - `20073`
  - `20074`

## 恢复动作
1. 不手工拼接 token。
2. 重新运行 `python3 code/get_initial_refresh_token.py`。
3. 用新回调 URL 重新写入 `code/token_store.json`。
