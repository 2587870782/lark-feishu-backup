# 输出统计与退出码

## 统计字段（`[SUMMARY]`）
- `Folders visited`
- `Files processed`
- `Exported files`
- `Fallback downloaded files`
- `Failed files`

## 退出码语义
- `0`：执行完成且无失败文件。
- `2`：执行完成但存在失败文件（会打印 `[FAILED LIST]`）。
- `1`：运行级异常（配置、授权、请求等导致流程中断）。

## 判读建议
1. 先看退出码确定大类。
2. 再看 `Failed files` 与失败清单定位具体对象。
3. 若存在 `Fallback downloaded files`，说明部分 `file` 类型走了降级直传。
