# 11 — Dono único categoria→nível + dedup de avisos `in_values`/`outros`

**What to build:** o mapa categoria→nível (domínio contratual, Anexo) ganha dono único,
e os avisos de `in_values` sem correspondência e de `outros` são emitidos uma única vez
quando `run` executa split+measure na mesma passada.

Hoje o mapa vive em `sintetico.py` e `inms_1_1_audit.py` (4 mappings idênticos) com uma
cópia parcial em `excel/groups.py`. O aviso de `in_values` sem correspondência é copiado
verbatim em `measure` e `split` — quando `run` roda split+measure, o aviso aparece duas
vezes no mesmo output re-avaliando os mesmos `real_values`; o aviso `outros` idem.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] Mapa categoria→nível existe em um único dono (domínio contratual) e `sintetico`/`inms_1_1_audit`/`groups` o importam — cópias locais removidas.
- [ ] Aviso de `in_values` sem correspondência e aviso `outros` emitidos 1x por passada quando `run` executa split+measure (sem duplicação no mesmo output).
- [ ] Testes de sintético, inms_1_1_audit, split e measure verdes.