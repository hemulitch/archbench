# Правило ACL: внешние системы только через адаптеры

**Утверждение.** Любая связь сервиса с внешней системой исходит от сервиса с
меткой `acl`. Источник решения: `repo/docs/adr/0001-anti-corruption-layer.md`.

**Проверка.** Правило `acl` из AACT на модели, снятой с `deploy/*.yaml`. Внешняя
система — любой хост в URL из `environment`, которого нет среди манифестов.

**Типичное нарушение.** `orders-api` получает адрес FastShip и зовёт его сам.

    python bench/archcheck.py <workspace> tasks/t1_acl_delivery/task.yaml
