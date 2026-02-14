# Мини-анкета

Небольшое веб-приложение с backend на Go и frontend на HTML/CSS/JavaScript.

## Требования

- Go 1.22 или выше

## Как запустить

1. Перейти в папку проекта:
```powershell
cd c:\repos\OTUS_HW_1
```

2. Запустить сервер:
```powershell
go run .
```

3. Открыть в браузере:
```text
http://localhost:8080
```

## API

- `GET /questions` — возвращает список вопросов анкеты.
- `POST /answers` — принимает ответы пользователя в JSON и сохраняет их в памяти backend.
