# file 类型降级下载边界

## 触发条件
在 `code/main.py` 中，处理文件时先尝试导出：
- `export_and_save(...)` 失败后，
- 若 `file_type == "file"`，进入 `direct_download_and_save(...)` 降级直传下载。

## 成功表现
- 统计项 `fallback_downloaded` 增加。
- 日志包含 `Fallback direct download (non-PDF)`。

## 失败表现
- 同时记录导出失败与直传失败信息：
  - `export_error=...`
  - `download_error=...`
- 该文件计入 `Failed files`。

## 文件命名规则
- 原文件名无扩展名时自动补 `.bin`。
- 与已有文件重名时自动追加 ` (1)`、` (2)` 等后缀。

## 排查建议
1. 先确认是否真的为 `type=file`。
2. 再检查 `drive:file:download` 权限是否具备。
3. 再检查目标资源是否允许当前身份下载。
