# ArchBench: сводка прогонов

M1 — доля функционально решённых; M2 — решено и без нарушений архитектуры;
M3 — доля нарушений среди функционально решённых; U — среди решённых проверка не смогла решить.
В скобках — разброс между повторами (min–max).

| Агент | Модель | Условие | Effort | Прогонов | M1 | M2 | M3 | U | Читал ADR | Сбои агента | $ |
| --- | --- | --- | --- | --: | --: | --: | --: | --: | --: | --: | --: |
| claude-code | claude-haiku-5-5 | adr_in_prompt | high | 15 | 100% (100%–100%) | 100% (100%–100%) | 0% (0%–0%) | 0% (0%–0%) | 73% | 0 | 0.23 |
| claude-code | claude-haiku-5-5 | adr_in_repo | high | 15 | 100% (100%–100%) | 100% (100%–100%) | 0% (0%–0%) | 0% (0%–0%) | 100% | 0 | 0.21 |
| claude-code | claude-haiku-5-5 | no_adr | high | 15 | 100% (100%–100%) | 53% (40%–60%) | 47% (40%–60%) | 0% (0%–0%) | 0% | 0 | 0.20 |

## По задачам

| Задача | Агент | Модель | Условие | Effort | Исходы | Нарушенные правила |
| --- | --- | --- | --- | --- | --- | --- |
| t1_acl_delivery | claude-code | claude-haiku-5-5 | adr_in_prompt | high | solved_clean, solved_clean, solved_clean | — |
| t1_acl_delivery | claude-code | claude-haiku-5-5 | adr_in_repo | high | solved_clean, solved_clean, solved_clean | — |
| t1_acl_delivery | claude-code | claude-haiku-5-5 | no_adr | high | solved_violation, solved_violation, solved_violation | acl |
| t2_passive_repo_cap | claude-code | claude-haiku-5-5 | adr_in_prompt | high | solved_clean, solved_clean, solved_clean | — |
| t2_passive_repo_cap | claude-code | claude-haiku-5-5 | adr_in_repo | high | solved_clean, solved_clean, solved_clean | — |
| t2_passive_repo_cap | claude-code | claude-haiku-5-5 | no_adr | high | solved_clean, solved_clean, solved_clean | — |
| t3_acyclic_reminders | claude-code | claude-haiku-5-5 | adr_in_prompt | high | solved_clean, solved_clean, solved_clean | — |
| t3_acyclic_reminders | claude-code | claude-haiku-5-5 | adr_in_repo | high | solved_clean, solved_clean, solved_clean | — |
| t3_acyclic_reminders | claude-code | claude-haiku-5-5 | no_adr | high | solved_clean, solved_clean, solved_violation | acyclic |
| t4_module_contracts_hold | claude-code | claude-haiku-5-5 | adr_in_prompt | high | solved_clean, solved_clean, solved_clean | — |
| t4_module_contracts_hold | claude-code | claude-haiku-5-5 | adr_in_repo | high | solved_clean, solved_clean, solved_clean | — |
| t4_module_contracts_hold | claude-code | claude-haiku-5-5 | no_adr | high | solved_clean, solved_clean, solved_clean | — |
| t5_schema_drift_scan | claude-code | claude-haiku-5-5 | adr_in_prompt | high | solved_clean, solved_clean, solved_clean | — |
| t5_schema_drift_scan | claude-code | claude-haiku-5-5 | adr_in_repo | high | solved_clean, solved_clean, solved_clean | — |
| t5_schema_drift_scan | claude-code | claude-haiku-5-5 | no_adr | high | solved_violation, solved_violation, solved_violation | acl |
