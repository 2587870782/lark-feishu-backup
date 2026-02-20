# lark-feishu-backup
基于飞书官方 API 实现的云文档批量下载工具。突破客户端仅支持逐个下载的限制，支持一键导出 Word (.docx)、PPT (.pptx) 及 Excel (.xlsx) 格式，配置简单。


# 飞书云文档全量备份（基于 user_access_token）

这是一个用于**全量备份飞书云文档**的 Python 脚本项目。程序会从指定入口递归遍历文档节点，并把可导出的资源下载到本地目录，适合个人资料归档、迁移留存与周期性离线备份。

## == 免责声明：==

==本工具仅供学习交流使用，使用者在下载企业内部文档时，需确保已获得相关授权。因违规使用导致的账号封禁或法律责任由使用者自行承担。==

## 项目定位

- 使用 `user_access_token` 身份访问用户可见文档。
- 支持从以下入口备份：
  - 飞书云盘根目录（`drive`）
  - 我的文档库（`my_library`）
- 目标是“可运行、可恢复、可排障”的脚本化备份，不是 GUI 产品。

## 功能说明

- 递归遍历目录与知识库节点。
- 自动按文档类型导出：
  - `doc` / `docx` -> `docx`
  - `sheet` / `bitable` -> `xlsx`
  - `slides` -> `pptx`
  - 其他类型默认尝试导出为 `pdf`
- 对 `wiki` 类型先解析真实 `obj_type`/`obj_token` 再导出。
- 对普通附件（`type=file`）在导出失败时自动降级为直传下载，避免任务中断。
- 内置请求重试、导出轮询和失败清单输出。

## 功能边界

- 当前为单进程串行执行，不做并发下载。
- 不做增量比较与去重策略，按每次运行结果输出文件。
- 不包含数据库、Web 服务或前端页面。

## 目录结构

```text
.
├── README.md
├── app.manifest.json
├── index.meta.json
├── code/
│   ├── main.py
│   ├── get_initial_refresh_token.py
│   └── requirements.txt
├── skills/
│   └── ...
└── 技术文档/
    └── ...
```

关键文件说明：
- `code/main.py`：主备份脚本。
- `code/get_initial_refresh_token.py`：首次授权并写入 `token_store.json`。
- `app.manifest.json`：飞书应用权限清单（保留用于权限核对）。
- `index.meta.json`：运行入口元信息（保留用于工程元数据）。
- `skills/`：自动化技能与排障参考（保留）。
- `技术文档/`：接口参考资料（保留）。

## 运行环境

- Python 3.10+
- macOS / Linux / Windows（脚本本身跨平台）
- 可访问飞书开放平台 API 的网络环境

## 运行前准备

### 1) 创建并配置飞书应用

在飞书开放平台创建应用后，至少确保已开通并授权以下范围（按实际场景可增减）：

- `offline_access`
- `drive:drive` / `drive:drive:readonly`
- `drive:file:download`
- `docs:document:export` 或 `drive:export:readonly`
- `wiki:node:retrieve`
- `wiki:wiki:readonly`

同时在应用安全设置里配置 OAuth 回调地址（`REDIRECT_URI`）。

### 2) 填写脚本顶部配置（占位符改为真实值）

编辑 `code/get_initial_refresh_token.py`：

- `APP_ID = "<YOUR_APP_ID>"`
- `APP_SECRET = "<YOUR_APP_SECRET>"`
- `REDIRECT_URI = "https://example.com/api/oauth/callback"`（替换为你在飞书后台配置的地址）

编辑 `code/main.py`：

- `APP_ID = "<YOUR_APP_ID>"`
- `APP_SECRET = "<YOUR_APP_SECRET>"`

## 安装依赖

```bash
cd code
python3 -m pip install -r requirements.txt
```

## 首次授权并生成 token_store.json

```bash
cd code
python3 get_initial_refresh_token.py
```

流程说明：
1. 脚本打印授权链接；
2. 浏览器完成授权；
3. 把最终回调 URL 粘贴回终端；
4. 脚本自动生成 `code/token_store.json`（包含 `refresh_token`）。

## 执行备份

```bash
cd code
python3 main.py
```

`main.py` 会读取 `token_store.json` 中的 `refresh_token`，自动刷新 `user_access_token` 后执行备份。

## 运行配置（main.py 顶部常量）

- `TOKEN_STORE_FILE`：token 文件路径（默认 `code/token_store.json`）
- `OUTPUT_DIR`：备份输出根目录（默认 `<项目目录>/feishu_backups`）
- `RUN_SUBDIR_BY_DATE`：是否按时间创建子目录（默认 `True`）
- `BACKUP_SOURCE`：入口模式，`"drive"` 或 `"my_library"`
- `MY_LIBRARY_SPACE_ID`：默认 `"my_library"`
- `REQUEST_TIMEOUT_SECONDS`：单次请求超时秒数
- `MAX_RETRIES`：请求重试次数
- `POLL_INTERVAL_SECONDS`：导出任务轮询间隔
- `MAX_EXPORT_WAIT_SECONDS`：单文件导出最长等待时间

## 输出与退出码

脚本结束会输出汇总：

- 遍历文件夹数
- 处理文件数
- 导出成功数
- 降级直传下载数
- 失败数与失败清单

退出码：

- `0`：全部成功
- `2`：部分失败（有失败清单）
- `1`：运行异常（配置、授权或请求错误等）

## 常见问题

### 1) 提示未找到 token_store.json
先执行：

```bash
cd code
python3 get_initial_refresh_token.py
```

### 2) 提示 refresh_token 无效或失效
重新走一次授权流程，覆盖生成新的 `token_store.json`。

### 3) 403 无权限
检查两层权限：
- 应用 scope 是否已开通并获授权；
- 当前用户是否有目标文档访问权限。

### 4) 429 限频或导出超时
可适当调大：
- `MAX_RETRIES`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_EXPORT_WAIT_SECONDS`

## 安全与开源建议

- 不要提交真实 `APP_SECRET`、`refresh_token`、`access_token`。
- `code/token_store.json` 仅用于本地运行，禁止入库。
- 建议在开源发布前轮换一次飞书应用密钥和已签发 token。
- 如曾泄露凭据，建议同时在飞书后台撤销旧授权并重新授权。

## 开源发布说明

当前仓库保留以下辅助内容，便于后续维护与排障：

- `skills/`：执行/排障技能说明
- `技术文档/`：API 参考资料
- `app.manifest.json`：应用权限配置清单
- `index.meta.json`：工程入口元信息

这些文件不会影响主脚本运行，但有助于协作与问题定位。


