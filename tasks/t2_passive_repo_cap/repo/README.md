# Loyalty

Программа лояльности: начисление баллов за покупки. Каждый сервис — отдельный
процесс; адреса зависимостей задаются только в `deploy/*.yaml`.

    pip install -r requirements.txt
    pytest

- `services/` — код сервисов, у каждого есть `GET /health`
- `deploy/` — манифесты развёртывания
- `architecture/architecture.puml` — схема C4
- `docs/adr/` — принятые архитектурные решения
