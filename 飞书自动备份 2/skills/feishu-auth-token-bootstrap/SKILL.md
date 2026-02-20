---
name: feishu-auth-token-bootstrap
description: 处理飞书 OAuth 授权、回调 URL 解析、refresh_token 初始化与失效重置，并校验 code/token_store.json 合法性。 当用户提出“获取授权链接”“回调换 token”“refresh_token 失效”“token_store.json 缺失或格式错误排查”时使用。
---

# 飞书授权与令牌初始化

## 目标
- 完成 refresh_token 的首次获取和本地落盘。
- 处理 refresh_token 失效、授权失败、token 文件损坏等常见问题。
- 只沉淀操作知识，不改动 `code/main.py` 业务逻辑。

## 使用边界
- 只处理授权链路与 token 生命周期，不执行备份任务。
- 不回显 `APP_SECRET`、`access_token`、`refresh_token` 全值。
- 需要执行备份时，转交 `$feishu-backup-execution`。

## 执行流程
1. 检查 `code/get_initial_refresh_token.py` 的 `APP_ID`、`APP_SECRET`、`REDIRECT_URI`。
2. 确认 `scope` 包含 `offline_access`。
3. 运行授权脚本并复制授权链接。
4. 完成网页授权后，把完整回调 URL 粘贴回终端。
5. 由脚本自动写入 `code/token_store.json`。
6. 运行 `code/main.py` 验证可刷新 `user_access_token`。

## 最小检查清单
- `REDIRECT_URI` 与飞书后台安全设置完全一致。
- `code/token_store.json` 是可解析 JSON。
- `code/token_store.json` 中 `refresh_token` 非空且格式有效。
- 遇到 invalid refresh_token 报错时，重新走一次授权写入流程。

## 参考文档导航
- OAuth 全链路与参数说明：`references/oauth-flow.md`
- token_store 结构与校验规则：`references/token-store-contract.md`
- 授权常见问题排查：`references/auth-faq.md`

## 交接规则
- 令牌准备完成后，把执行任务交给 `$feishu-backup-execution`。
- 备份过程中出现错误码或导出失败时，交给 `$feishu-backup-troubleshooting`。
