# 11 — Dono único categoria→nível + dedup de avisos `in_values`/`outros`

**What to build:** o mapa categoria→nível (domínio contratual, Anexo) ganha dono único,
e os avisos de `in_values` sem correspondência e de `outros` são emitidos uma única vez
quando `run` executa split+measure na mesma passada.

Hoje o mapa vive em `sintetico.py` e `inms_1_1_audit.py` (4 mappings idênticos) com uma
cópia parcial em `excel/groups.py`. O aviso de `in_values` sem correspondência é copiado
verbatim em `measure` e `split` — quando `run` roda split+measure, o aviso aparece duas
vezes no mesmo output re-avaliando os mesmos `real_values`; o aviso `outros` idem.

**Blocked by:** 06

**Status:** done

- [x] Mapa categoria→nível existe em um único dono (domínio contratual) e `sintetico`/`inms_1_1_audit`/`groups` o importam — cópias locais removidas.
- [x] Aviso de `in_values` sem correspondência e aviso `outros` emitidos 1x por passada quando `run` executa split+measure (sem duplicação no mesmo output).
- [x] Testes de sintético, inms_1_1_audit, split e measure verdes.

## Comments

- 2026-08-22 — Implementado. (a) Novo módulo `pyauditor/config/niveis.py`
  (`NIVEL_BY_CATEGORIA`/`NIVEL_ORDER`) como dono único do mapa
  categoria→nível; `excel/groups.py` re-exporta e `excel/sintetico.py`/
  `excel/inms_1_1_audit.py` importam (aliases `_NIVEL_BY_CATEGORIA`/
  `_NIVEL_ORDER` preservados localmente), cópias literais removidas. (b)
  `cli/measure.py`: no caminho em-memória, os avisos de `in_values` sem
  correspondência e de `outros` são suprimidos quando `already_split=True`
  (dispatch de `run`, que roda split antes de measure na mesma passada) —
  `split` já os havia emitido sobre os mesmos `real_values`. Teste novo
  `test_run_measure_already_split_dedups_in_values_e_outros_warning` em
  `test_cli_measure.py`. Suíte alvo (92) verde.