import argparse
import json
import sys


# Настройки OpenRouter (заполните своими значениями)
OPENROUTER_MODEL = "arcee-ai/trinity-large-preview:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = "SET_YOUR_API_KEY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LangChain-агент для JSONPlaceholder (OpenRouter, CLI)"
    )
    parser.add_argument(
        "query",
        help='Запрос на естественном языке, например: "получи пост 5"',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from jsonplaceholder_agent import build_agent, invoke_agent

        agent = build_agent(
            model_name=OPENROUTER_MODEL,
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        result = invoke_agent(agent, args.query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") != "error" else 1

    except ModuleNotFoundError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Не установлены зависимости Python.",
                    "performed_operations": [],
                    "result": {
                        "error": str(exc),
                        "hint": "Выполните: pip install -r requirements.txt",
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Сбой при выполнении агента.",
                    "performed_operations": [],
                    "result": {
                        "error": str(exc),
                        "hint": (
                            "Проверьте настройки OpenRouter (base URL, API key, модель) "
                            "и доступность сети."
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
