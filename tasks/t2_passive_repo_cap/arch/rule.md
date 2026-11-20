# Правило CRUD: пассивный репозиторий

**Утверждение.** Сервис с меткой `repo` связан только со своей БД, а к БД ходят
только репозитории. Источник решения: `repo/docs/adr/0001-passive-repository.md`.

**Проверка.** Правило `crud` из AACT на модели, снятой с `deploy/*.yaml`.

**Типичное нарушение.** Атомарный расчёт остатка лимита живёт в транзакции
репозитория, и `loyalty-repo` сам запрашивает уровень клиента у `customers-api`.

    python bench/archcheck.py <workspace> tasks/t2_passive_repo_cap/task.yaml
