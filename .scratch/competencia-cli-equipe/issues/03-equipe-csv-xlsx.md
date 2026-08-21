---
Type: grilling
Status: resolved
---

# equipe.csv alimenta os responsáveis do xlsx

## Question

Detalhar reader e consumo (Q6 do mapa): leitura de `input/equipe.csv` (FUNÇÃO/NOME/SIAPE, vírgula), mapeamento FUNÇÃO→campo da capa ("Gestor do Contrato"→"Gestor do contrato", "Fiscal Técnico"→"Fiscal técnico", "Fiscal Requisitante", "Fiscal Administrativo"), normalização de caixa/acento, duplicatas, valor da célula `"Nome (SIAPE)"`. Reader mora em `excel/equipe.py` análogo a `objetos.py`? Onde o `report` injeta os valores antes do `render_capa_sheet`? Bootstrap cria template de equipe.csv ou o arquivo é mantido à mão? O consolidado (`build_capa`) também passa a mostrar responsáveis?

## Answer

Aprovado pelo humano (2026-08-21):

1. **Reader**: módulo novo `excel/equipe.py`, padrão `objetos.py` — `EQUIPE_FILENAME = "equipe.csv"`, delimiter `,`, encoding `utf-8-sig`; dataclass `Equipe` com mapeamento função→(nome, siape) e `warnings`; `read_equipe` levanta `ValueError` se malformado (cabeçalho errado, linha sem nome, função duplicada); arquivo ausente é decisão do chamador.
2. **Mapeamento**: FUNÇÃO normalizada (caixa/acento ignorados) — "Gestor do Contrato"→"Gestor do contrato"; "Fiscal Técnico"/"Fiscal Requisitante"/"Fiscal Administrativo"→respectivos campos. Sufixo "- Substituto" nunca vai para planilha nem ROM.
3. **Célula**: `"Nome (SIAPE)"` (ex.: "João Antônio Carvalho Monteiro de Oliveira (1499628)"). Equipe ausente/malformada → warning + campos vazios (charting).
4. **Fonte única** (Q1): os 4 rótulos saem de `ORGAO_FIELD_LABELS`; bootstrap para de criá-los na capa CSV; capa embutida, consolidado e a seção Responsáveis do ROM leem exclusivamente do Equipe.
5. **Consolidado** (Q2): `build_capa` passa a exibir os 4 responsáveis.
6. **Bootstrap** (Q3): cria esqueleto `input/equipe.csv` com as 8 funções e valores vazios — idempotente como as capas; garante cabeçalho canônico.
7. **Publication gate**: os 4 responsáveis contam como satisfeitos quando presentes no Equipe lido.
