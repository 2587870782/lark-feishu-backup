---
name: feishu-backup-execution
description: 指导稳定执行现有飞书全量备份流程（code/main.py），覆盖依赖检查、source 模式切换（drive 或 my_library）、运行参数调优、输出统计与退出码判读。 当用户提出“运行全量备份”“切换 source”“解释输出目录、统计信息或退出码”时使用。
---

# 飞书备份执行与验收

## 目标
- 在不改业务逻辑的前提下稳定执行 `code/main.py`。
- 解释运行结果并给出验收结论。
- 把故障排查交给 `$feishu-backup-troubleshooting`。

## 使用边界
- 执行现有脚本，不重构备份逻辑。
- 优先使用仓库现有路径和配置，不引入全局安装依赖。

## 执行主流程
1. 检查依赖是否已安装（`code/requirements.txt`）。
2. 检查 `code/token_store.json` 是否存在且可用。
3. 确认 source 模式（`drive` 或 `my_library`）。
4. 运行 `code/main.py` 执行备份。
5. 读取 `[SUMMARY]` 和失败列表，给出验收结论。

## 参数与模式入口
- source 模式差异：`references/source-mode-drive-vs-my-library.md`
- 运行参数与超时重试：`references/env-and-runtime.md`
- 标准执行 runbook：`references/runbook.md`
- 输出统计与退出码判读：`references/output-and-exit-codes.md`

## 验收口径
- 成功：退出码 `0`，且 `Failed files: 0`。
- 部分成功：退出码 `2`，存在失败清单。
- 运行失败：退出码 `1`，通常是配置或授权前置问题。

## 交接规则
- 遇到权限不足、限频、导出失败或降级下载异常时，转交 `$feishu-backup-troubleshooting`。
