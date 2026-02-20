# 权限与 scope 检查清单

## 1) 应用权限（后台）
最小应包含以下能力（按当前项目实现）：
- `drive:drive` 或 `drive:drive:readonly`
- `drive:file:download`
- `docs:document:export` 或 `drive:export:readonly`
- `wiki:node:retrieve`
- `wiki:wiki:readonly`
- `offline_access`（用于 refresh_token）

## 2) 用户授权 scope
- 授权链接中的 `scope` 必须覆盖目标 API 需要的权限。
- 若授权时报 20027，优先排查“申请权限”与“链接 scope”不一致。

## 3) 资源权限
- 使用 `user_access_token` 时，用户本身必须能访问目标文档。
- 文档未分享给用户或应用时会出现 `1069902` 类错误。

## 4) 排查顺序
1. 看错误码是否为权限类。
2. 核对后台权限是否已开通。
3. 核对授权 scope 是否包含目标权限。
4. 核对文档/知识库节点是否对该身份可读。
