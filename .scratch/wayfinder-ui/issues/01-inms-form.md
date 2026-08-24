# 01 — Formulário do indicador INMS

- **Type:** prototype
- **Status:** resolved
- **Blocked by:** —

## Question

Hoje o indicador INMS é editado como YAML cru: `_shared/inms-NN.yaml`
(contrato do indicador) + `{orgao}/inms-NN.CATEGORIA.yaml` (parametrização por
órgão/categoria). O usuário não deve sentir que está editando YAML.

Decidir: o layout e os campos do formulário que substitui essa edição —
quais campos aparecem, como o par `_shared` + `{orgao}` se apresenta (uma tela
com duas seções? duas telas?), como avisar sobre `Categoria`/`Ativo` quando o
indicador é segmentado, validação inline, e o que muda na navegação da
sidebar (hoje é uma lista plana de caminhos de arquivo — isso ainda faz
sentido quando os arquivos viram formulários?).

Construir um protótipo (chamar Skill `prototype`) pra reagir a uma proposta
concreta em vez de discutir em abstrato.

## Answer

_(protótipo construido — decisão de layout: variante B, duas telas contrato →
segmentos — escolhida em HITL; proto capturado na branch `prototype/inms-form`.
Follow-up: formulário real implementado em `src/ui` — backend em `src/ui/inms.py`
+ endpoints `/api/indicators` e `/api/indicator`, frontend em `index.html`/`app.js`
(árbol da sidebar agrupada por indicador INMS; o painel central renderiza contrato
compartido + segmentos por órgão como formulário; salvar escreve de volta os YAMLs).)_


