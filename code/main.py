import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import requests

BASE_URL = "https://open.feishu.cn/open-apis"
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}
RETRYABLE_API_CODES = {1069923}
INVALID_REFRESH_TOKEN_CODES = {20026, 20037, 20064, 20073, 20074}

# =========================
# Required user config
# =========================
APP_ID = "<YOUR_APP_ID>"
APP_SECRET = "<YOUR_APP_SECRET>"

# Optional config
CODE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CODE_DIR.parent
TOKEN_STORE_FILE = str(CODE_DIR / "token_store.json")
OUTPUT_DIR = str(PROJECT_DIR / "feishu_backups")
RUN_SUBDIR_BY_DATE = True
BACKUP_SOURCE = "my_library"  # "drive" or "my_library"
MY_LIBRARY_SPACE_ID = "my_library"
VALID_BACKUP_SOURCES = {"drive", "my_library"}

REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
POLL_INTERVAL_SECONDS = 2
MAX_EXPORT_WAIT_SECONDS = 600


class FeishuApiError(Exception):
    pass


def validate_required_config() -> None:
    if APP_ID.strip() in {"", "<YOUR_APP_ID>"}:
        raise ValueError("请在脚本顶部配置 APP_ID")
    if APP_SECRET.strip() in {"", "<YOUR_APP_SECRET>"}:
        raise ValueError("请在脚本顶部配置 APP_SECRET")
    if not Path(TOKEN_STORE_FILE).exists():
        raise ValueError("未找到 token_store.json，请先运行 get_initial_refresh_token.py 完成授权")
    if BACKUP_SOURCE not in VALID_BACKUP_SOURCES:
        raise ValueError(f"BACKUP_SOURCE 必须是 {sorted(VALID_BACKUP_SOURCES)} 之一")


