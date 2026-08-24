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

_(prototipo construido — decisión pendiente de HITL)_

Protótipo: `src/ui/prototype-inms.html` (throwaway, no se debe enviar).

Cómo correrlo: `python3 -m http.server` dentro de `src/ui/` (o `uv run pyauditor
--workspace` — el server existente sirve estáticos), y abrir
`prototype-inms.html?variant=A`. Conmutador flotante inferior o teclas `←`/`→`.

Cuatro variantes estructuralmente distintas del formulario del indicador INMS,
sobre el mismo chrome (topbar + sidebar en árbol + pipeline stub). Datos
incrustados en memoria; `Save` es un stub toast. Dos indicadores de muestra:
INMS-01 (segmentado por **Categoría**: ATENDIMENTO_N1/N2, OPERACAO_N3) e
INMS-14 (segmentado por **Ativo**).

- **A — Panel único, contrato + segmentos.** Una pantalla, dos secciones:
  ficha compartida (nombre, contractual_id, shape, target, penalización,
  quality gates) arriba; por segmento (CSV, columna id, columna de período)
  abajo. Respuesta: *una pantalla con dos secciones*.
- **B — Dos pantallas (contrato → segmentos).** rail de pasos; paso 1 =
  contrato, paso 2 = segmentos. La meta/penalización **no** se repite en el
  paso 2 (se heredan del contrato). Respuesta: *dos pantallas*.
- **C — Panel largo con aviso de segmentación.** banner destacado que avisa
  que cambiar objetivo/penalización aplica a los N segmentos (viven en el
  archivo compartido) y que la fuente es por segmento. Respuesta: *un panel
  con aviso*.
- **D — Árbol + contrato de solo lectura.** la ficha compartida se muestra
  read-only (se edita en el nodo del indicador); cada hoja del árbol edita
  solo su fuente. Respuesta: *jerarquía de navegación distinta*.

La validación inline se representa como restricción visible en el campo
objetivo ("debe estar entre 0 y 100", variantes A/B/C) para reaccionar al
tratamiento.

Una vez el humano elija una variante (o mezcla de trozos), se pliega a la UI
real (`src/ui/index.html` + `server.py`) y el prototipo se descarta.

## Verdict (HITL)

**Variante B — Dos pantallas (contrato → segmentos).** Elegida por el
desarrollador.

Razones estructurales de por qué B gana sobre el resto:

- **Espelha o modelo de dois arquivos.** O passo 1 (contrato) corresponde a
  `_shared/inms-NN.yaml`; o passo 2 (segmentos) às parametrizações por
  órgão/categoria/ativo. Uma tela por arquivo elimina a pergunta "este campo
  vai pra qual arquivo?" que as variantes A/C deixam em aberto.
- **Meta/penalização não se repetem** no passo 2 (herdam do contrato) — a
  variante A repete a meta no contexto de cada segmento, sugerindo que dá pra
  variar a meta por categoria, o que o domínio não permite (a meta é do Anexo D
  do indicador).
- **Redireciona o foco:** passo 1 = "o que é este indicador", passo 2 = "de
  onde vêm os dados de cada segmento". O usuário segmenta a tarefa de edição.

Para indicador não segmentado (sem Categoria/Ativo), B colapsa num passo único
sem a railroad. A validação inline (restrição 0–100 no target) permanece do
protótipo.

Implementação do formulário real (server.py + index.html + app.js) é ticket
de follow-up — ver map.md.

## Comments

- HITL: "i like B" → variante B venceu.
