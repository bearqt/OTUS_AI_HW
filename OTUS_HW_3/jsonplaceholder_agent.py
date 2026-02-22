import json
from typing import Any, Dict, Literal, Optional

import requests
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


BASE_URL = "https://jsonplaceholder.typicode.com"
ALLOWED_RESOURCES = {"posts", "users", "todos", "comments", "albums", "photos"}


class JsonPlaceholderToolInput(BaseModel):
    operation: Literal["create", "get", "update", "list", "stats"] = Field(
        description="Операция: create/get/update/list/stats"
    )
    resource: str = Field(
        description="Ресурс JSONPlaceholder: posts, users, todos, comments, albums, photos"
    )
    resource_id: Optional[int] = Field(
        default=None,
        description="ID сущности для get/update",
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON-данные для create/update",
    )
    query: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query-параметры для list, например {'userId': 1}",
    )


def _response_payload(
    *,
    status: str,
    operation: str,
    resource: str,
    resource_id: Optional[int] = None,
    http_status: Optional[int] = None,
    data: Any = None,
    error: Optional[str] = None,
) -> str:
    result = {
        "status": status,
        "operation": operation,
        "resource": resource,
        "resource_id": resource_id,
        "http_status": http_status,
        "data": data,
        "error": error,
    }
    return json.dumps(result, ensure_ascii=False)


@tool(args_schema=JsonPlaceholderToolInput)
def jsonplaceholder_api(
    operation: str,
    resource: str,
    resource_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
) -> str:
    """Выполняет операции create/get/update/list/stats над API JSONPlaceholder."""
    operation = operation.strip().lower()
    resource = resource.strip().lower()
    if resource not in ALLOWED_RESOURCES:
        return _response_payload(
            status="error",
            operation=operation,
            resource=resource,
            resource_id=resource_id,
            error=f"Неподдерживаемый ресурс '{resource}'.",
        )

    try:
        if operation == "create":
            url = f"{BASE_URL}/{resource}"
            response = requests.post(url, json=payload or {}, timeout=20)
            response.raise_for_status()
            return _response_payload(
                status="success",
                operation=operation,
                resource=resource,
                http_status=response.status_code,
                data=response.json(),
            )

        if operation == "get":
            if resource_id is None:
                return _response_payload(
                    status="error",
                    operation=operation,
                    resource=resource,
                    error="Для операции get требуется resource_id.",
                )
            url = f"{BASE_URL}/{resource}/{resource_id}"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            return _response_payload(
                status="success",
                operation=operation,
                resource=resource,
                resource_id=resource_id,
                http_status=response.status_code,
                data=response.json(),
            )

        if operation == "update":
            if resource_id is None:
                return _response_payload(
                    status="error",
                    operation=operation,
                    resource=resource,
                    error="Для операции update требуется resource_id.",
                )
            url = f"{BASE_URL}/{resource}/{resource_id}"
            response = requests.patch(url, json=payload or {}, timeout=20)
            response.raise_for_status()
            return _response_payload(
                status="success",
                operation=operation,
                resource=resource,
                resource_id=resource_id,
                http_status=response.status_code,
                data=response.json(),
            )

        if operation == "list":
            url = f"{BASE_URL}/{resource}"
            response = requests.get(url, params=query or {}, timeout=20)
            response.raise_for_status()
            data = response.json()
            return _response_payload(
                status="success",
                operation=operation,
                resource=resource,
                http_status=response.status_code,
                data={
                    "count": len(data) if isinstance(data, list) else None,
                    "items": data,
                },
            )

        if operation == "stats":
            url = f"{BASE_URL}/{resource}"
            response = requests.get(url, params=query or {}, timeout=20)
            response.raise_for_status()
            data = response.json()
            stats: Dict[str, Any] = {
                "total_count": len(data) if isinstance(data, list) else None,
            }
            if resource == "todos" and isinstance(data, list):
                completed = sum(1 for item in data if item.get("completed") is True)
                stats["completed_count"] = completed
                stats["pending_count"] = len(data) - completed
            if resource == "posts" and isinstance(data, list):
                user_ids = {item.get("userId") for item in data if "userId" in item}
                stats["unique_user_count"] = len(user_ids)

            return _response_payload(
                status="success",
                operation=operation,
                resource=resource,
                http_status=response.status_code,
                data=stats,
            )

        return _response_payload(
            status="error",
            operation=operation,
            resource=resource,
            resource_id=resource_id,
            error=f"Неподдерживаемая операция '{operation}'.",
        )

    except requests.RequestException as exc:
        http_status = getattr(getattr(exc, "response", None), "status_code", None)
        return _response_payload(
            status="error",
            operation=operation,
            resource=resource,
            resource_id=resource_id,
            http_status=http_status,
            error=str(exc),
        )


SYSTEM_PROMPT = """
Ты API-оператор для JSONPlaceholder (https://jsonplaceholder.typicode.com).

Цель:
- Понимать запросы пользователя на русском языке.
- Для работы с данными всегда использовать tool `jsonplaceholder_api`.
- Возвращать ответ СТРОГО в JSON на русском языке.

Что ты умеешь:
- create, get, update, list, stats для ресурсов JSONPlaceholder.

Ограничения:
- Не выдумывай данные и не утверждай, что API выполнилось успешно без вызова tool.
- JSONPlaceholder — тестовое API: изменения могут быть фиктивными и не сохраняться.
- Если данных недостаточно (например, нет id), попроси уточнение.
- Не используй операции delete.

Правила вызова tool:
- Выбирай `resource` из: posts, users, todos, comments, albums, photos.
- Для update используй PATCH.
- Для list/stat можно передавать фильтры через `query`.

Формат финального ответа (строго JSON):
{
  "status": "success|error|need_clarification",
  "message": "краткое описание результата",
  "performed_operations": [
    {
      "operation": "create|get|update|list|stats",
      "resource": "string",
      "resource_id": 1,
      "result_status": "success|error"
    }
  ],
  "result": {}
}
""".strip()


def build_agent(
    model_name: str = "openai/gpt-4o-mini",
    temperature: float = 0,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Any:
    chat_kwargs: Dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
    }
    if base_url:
        chat_kwargs["base_url"] = base_url
    if api_key:
        chat_kwargs["api_key"] = api_key

    model = ChatOpenAI(**chat_kwargs)

    return create_agent(model=model, tools=[jsonplaceholder_api], system_prompt=SYSTEM_PROMPT)


def extract_text_from_agent_response(response: Any) -> str:
    if isinstance(response, dict):
        if "output" in response and isinstance(response["output"], str):
            return response["output"]
        messages = response.get("messages")
        if isinstance(messages, list) and messages:
            last = messages[-1]
            content = getattr(last, "content", None)
            if content is None and isinstance(last, dict):
                content = last.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                chunks = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        chunks.append(item.get("text", ""))
                    elif isinstance(item, str):
                        chunks.append(item)
                if chunks:
                    return "\n".join(chunks)
        return json.dumps(response, ensure_ascii=False, default=str)
    return str(response)


def invoke_agent(agent: Any, user_query: str) -> Dict[str, Any]:
    raw_response = agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]}
    )
    text = extract_text_from_agent_response(raw_response)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "status" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    return {
        "status": "success",
        "message": "Ответ агента получен, но не в JSON-формате. Возвращен текст.",
        "performed_operations": [],
        "result": {"raw_text": text},
    }
