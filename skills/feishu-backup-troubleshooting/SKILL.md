---
name: feishu-backup-troubleshooting
description: 聚焦飞书备份过程的错误分类与排障决策，覆盖授权失败、权限不足、限频超时、导出任务异常、分页异常和 file 类型降级下载确认。 当出现错误码（如 1069902、1069923）或“导出失败”时使用。
---

# 飞书备份排障决策

## 目标
- 以“先定位再修复”的方式处理备份失败。
- 给出可执行的恢复动作和复验步骤。
- 保持现有备份脚本逻辑不变，只调整运行与授权侧配置。

## 故障分层
- 授权类：无法获取或刷新 token。
- 权限类：应用 scope 或资源权限不足。
- 限频与稳定性：429、超时、重试耗尽。
- 导出任务类：任务失败、导出文件不可下载。
- 下载类：`file` 类型触发降级直传仍失败。

## 排障顺序
1. 先看 HTTP 状态与 API `code/msg`。
2. 再判断是 token 问题、scope 问题还是文档资源权限问题。
3. 再决定是否调大重试/超时参数。
4. 最后确认是否属于业务侧限制（文档过大、内容无权限等）。

## 快速入口
- 错误码映射：`references/error-matrix.md`
- 重试与超时调参：`references/retry-and-timeout-tuning.md`
- scope 与资源权限核查：`references/permission-scope-checklist.md`
- 降级下载行为边界：`references/fallback-download-cases.md`

## 升级处理条件
- 同一文件连续重试后稳定失败。
- 多文件同时出现权限拒绝且已完成 scope/分享检查。
- 导出任务长期卡在 processing 或频繁 timeout。
- 出现无法解释的响应结构变化或分页异常。
