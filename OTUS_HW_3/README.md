Использовался провайдер OpenRouter и LLM arcee-ai/trinity-large-preview:free
Чтобы им воспользоваться, надо авторизоваться на https://openrouter.ai/ и забрать там API ключ. После этого надо проставить в переменную OPENROUTER_API_KEY значение этого ключа.

Используемое API - https://jsonplaceholder.typicode.com/
API для него
Routes

GET	/posts
GET	/posts/1
GET	/posts/1/comments
GET	/comments?postId=1
POST	/posts
PUT	/posts/1
PATCH	/posts/1
DELETE	/posts/1

Тестовые запросы и результаты приведены в файле RESULTS.md.

# Объявление tool
В файле jsonplaceholder_agent.py:L58-L188

# Логирование результата
Производится в консоль в файле main.py:L35

# Пример одного запроса, который приводит к вызову конкретного API метода
Запрос: "получи пост 5"
Вызов API метода: https://jsonplaceholder.typicode.com/posts/5

# Требования к формату ответа агента
Описаны в файле jsonplaceholder_agent.py:L192-L226

# Использованные промпты:

Системный промпт:

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