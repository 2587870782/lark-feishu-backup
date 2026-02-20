# 备份执行 Runbook

## 1) 执行前检查
1. 确认已安装依赖：
   ```bash
   python3 -m pip install -r code/requirements.txt
   ```
2. 确认 `code/token_store.json` 已存在且可解析。
3. 确认 `code/main.py` 中 `APP_ID` 和 `APP_SECRET` 已配置。

## 2) 执行备份
在仓库根目录运行：
```bash
python3 code/main.py
```

## 3) 观察关键输出
- `[INFO] Start Feishu backup`
- `Source mode: drive` 或 `Source mode: my_library`
- `[SUMMARY]` 段落中的统计项

## 4) 验收
- 退出码 `0`：无失败文件。
- 退出码 `2`：有失败文件，检查 `[FAILED LIST]`。
- 退出码 `1`：运行级错误，优先检查授权和配置。

## 5) 结果目录
- 默认输出目录：`feishu_backups/`
- 默认会创建按时间命名的子目录（如 `2026-02-15_21-00-28`）。
