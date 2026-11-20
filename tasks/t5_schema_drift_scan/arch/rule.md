# Правило: схема соответствует развёрнутой системе

**Утверждение.** Набор элементов и связей `architecture/architecture.puml` совпадает
с тем, что объявлено в `deploy/*.yaml`. Источник решения:
`repo/docs/adr/0001-architecture-model-is-kept-current.md`.

**Проверка.** `computeDiff` из AACT между моделью схемы и моделью из `deploy/*.yaml`,
считаются только структурные расхождения. Источники независимы: схему пишет
человек, конфигурацию читает кластер.

**Типичное нарушение.** Новый адаптер и связи добавлены в `deploy/`, схема не тронута.

    python bench/archcheck.py <workspace> tasks/t5_schema_drift_scan/task.yaml
