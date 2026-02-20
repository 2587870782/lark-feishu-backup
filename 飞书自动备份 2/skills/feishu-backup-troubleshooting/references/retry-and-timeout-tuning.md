# 重试与超时调参

## 代码位置
- `code/main.py`

## 可调参数
- `MAX_RETRIES`
- `REQUEST_TIMEOUT_SECONDS`
- `POLL_INTERVAL_SECONDS`
- `MAX_EXPORT_WAIT_SECONDS`

## 调参顺序
1. 先确认是否权限或 token 问题，避免无效重试。
2. 对 429/5xx 增加 `MAX_RETRIES`。
3. 对慢任务增加 `MAX_EXPORT_WAIT_SECONDS`。
4. 对网络慢请求增加 `REQUEST_TIMEOUT_SECONDS`。
5. 对频繁轮询导致压力问题提高 `POLL_INTERVAL_SECONDS`。

## 复验方法
1. 调整单个参数后执行一次完整备份。
2. 比较 `Failed files`、重试日志、总耗时。
3. 仅保留有效参数变更，避免一次改多个导致不可归因。
