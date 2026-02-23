from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from kb_index import KnowledgeBaseIndex

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Package 'mcp' is not installed. Install dependencies: pip install -r requirements.txt"
    ) from exc


DEFAULT_KB_DIR = Path(__file__).resolve().parent / "scrape_result"

mcp = FastMCP(
    name="Knowledge Base Semantic Search",
    instructions=(
        "HTTP MCP server for semantic search over local markdown knowledge base. "
        "All tools return structured JSON objects."
    ),
    json_response=True,
)

KB_INDEX: KnowledgeBaseIndex | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_for_logs(value: Any) -> Any:
    secret_markers = ("token", "secret", "password", "authorization", "api_key", "apikey")

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for k, v in value.items():
            if any(marker in k.lower() for marker in secret_markers):
                result[k] = "***"
            else:
                result[k] = _sanitize_for_logs(v)
        return result

    if isinstance(value, (list, tuple)):
        return [_sanitize_for_logs(v) for v in value]

    if isinstance(value, str):
        if len(value) > 400:
            return value[:400] + "...<truncated>"
        return value

    return value


def _log_tool_event(tool_name: str, status: str, inputs: dict[str, Any], error: str | None = None) -> None:
    event = {
        "timestamp": _utc_now(),
        "tool": tool_name,
        "inputs": _sanitize_for_logs(inputs),
        "status": status,
    }
    if error:
        event["error"] = error
    message = json.dumps(event, ensure_ascii=False)
    # Do not let logging failures break tool execution (common on Windows when stdout is detached).
    for stream in (sys.stdout, sys.stderr):
        try:
            print(message, file=stream, flush=True)
            return
        except OSError:
            continue
        except ValueError:
            continue


def _tool_logger(tool_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            inputs = dict(bound.arguments)
            _log_tool_event(tool_name, "started", inputs)
            try:
                result = func(*args, **kwargs)
                _log_tool_event(tool_name, "success", inputs)
                return result
            except Exception as exc:
                _log_tool_event(tool_name, "error", inputs, error=f"{type(exc).__name__}: {exc}")
                try:
                    traceback.print_exc()
                except (OSError, ValueError):
                    pass
                raise

        return wrapper

    return decorator


def _get_index() -> KnowledgeBaseIndex:
    if KB_INDEX is None:
        raise RuntimeError("Index is not initialized")
    return KB_INDEX


@mcp.tool()
@_tool_logger("search_knowledge")
def search_knowledge(
    query: str,
    top_k: int = 5,
    min_score: float = 0.08,
    deduplicate_docs: bool = True,
) -> dict[str, Any]:
    """
    Семантический поиск по базе знаний (markdown-файлы в scrape_result).

    Возвращает список наиболее релевантных фрагментов с оценкой похожести.
    """
    index = _get_index()
    payload = index.search(
        query=query,
        top_k=top_k,
        min_score=min_score,
        deduplicate_docs=deduplicate_docs,
    )
    if payload.get("error"):
        return {"status": "error", **payload}
    return {"status": "success", **payload}


@mcp.tool()
@_tool_logger("get_document")
def get_document(
    doc_id: str,
    include_content: bool = True,
    max_chars: int = 4000,
) -> dict[str, Any]:
    """
    Получить документ из базы знаний по имени файла (doc_id).

    Пример doc_id: 'NGINX.md'.
    """
    index = _get_index()
    payload = index.get_document(doc_id, include_content=include_content, max_chars=max_chars)
    if not payload.get("found"):
        return {"status": "error", "error": "document_not_found", **payload}
    return {"status": "success", **payload}


@mcp.tool()
@_tool_logger("list_documents")
def list_documents(
    limit: int = 20,
    offset: int = 0,
    name_contains: str | None = None,
) -> dict[str, Any]:
    """
    Получить список документов в базе знаний с пагинацией и фильтром по имени/заголовку.
    """
    index = _get_index()
    items = index.list_documents(limit=limit, offset=offset, name_contains=name_contains)
    return {"status": "success", **items}


@mcp.tool()
@_tool_logger("rebuild_index")
def rebuild_index() -> dict[str, Any]:
    """
    Пересобрать индекс семантического поиска после изменения файлов в scrape_result.
    """
    index = _get_index()
    stats = index.build()
    return {"status": "success", "message": "index_rebuilt", "index_stats": stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HTTP MCP server for semantic search over markdown KB")
    parser.add_argument(
        "--kb-dir",
        default=os.getenv("KB_DIR", str(DEFAULT_KB_DIR)),
        help="Path to knowledge base directory with .md files",
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8006")), help="Bind port")
    parser.add_argument("--chunk-size", type=int, default=int(os.getenv("KB_CHUNK_SIZE", "1400")))
    parser.add_argument("--chunk-overlap", type=int, default=int(os.getenv("KB_CHUNK_OVERLAP", "250")))
    parser.add_argument("--max-features", type=int, default=int(os.getenv("KB_MAX_FEATURES", "25000")))
    parser.add_argument("--svd-components", type=int, default=int(os.getenv("KB_SVD_COMPONENTS", "256")))
    return parser.parse_args()


def main() -> None:
    global KB_INDEX

    args = parse_args()
    KB_INDEX = KnowledgeBaseIndex(
        args.kb_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_features=args.max_features,
        svd_components=args.svd_components,
    )

    print(
        json.dumps(
            {
                "timestamp": _utc_now(),
                "event": "server_startup",
                "kb_dir": str(Path(args.kb_dir).resolve()),
                "host": args.host,
                "port": args.port,
                "transport": "streamable-http",
                "endpoint_hint": f"http://{args.host}:{args.port}/mcp",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    # Compatibility with installed MCP SDK variant where host/port are configured on settings.
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    stats = KB_INDEX.build()
    print(
        json.dumps(
            {"timestamp": _utc_now(), "event": "index_built", "status": "success", "index_stats": stats},
            ensure_ascii=False,
        ),
        flush=True,
    )

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