def load_refresh_token() -> str:
    token_file = Path(TOKEN_STORE_FILE)
    try:
        data = json.loads(token_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("未找到 token_store.json，请先运行 get_initial_refresh_token.py 完成授权")
    except Exception as exc:
        raise ValueError(f"token_store.json 解析失败，请重新运行 get_initial_refresh_token.py: {exc}")

    refresh_token = str(data.get("refresh_token", "")).strip()
    if not refresh_token:
        raise ValueError("token_store.json 中 refresh_token 为空，请重新运行 get_initial_refresh_token.py")
    if refresh_token.count(".") != 2:
        raise ValueError("token_store.json 中 refresh_token 格式无效，请重新运行 get_initial_refresh_token.py")
    return refresh_token


def refresh_user_access_token(refresh_token: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/authen/v2/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise FeishuApiError(f"刷新 user_access_token 请求失败: {exc}") from exc

    if response.status_code != 200:
        raise FeishuApiError(f"刷新 user_access_token 失败: HTTP {response.status_code}, body={response.text[:200]}")

    try:
        data = response.json()
    except ValueError as exc:
        raise FeishuApiError(f"刷新 user_access_token 返回非 JSON: {response.text[:200]}") from exc

    code = data.get("code", -1)
    if code != 0:
        if code in INVALID_REFRESH_TOKEN_CODES:
            raise FeishuApiError("refresh_token 已失效，请重新运行 get_initial_refresh_token.py 生成新 token_store.json")
        msg = data.get("error_description") or data.get("msg") or data.get("error") or "unknown error"
        raise FeishuApiError(f"刷新 user_access_token 失败: code={code}, msg={msg}")

    if not data.get("access_token") or not data.get("refresh_token"):
        raise FeishuApiError("刷新 user_access_token 成功但返回字段不完整")

    return data


def save_token_store(resp_json: Dict[str, Any]) -> None:
    token_file = Path(TOKEN_STORE_FILE)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "refresh_token": resp_json.get("refresh_token", ""),
        "access_token": resp_json.get("access_token", ""),
        "expires_in": resp_json.get("expires_in", 0),
        "updated_at": int(time.time()),
    }
    token_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_runtime_user_access_token() -> str:
    validate_required_config()
    refresh_token = load_refresh_token()
    token_resp = refresh_user_access_token(refresh_token)
    save_token_store(token_resp)
    print("[INFO] user_access_token 刷新成功")
    return str(token_resp["access_token"])


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[\\/:*?"<>|\x00-\x1F]', "_", name).strip()
    return sanitized or "untitled"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
        index += 1


class FeishuDriveBackup:
    def __init__(
        self,
        user_access_token: str,
        output_dir: Path,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        poll_interval_seconds: int = 2,
        max_export_wait_seconds: int = 600,
    ) -> None:
        self.user_access_token = user_access_token
        self.output_dir = output_dir
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.poll_interval_seconds = poll_interval_seconds
        self.max_export_wait_seconds = max_export_wait_seconds

        self.stats: Dict[str, int] = {
            "folders": 0,
            "files": 0,
            "exported": 0,
            "fallback_downloaded": 0,
            "failed": 0,
        }
        self.failures: List[str] = []

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.user_access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        absolute_url: bool = False,
        include_auth: bool = True,
    ) -> requests.Response:
        url = path_or_url if absolute_url else f"{BASE_URL}{path_or_url}"
        headers: Dict[str, str] = {}
        if include_auth:
            headers.update(self._headers)
        elif not stream:
            headers["Content-Type"] = "application/json; charset=utf-8"

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=self.timeout_seconds,
                    stream=stream,
                )

                retry_after = response.headers.get("Retry-After")
                if response.status_code in RETRYABLE_HTTP_STATUS:
                    if attempt < self.max_retries:
                        sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else attempt
                        print(f"[WARN] HTTP {response.status_code}, retry after {sleep_seconds}s: {url}")
                        time.sleep(sleep_seconds)
                        continue

                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait_seconds = attempt
                    print(f"[WARN] Request failed (attempt {attempt}/{self.max_retries}), retry in {wait_seconds}s: {url}")
                    time.sleep(wait_seconds)
                    continue
                break

        if last_error is not None:
            raise FeishuApiError(f"Request failed after {self.max_retries} attempts: {url} ({last_error})")
        raise FeishuApiError(f"Request failed after {self.max_retries} attempts: {url}")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        last_response_text = ""
        for attempt in range(1, self.max_retries + 1):
            response = self._request(method, path, params=params, json_body=json_body, stream=False)
            last_response_text = response.text

            try:
                payload = response.json()
            except ValueError:
                payload = {"code": -1, "msg": f"Non-JSON response: {response.text[:200]}"}

            code = payload.get("code", 0)
            retriable = response.status_code in RETRYABLE_HTTP_STATUS or code in RETRYABLE_API_CODES
            if response.status_code < 400 and code == 0:
                return payload

            message = payload.get("msg") or f"HTTP {response.status_code}"
            if retriable and attempt < self.max_retries:
                wait_seconds = attempt
                print(f"[WARN] API failed (code={code}, attempt {attempt}/{self.max_retries}), retry in {wait_seconds}s: {message}")
                time.sleep(wait_seconds)
                continue

            raise FeishuApiError(f"API request failed: {message} (code={code}, http={response.status_code})")

        raise FeishuApiError(f"API request failed with no response payload: {last_response_text[:200]}")

    def _request_binary(
        self,
        method: str,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        absolute_url: bool = False,
        include_auth: bool = True,
    ) -> requests.Response:
        response = self._request(
            method,
            path_or_url,
            params=params,
            stream=True,
            absolute_url=absolute_url,
            include_auth=include_auth,
        )

        if response.status_code >= 400:
            preview = response.text[:200] if response.text else ""
            raise FeishuApiError(
                f"Binary download failed: http={response.status_code}, body={preview}"
            )
        return response

    def list_folder_files(
        self,
        folder_token: Optional[str],
        page_token: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        params: Dict[str, Any] = {"page_size": 200}
        if folder_token:
            params["folder_token"] = folder_token
        if page_token:
            params["page_token"] = page_token

        payload = self._request_json("GET", "/drive/v1/files", params=params)
        data = payload.get("data", {})
        files = data.get("files", [])
        has_more = bool(data.get("has_more", False))
        next_page_token = data.get("next_page_token") or data.get("page_token")
        return files, has_more, next_page_token

    def iter_folder_files(self, folder_token: Optional[str]) -> Iterator[Dict[str, Any]]:
        def fetch_page(page_token: Optional[str]) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
            return self.list_folder_files(folder_token, page_token)

        yield from self._iter_paginated(
            fetch_page=fetch_page,
            missing_token_warn="[WARN] has_more=true but no next page token returned, stopping pagination to avoid infinite loop",
        )

    def list_my_library_nodes(
        self,
        parent_node_token: Optional[str],
        page_token: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        params: Dict[str, Any] = {"page_size": 50}
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        if page_token:
            params["page_token"] = page_token

        payload = self._request_json(
            "GET",
            f"/wiki/v2/spaces/{MY_LIBRARY_SPACE_ID}/nodes",
            params=params,
        )
        data = payload.get("data", {})
        items = data.get("items", [])
        has_more = bool(data.get("has_more", False))
        next_page_token = data.get("page_token")
        return items, has_more, next_page_token

    def iter_my_library_nodes(self, parent_node_token: Optional[str]) -> Iterator[Dict[str, Any]]:
        def fetch_page(page_token: Optional[str]) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
            return self.list_my_library_nodes(parent_node_token, page_token)

        yield from self._iter_paginated(
            fetch_page=fetch_page,
            missing_token_warn="[WARN] has_more=true but no page token returned, stopping pagination to avoid infinite loop",
        )

    def _iter_paginated(
        self,
        fetch_page: Callable[[Optional[str]], Tuple[List[Dict[str, Any]], bool, Optional[str]]],
        missing_token_warn: str,
    ) -> Iterator[Dict[str, Any]]:
        page_token: Optional[str] = None
        while True:
            items, has_more, next_page_token = fetch_page(page_token)
            for node in items:
                yield node
            if not has_more:
                break
            if not next_page_token:
                print(missing_token_warn)
                break
            page_token = next_page_token

    @staticmethod
    def library_node_to_file_info(node: Dict[str, Any]) -> Dict[str, Any]:
        obj_token = node.get("obj_token")
        obj_type = node.get("obj_type")
        if not obj_token or not obj_type:
            raise FeishuApiError("Library node missing obj_token/obj_type")
        return {
            "token": obj_token,
            "type": obj_type,
            "name": node.get("title") or obj_token,
        }

    @staticmethod
    def export_extension_for_type(file_type: str) -> str:
        if file_type in {"doc", "docx"}:
            return "docx"
        if file_type in {"sheet", "bitable"}:
            return "xlsx"
        if file_type == "slides":
            return "pptx"
        return "pdf"

    def create_export_task(self, file_token: str, file_type: str, extension: str) -> str:
        payload = {
            "token": file_token,
            "type": file_type,
            "file_extension": extension,
        }
        resp = self._request_json("POST", "/drive/v1/export_tasks", json_body=payload)
        ticket = (resp.get("data") or {}).get("ticket")
        if not ticket:
            raise FeishuApiError("Export task created but no ticket returned")
        return ticket

    def resolve_wiki_node(self, wiki_token: str) -> Tuple[str, str]:
        resp = self._request_json(
            "GET",
            "/wiki/v2/spaces/get_node",
            params={"token": wiki_token},
        )
        data = resp.get("data") or {}
        node = data.get("node") or data
        obj_token = node.get("obj_token")
        obj_type = node.get("obj_type")
        if not obj_token or not obj_type:
            raise FeishuApiError("Wiki node resolved without obj_token/obj_type")
        return obj_token, obj_type

    def query_export_task(self, ticket: str, file_token: str) -> Dict[str, Any]:
        resp = self._request_json(
            "GET",
            f"/drive/v1/export_tasks/{ticket}",
            params={"token": file_token},
        )
        data = resp.get("data") or {}
        result = data.get("result") or {}

        # Compatibility with possible older schema.
        if not result and data:
            result = data

        return result

    @staticmethod
    def parse_export_status(result: Dict[str, Any]) -> Tuple[str, str]:
        if "job_status" in result:
            status_code = result.get("job_status")
            if status_code in (1, 2):
                return "processing", ""
            if status_code == 0:
                return "success", ""
            return "failed", str(result.get("job_error_msg") or f"job_status={status_code}")

        status = str(result.get("status", "")).lower()
        if status in {"processing", "running", "queued", "pending"}:
            return "processing", ""
        if status in {"success", "succeeded", "done"}:
            return "success", ""
        if status in {"failed", "error"}:
            return "failed", str(result.get("error_msg") or "export failed")

        return "processing", ""

    def wait_for_export(self, ticket: str, file_token: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        start = time.time()
        while True:
            result = self.query_export_task(ticket, file_token)
            status, err = self.parse_export_status(result)

            if status == "success":
                exported_file_token = result.get("file_token")
                exported_url = None

                file_info = result.get("file") or {}
                if not exported_file_token:
                    exported_file_token = file_info.get("token")
                exported_url = file_info.get("url") or result.get("url")

                file_name = result.get("file_name") or file_info.get("name")
                return exported_file_token, exported_url, file_name

            if status == "failed":
                raise FeishuApiError(f"Export task failed: {err}")

            if time.time() - start > self.max_export_wait_seconds:
                raise FeishuApiError(
                    f"Export task timeout after {self.max_export_wait_seconds}s (ticket={ticket})"
                )

            time.sleep(self.poll_interval_seconds)

    def download_export_file(self, exported_file_token: Optional[str], exported_url: Optional[str]) -> requests.Response:
        if exported_file_token:
            return self._request_binary(
                "GET",
                f"/drive/v1/export_tasks/file/{exported_file_token}/download",
            )
        if exported_url:
            # Some older responses may return a direct download URL.
            return self._request_binary(
                "GET",
                exported_url,
                absolute_url=True,
                include_auth=False,
            )
        raise FeishuApiError("No exported file token or URL returned")

    def download_regular_file(self, file_token: str) -> requests.Response:
        return self._request_binary("GET", f"/drive/v1/files/{file_token}/download")

    @staticmethod
    def build_export_filename(original_name: str, extension: str) -> str:
        sanitized = sanitize_filename(original_name)
        suffix = f".{extension.lower()}"

        # Keep clean names like "foo.docx" instead of "foo.docx.docx".
        if sanitized.lower().endswith(suffix):
            return sanitized

        stem = Path(sanitized).stem if Path(sanitized).suffix else sanitized
        return f"{stem}{suffix}"

    @staticmethod
    def stream_to_file(response: requests.Response, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)

    def export_and_save(self, file_info: Dict[str, Any], local_dir: Path) -> None:
        file_token = file_info["token"]
        file_type = file_info["type"]
        original_name = file_info.get("name") or file_token

        if file_type == "wiki":
            file_token, file_type = self.resolve_wiki_node(file_token)

        target_ext = self.export_extension_for_type(file_type)
        target_name = self.build_export_filename(original_name, target_ext)
        target_path = unique_path(local_dir / target_name)

        ticket = self.create_export_task(file_token, file_type, target_ext)
        exported_file_token, exported_url, _ = self.wait_for_export(ticket, file_token)
        response = self.download_export_file(exported_file_token, exported_url)
        self.stream_to_file(response, target_path)
        self.stats["exported"] += 1
        print(f"[OK] Exported: {target_path}")

    def direct_download_and_save(self, file_info: Dict[str, Any], local_dir: Path) -> None:
        file_token = file_info["token"]
        original_name = sanitize_filename(file_info.get("name") or file_token)
        if not Path(original_name).suffix:
            original_name = f"{original_name}.bin"
        target_path = unique_path(local_dir / original_name)

        response = self.download_regular_file(file_token)
        self.stream_to_file(response, target_path)
        self.stats["fallback_downloaded"] += 1
        print(f"[WARN] Fallback direct download (non-PDF): {target_path}")

    def process_file(self, file_info: Dict[str, Any], local_dir: Path) -> None:
        self.stats["files"] += 1

        file_name = file_info.get("name", "<unknown>")
        file_type = file_info.get("type", "<unknown>")
        file_token = file_info.get("token", "<unknown>")

        print(f"[INFO] Processing file: {file_name} (type={file_type}, token={file_token})")

        try:
            self.export_and_save(file_info, local_dir)
        except Exception as export_error:
            if file_type == "file":
                try:
                    self.direct_download_and_save(file_info, local_dir)
                    return
                except Exception as download_error:
                    self.stats["failed"] += 1
                    self.failures.append(
                        f"{file_name} ({file_token}) export_error={export_error}; download_error={download_error}"
                    )
                    print(f"[ERROR] Failed file: {file_name} ({file_token})")
                    return

            self.stats["failed"] += 1
            self.failures.append(f"{file_name} ({file_token}) export_error={export_error}")
            print(f"[ERROR] Failed file: {file_name} ({file_token})")

    def process_folder(self, folder_token: Optional[str], local_dir: Path) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)

        for file_info in self.iter_folder_files(folder_token):
            file_type = file_info.get("type")
            file_name = file_info.get("name") or file_info.get("token") or "untitled"
            safe_name = sanitize_filename(file_name)

            if file_type == "folder":
                self.stats["folders"] += 1
                subfolder = unique_path(local_dir / safe_name)
                print(f"[INFO] Enter folder: {subfolder}")
                self.process_folder(file_info.get("token"), subfolder)
                continue

            self.process_file(file_info, local_dir)

    def process_my_library_node(self, node: Dict[str, Any], local_dir: Path) -> None:
        node_name = node.get("title") or node.get("obj_token") or "untitled"
        node_token = node.get("node_token") or "<unknown>"
        safe_name = sanitize_filename(node_name)

        try:
            file_info = self.library_node_to_file_info(node)
            self.process_file(file_info, local_dir)
        except Exception as exc:
            self.stats["failed"] += 1
            self.failures.append(f"{node_name} ({node_token}) node_error={exc}")
            print(f"[ERROR] Failed node: {node_name} ({node_token})")

        if not node.get("has_child"):
            return

        child_parent_token = node.get("node_token")
        if not child_parent_token:
            self.stats["failed"] += 1
            self.failures.append(f"{node_name} ({node_token}) missing node_token for child traversal")
            print(f"[ERROR] Failed node child traversal: {node_name} ({node_token})")
            return

        self.stats["folders"] += 1
        subfolder = unique_path(local_dir / safe_name)
        print(f"[INFO] Enter my_library node: {subfolder}")
        subfolder.mkdir(parents=True, exist_ok=True)
        for child_node in self.iter_my_library_nodes(parent_node_token=child_parent_token):
            self.process_my_library_node(child_node, subfolder)

    def process_my_library(self, local_dir: Path) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        for root_node in self.iter_my_library_nodes(parent_node_token=None):
            self.process_my_library_node(root_node, local_dir)

    def run(self) -> int:
        print(f"[INFO] Start Feishu backup, source={BACKUP_SOURCE}")
        if BACKUP_SOURCE == "drive":
            print("[INFO] Source mode: drive homepage")
            self.process_folder(folder_token=None, local_dir=self.output_dir)
        else:
            print(f"[INFO] Source mode: my_library (space_id={MY_LIBRARY_SPACE_ID})")
            self.process_my_library(local_dir=self.output_dir)

        print("\n[SUMMARY]")
        print(f"Output dir: {self.output_dir}")
        print(f"Folders visited: {self.stats['folders']}")
        print(f"Files processed: {self.stats['files']}")
        print(f"Exported files: {self.stats['exported']}")
        print(f"Fallback downloaded files: {self.stats['fallback_downloaded']}")
        print(f"Failed files: {self.stats['failed']}")

        if self.failures:
            print("\n[FAILED LIST]")
            for item in self.failures:
                print(f"- {item}")
            return 2
        return 0


def main() -> None:
    try:
        user_access_token = get_runtime_user_access_token()
        output_dir = Path(OUTPUT_DIR)
        if RUN_SUBDIR_BY_DATE:
            output_dir = output_dir / time.strftime("%Y-%m-%d_%H-%M-%S")

        backup = FeishuDriveBackup(
            user_access_token=user_access_token,
            output_dir=output_dir,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
            poll_interval_seconds=POLL_INTERVAL_SECONDS,
            max_export_wait_seconds=MAX_EXPORT_WAIT_SECONDS,
        )
        exit_code = backup.run()
        sys.exit(exit_code)
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
