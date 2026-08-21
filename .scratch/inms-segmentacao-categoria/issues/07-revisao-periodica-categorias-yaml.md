# 07 — Mecanismo de revisão periódica de `categorias.yaml`

Type: grilling
Status: resolved

Blocked by: 02, 03

## Question

O ticket 02 fixou o mapeamento declarativo `categorias.yaml`, mas não definiu o que acontece quando
novos dados reais chegam e os literais de `Grupo_executor` mudam (aconteceu na própria sessão do
ticket 02, com a chegada de dado real do MTur para o INMS 1.6). Falta decidir: o mecanismo é
reativo (via a categoria `outros`, que já captura o que não bate em nenhuma categoria) ou proativo
(um alerta explícito), quem é responsável por atualizar o arquivo, e com que cadência.

## Answer

Resolvido via grilling (2 perguntas, ambas aprovadas).

1. **Mecanismo: proativo, em cima do sinal já existente.** `outros` já captura e conta linhas não
   classificadas (ticket 01), mas isso sozinho é passivo — exige que alguém abra o xlsx sintético.
   `split` deve emitir um `WARNING` explícito no log sempre que `outros > 0` para um INMS/categoria,
   em vez de só um `INFO` de contagem. Texto exato:

   ```
   WARNING: INMS 1.1 (MinC/2026-06), categoria outros: 3 linha(s) não classificada(s) em nenhuma categoria — revisar categorias.yaml
   ```

2. **Responsabilidade e cadência: atrelada à execução mensal existente, sem processo separado.**
   Como `split` já roda toda competência (parte de `run`), o warning acima aparece naturalmente a
   cada rodada — não é necessário um processo de revisão periódica à parte. A responsabilidade é de
   quem opera o `pyauditor` mensalmente (mesma pessoa que já lida com os demais warnings/erros do
   CLI): ao ver o warning, decide se o `Grupo_executor` novo merece entrada em `categorias.yaml` ou
   se é ruído esperado (ex.: grupo transitório).
