# OAuth 流程（授权到落盘）

## 适用范围
- 适用于首次拿 `refresh_token`。
- 适用于 `refresh_token` 失效后的重新授权。

## 前置条件
- 在飞书开放平台开通必要 scope。
- 在 `code/get_initial_refresh_token.py` 填好：
  - `APP_ID`
  - `APP_SECRET`
  - `REDIRECT_URI`
- 确保 `scope` 包含 `offline_access`。

## 步骤
1. 在仓库根目录运行：
   ```bash
   python3 code/get_initial_refresh_token.py
   ```
2. 打开脚本输出的授权链接并完成授权。
3. 复制浏览器最终回调 URL（包含 `code=`）。
4. 把完整回调 URL 粘贴回终端。
5. 脚本自动把 `refresh_token` 写入 `code/token_store.json`。
6. 运行：
   ```bash
   python3 code/main.py
   ```
   观察是否出现 `user_access_token 刷新成功`。

## 关键约束
- 授权码 `code` 有效期短且一次性使用。
- 回调地址不一致会导致换 token 失败。
- `refresh_token` 失效时不能靠重试恢复，必须重新授权生成。
