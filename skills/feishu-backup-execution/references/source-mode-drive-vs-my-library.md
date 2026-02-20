# source 模式对比：drive vs my_library

## 配置位置
- `code/main.py` 顶部常量：
  - `BACKUP_SOURCE = "drive"` 或 `"my_library"`

## drive 模式
- 入口：云盘根目录。
- 递归方式：调用 `/drive/v1/files`，遇到 `folder` 继续递归。
- 适用场景：希望按云盘文件夹结构完整备份。

## my_library 模式
- 入口：`MY_LIBRARY_SPACE_ID = "my_library"`。
- 递归方式：调用 `/wiki/v2/spaces/my_library/nodes`。
- 节点处理：先取 `obj_token` + `obj_type` 再导出。
- 适用场景：优先覆盖“我的文档库”节点视角。

## 切换建议
1. 先明确业务要“云盘结构”还是“文档库结构”。
2. 修改 `BACKUP_SOURCE` 后再执行 `python3 code/main.py`。
3. 保持一次运行只使用一种 source，方便对账。
