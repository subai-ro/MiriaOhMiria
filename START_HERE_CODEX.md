# Перенос World Zero в локальный Codex

Этот архив уже содержит полный проект V0.0-D.2.3: исходники, 139 тестов,
acceptance-сценарии, спецификации, исходные канонические документы и постоянные
инструкции AGENTS.md. Старый архив D.1.3.3 поверх него распаковывать не нужно.

## 1. Безопасная распаковка

Распакуй архив рядом с текущей папкой, а не поверх неё. Например:

    Expand-Archive .\world_zero_v0_0d2_3_codex_ready.zip -DestinationPath C:\Creation

Открой получившуюся папку world_zero_v0_0d2_3_codex_ready. Существующую
C:\Creation\world_zero пока оставь как резервную копию.

## 2. Проверка baseline

В PowerShell из корня новой папки:

    powershell -ExecutionPolicy Bypass -File .\verify_d23.ps1

Скрипт использует py, а при его отсутствии python. Никаких пакетов, API-ключей
или запущенного Ollama для D.2.3 не требуется. Логи попадут в
local_acceptance/, не затрагивая эталонные файлы acceptance/.

Ожидаемый итог:

- 139 tests, OK
- 10/10 LAW
- 19/19 LAW
- 26/26 LAW
- 26/26 LAW

Если любой шаг красный, не замораживай checkpoint и не ослабляй LAW. Сохрани
полный вывод и попроси Codex диагностировать расхождение.

## 3. Создание локальной истории Git

Только после зелёной проверки:

    git init
    git add .
    git commit -m "World Zero D.2.3 verified baseline"
    git tag v0.0-d2.3-local-baseline

Git не обязателен для работы Codex, но даёт понятные diff и безопасные точки
возврата. Не публикуй репозиторий, пока сам этого не решишь.

Если хочешь вернуть привычный путь C:\Creation\world_zero, после проверки
переименуй старую папку в резервную и новую в world_zero. Не удаляй резервную
копию до первого успешного рабочего checkpoint.

## 4. Открытие в Codex

Открой именно корень проекта — папку, где лежит AGENTS.md:

    code C:\Creation\world_zero_v0_0d2_3_codex_ready

Дальше открой панель Codex в VS Code либо запусти Codex CLI из этой папки.
Codex автоматически читает корневой AGENTS.md и использует Git root как границу
проекта.

Для начала оставь стандартные разрешения: запись только внутри workspace и
подтверждение действий за его пределами. Полный доступ системе проекту не
нужен.

Актуальные официальные справки:

- AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex CLI: https://learn.chatgpt.com/docs/codex/cli
- практики работы: https://learn.chatgpt.com/guides/best-practices

## 5. Первый разговор с Codex

Скопируй первый запрос из CODEX_FIRST_PROMPTS.md. Он просит провести
read-only-аудит и пересказать границы проекта до любых изменений.

После этого передай Codex вывод verify_d23.ps1. Если все пять гейтов зелёные,
попроси только обновить статус локальной приёмки. Следующая содержательная
граница — проектирование P5, canonical model-backed Nereid cognition.

## Что не нужно переносить отдельно

- старый D.1.3.3 ZIP;
- кэш Python и временные логи;
- историю этого чата;
- API-ключи;
- Ollama-модель для D.2.3.

Важные решения из разговора уже сведены в AGENTS.md,
WORLD_ZERO_CURRENT_STATE.md и актуальный migration handoff.
