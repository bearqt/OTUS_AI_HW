# ИНТЕГРАЦИЯ С IDE 
Выполняется добавлением конфига сервера в настройки подключенных MCP.
Пример для Codex в файле config.toml:
[mcp_servers.kb-search]
url = "http://127.0.0.1:8006/mcp"


Сервер поднимается:
mcp_http_server.py:L26-L33 и его запуск в mcp_http_server.py:L246

Реализованы инструменты:
1) search_knowledge - семантический поиск по базе знаний - mcp_http_server.py:L119-L141
Пример вывода:
```json
{
  "status": "success",
  "query": "что такое стандарт PKCS 11 PKCS#11",
  "top_k": 5,
  "min_score": 0.08,
  "deduplicate_docs": true,
  "model_kind": "lsa_tfidf_svd_256",
  "results_count": 5,
  "results": [
    {
      "chunk_id": "pageId_2228227.md::chunk-1",
      "doc_id": "pageId_2228227.md",
      "title": "Рекомендации по выбору высокоуровневого интерфейса",
      "chunk_index": 1,
      "score": 0.810348,
      "snippet": "Стандарт PKCS #11, также известный под названием Cryptoki (Cryptographic Token Interface Standart), распространяется на «криптографические токены» – устройства, способные содержать криптографическую информацию и выполнять криптографические преобразования, и определяет для них инт...",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\pageId_2228227.md"
    }
  ]
}
```
2) get_document - получение документа из базы знаний по id - mcp_http_server.py:L144-L160
Пример вывода:
```json
{
  "status": "success",
  "found": true,
  "document": {
    "doc_id": "Indeed+AM.md",
    "title": "Indeed AM",
    "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Indeed+AM.md",
    "size_bytes": 7679,
    "content_length": 4766,
    "content": "[Indeed AM](https://dev.rutoken.ru/display/PUB/Indeed+AM)\n\n-\n\nCreated by [Технический писатель](https://dev.rutoken.ru/display/~dmitrieva), last modified by [Осьминина Анастасия](https://dev.rutoken.ru/display/~osminina) on [Jul 30, 2024](https://dev.rutoken.ru/pages/diffpagesbyversion.action?pageId=98936020&selectedPageVersions=5&selectedPageVersions=6 \"Show changes\")\n\nЭта настройка доступна, если выбрана опция **Интеграция с Indeed Access Manager** в разделе **Общие функции** Мастера настройки Рутокен KeyBox.\n\nРутокен KeyBox может быть интегрирован с Indeed Access Manager и Indeed AM Enterprise Single Sign-On. Интеграция позволит объединить операции выпуска устройства, запроса сертификата, записи сертификата и регистрации аутентификатора в единый процесс.\n\nВыпущенное подобным образом устройство может быть использовано пользователем как для аутентификации в домене и SSO-приложениях, так и для цифровой подписи или доступа к ресурсам, требующих наличие персональных сертификатов. Интеграция между системами возможна на любом этапе, независимо от того, какой из продуктов был развернут раньше.\n\nНастройка интеграции Рутокен KeyBox и Indeed AM состоит из двух этапов...",
    "content_truncated": false
  }
}
```
3) list_documents - получение списка всех документов из базы знаний - mcp_http_server.py:L163-L175
Пример вывода:
```json
{
  "status": "success",
  "total": 678,
  "offset": 0,
  "limit": 5,
  "items": [
    {
      "doc_id": "Apache+HTTP+Server.md",
      "title": "Apache HTTP Server",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Apache+HTTP+Server.md",
      "size_bytes": 15593,
      "content_length": 12752
    },
    {
      "doc_id": "Bitrix.md",
      "title": "Bitrix",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Bitrix.md",
      "size_bytes": 2586,
      "content_length": 1980
    },
    {
      "doc_id": "Bouncy+Castle.md",
      "title": "Bouncy Castle",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Bouncy+Castle.md",
      "size_bytes": 15295,
      "content_length": 13593
    },
    {
      "doc_id": "Event+Log+Proxy.md",
      "title": "Event Log Proxy",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Event+Log+Proxy.md",
      "size_bytes": 4560,
      "content_length": 3231
    },
    {
      "doc_id": "Indeed+AM.md",
      "title": "Indeed AM",
      "path": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result\\Indeed+AM.md",
      "size_bytes": 7679,
      "content_length": 4766
    }
  ]
}
```
4) rebuild_index - пересобрать индекс после изменений в базе знаний - mcp_http_server.py:L179-L186
Пример вывода:
```json
{
  "status": "success",
  "message": "index_rebuilt",
  "index_stats": {
    "kb_dir": "C:\\repos\\OTUS_AI_HW\\OTUS_HW_1\\OTUS_HW_4\\scrape_result",
    "documents_count": 10,
    "chunks_count": 328,
    "total_chars": 350104,
    "chunk_size": 1400,
    "chunk_overlap": 250,
    "max_features": 25000,
    "svd_components_requested": 256,
    "model_kind": "lsa_tfidf_svd_256",
    "built_at": "2026-02-23T14:27:45Z",
    "build_duration_ms": 1086
  }
}
```

Пример вызова предоставлен скриншотом в папке screenshots

# Tool outputs contract

mcp_http_server.py:L139-L141
mcp_http_server.py:L159-L160
mcp_http_server.py:L175
mcp_http_server.py:L26-L33
mcp_http_server.py:L186