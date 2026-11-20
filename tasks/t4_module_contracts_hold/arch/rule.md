# Правило: модули монолита общаются только через контракты

**Утверждение.** Импорт из другого модуля `shop/<модуль>` разрешён только для его
`contracts.py`. Источник решения: `repo/docs/adr/0001-module-contracts.md`.

**Проверка.** Собственное правило `bcIsolation` в формате правил AACT
(`bench/rules/bcIsolation.ts`) на графе импортов из исходного кода. Динамические
импорты дают ошибку проверки, а не зелёный результат.

**Типичное нарушение.** `shop/orders/service.py` импортирует готовый
`ReservationBook` из `shop/inventory/internal`, потому что контракт его не отдаёт.

    python bench/archcheck.py <workspace> tasks/t4_module_contracts_hold/task.yaml
