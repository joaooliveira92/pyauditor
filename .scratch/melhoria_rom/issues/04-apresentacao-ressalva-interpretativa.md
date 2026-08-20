Type: grilling
Status: resolved

## Question

Como apresentar as 3 leituras da pontuação (achado 8 da auditoria) sem o
script "decidir" qual é a correta, dado que `engine/strategies/_target.py`
já documenta uma decisão de engenharia anterior (linear contínua, sem
teto/piso) tomada com base na leitura do Anexo D — e `configs/MinC/inms-1.1.yaml`
tem um comentário registrando esse histórico (referência a um "ticket 04"
anterior que corrigiu uma leitura "ceil" assumida antes)?

Pontos a fechar:

- A leitura linear (a que o pipeline efetivamente usa em
  `calculation.penalty_points`) deve aparecer marcada como "metodologia
  adotada" e as outras duas (degraus completos / teto) como "leituras
  alternativas, não adotadas — para referência", ou as 3 devem aparecer sem
  nenhuma marcada como adotada?
- O cálculo das 3 leituras é puramente aritmético sobre `shortfall`,
  `step_size_pct`, `step_points`, `base_points` já existentes em
  `config.penalty` — decidir se essa função helper vive em
  `engine/strategies/_target.py` (perto de `_linear_penalty`, reaproveitando
  a mesma matemática) ou só em `rom/render.py` (mantendo o motor de cálculo
  livre de números que ele não usa para decidir conformidade).
- Texto fixo de enquadramento da ressalva (a frase que explica que a
  ambiguidade contratual não foi validada formalmente) — uma linha, sem
  redigir prosa jurídica nova a cada indicador.

## Answer

**Onde vive o cálculo**: em `rom/render.py` (camada de apresentação), reusando
`shortfall` de `engine/strategies/_target.py`. `engine/strategies/ratio.py`
não ganha nada novo — o motor de cálculo continua só sabendo da leitura
linear (a única que decide `CalculationResult.penalty_points`).

**Formato** (dentro de `## Ressalva interpretativa`, sem subheader):

```markdown
| Leitura | Fórmula | Pontuação apurada |
|---|---|---|
| Linear contínua (adotada) | base + (déficit / passo) × pontos_degrau | 222.14 |
| Degraus completos | base + ⌊déficit / passo⌋ × pontos_degrau | 205.00 |
| Qualquer fração inicia novo degrau | base + ⌈déficit / passo⌉ × pontos_degrau | 225.00 |

> A leitura linear contínua é a metodologia adotada por este pipeline. As
> demais leituras são apresentadas para transparência e não foram validadas
> formalmente pela gestão contratual/assessoria jurídica.
```

**Separador decimal**: ponto (`222.14`), não vírgula — consistente com o
resto do template atual (`97.71%`); trocar o separador decimal do projeto
inteiro para pt-BR é uma mudança maior, fora do escopo deste ticket.

