# 运行参数与调优

## 当前实现口径
- 现版本以 `code/main.py` 顶部常量为准。
- 若 README 提到环境变量，请以代码实装行为为准。

## 关键参数（`code/main.py`）
- `REQUEST_TIMEOUT_SECONDS`：单次请求超时秒数。
- `MAX_RETRIES`：请求重试次数。
- `POLL_INTERVAL_SECONDS`：导出任务轮询间隔。
- `MAX_EXPORT_WAIT_SECONDS`：单个导出任务最长等待秒数。
- `OUTPUT_DIR`：本地输出目录。
- `RUN_SUBDIR_BY_DATE`：是否自动创建时间子目录。

## 调优建议
- 网络抖动或 429 较多：先提高 `MAX_RETRIES`。
- 导出任务经常 timeout：提高 `MAX_EXPORT_WAIT_SECONDS`。
- 单次请求易超时：提高 `REQUEST_TIMEOUT_SECONDS`。
- 轮询频率过高：适当提高 `POLL_INTERVAL_SECONDS` 降压。

## 注意
- 调参属于运行策略调整，不属于备份逻辑重构。
- 调参后保留一轮完整运行记录，便于比较效果。
