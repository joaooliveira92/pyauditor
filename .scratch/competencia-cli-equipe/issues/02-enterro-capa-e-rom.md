---
Type: grilling
Status: resolved
---

# Enterro dos campos de período na capa e ROM derivado

## Question

Detalhar a remoção decidida no mapa (Q4/Q5): tirar Competência/Períodos de `ORGAO_FIELD_LABELS` (afeta template do bootstrap e `render_capa_sheet`), deletar `validate_periodo_competencia`, a chamada em `cli/report.py:188` e os testes em `test_capa.py`/`test_cli_report.py`. O ROM (`rom/render.py:129-136`) passa a receber competência/período derivados da CLI — por qual caminho (`MeasurementResult`? parâmetro de `render_rom`)? Qual o texto novo da nota de proveniência? `build_capa` (consolidado) já injeta Competência computada — injeta também o período?

Casos esperados, fixados pelo humano (a derivação em si já é decisão do mapa/ticket 01):

```text
run 2026-06 --orgao both → Competência '2026-06', início 01/06/2026, fim 30/06/2026
run 2025-12 --orgao both → Competência '2025-12', início 01/12/2025, fim 31/12/2025
```

A capa nunca mais carrega nem valida esses três campos; todo consumidor (ROM, capa embutida, consolidado) exibe o que a CLI mandou.

## Answer

Aprovado pelo humano (2026-08-21):

1. **ROM**: parâmetros explícitos `competencia` e `periodo` em `render_rom`/`render_combined_rom` (e em `_render_identificacao`); `capa_fields` passa a alimentar só Responsáveis. Competência exibida vem da CLI; "Período da aferição: 01/06/2026 a 30/06/2026" (formato BR) também.
2. **Planilhas**: CAPA_E_CONTROLE embutida e consolidado mostram "Período inicial da aferição" e "Período final da aferição" como duas linhas, rótulos canônicos preservados, valores sempre derivados da CLI. Os três campos saem de `ORGAO_FIELD_LABELS`: bootstrap para de criá-los na capa CSV; as duas linhas de período voltam como linhas de exibição preenchidas pelo pipeline (lista própria de rótulos derivados, não hand-fill).
3. **Nota de proveniência** (texto aprovado): "*Competência e Período da aferição são derivados do argumento --competência da CLI. Responsáveis refletem o estado da capa no momento em que este ROM foi gerado.*"
4. **Consequências diretas**: `_PUBLICATION_FIELDS` perde os dois períodos (período é sempre conhecido — nunca mais pendência impeditiva); `_CAPA_ROM_FIELDS` perde os três; `validate_periodo_competencia`, `_parse_data_br` privada e chamada em `cli/report.py:188` deletadas; capas antigas com os campos: ignoradas; testes de validação/divergência deletados, teste de placeholder vira teste do valor derivado.
