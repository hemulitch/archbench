# Правило: граф зависимостей сервисов ацикличен

**Утверждение.** В графе связей между контейнерами нет циклов. Источник решения:
`repo/docs/adr/0001-acyclic-service-dependencies.md`.

**Проверка.** Правило `acyclic` из AACT на модели, снятой с `deploy/*.yaml`.

**Типичное нарушение.** `notifications-api` при отправке сам запрашивает
бронирование у `bookings-api`, хотя тот уже вызывает `notifications-api`. Каждая
связь по отдельности выглядит безобидно, нарушает только их сочетание.

    python bench/archcheck.py <workspace> tasks/t3_acyclic_reminders/task.yaml
