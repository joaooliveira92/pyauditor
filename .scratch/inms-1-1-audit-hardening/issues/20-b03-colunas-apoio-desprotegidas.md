# 20 — B-03: Colunas de apoio não estão ocultas nem protegidas

**Severidade:** Baixa

**Status:** resolved

## Problema

O texto da planilha instrui a não excluir nem reordenar as colunas de apoio
(R:AM), mas nada impede a alteração — depende só de boa vontade de quem edita.

## Correção recomendada

- Ocultar as colunas R:AM
- Proteger a planilha
- Desbloquear apenas campos de justificativa e evidência
- Opcionalmente, mover os dados de apoio para uma aba dedicada

## Critério de aceite

- [x] Colunas R:AM ocultas por padrão
- [x] Proteção de planilha aplicada, com campos de justificativa/evidência desbloqueados
- [x] Teste (ou verificação manual documentada) confirmando que a proteção não quebra a leitura das fórmulas pelo pipeline

## Answer

`_protect_support_columns(sheet)`, chamada no final de `write_sheet()` (antes
de `freeze_panes`), oculta as colunas R:AM (`sheet.column_dimensions[...].hidden
= True`) e ativa `sheet.protection.sheet = True`, sem senha — o objetivo é
reduzir edição acidental das fórmulas, não impedir edição deliberada por quem
tem o arquivo. Os campos de preenchimento manual (Seção 4: "Justificativa de
exclusão", "Documento autorizador"; Seção 6: "Justificativa", "Aceite da
justificativa", "Documento/evidência") recebem `Protection(locked=False)`
(constante `_UNLOCKED`) e continuam editáveis mesmo com a aba protegida.

Não movemos os dados de apoio para uma aba dedicada (alternativa opcional
citada na correção recomendada) — ocultar+proteger na mesma aba é
suficientemente simples e preserva as referências de fórmula existentes
(`$R$2:$R$N` etc.) sem precisar reescrever nenhuma fórmula para apontar para
outra aba.

Verificação de que a proteção não quebra a leitura das fórmulas pelo
pipeline: **documentada, não testada por um motor de recálculo real** (mesma
limitação do ticket 08 — sem LibreOffice/Excel disponíveis neste ambiente).
A proteção de planilha do formato OOXML (`sheet.protection.sheet`) é, por
especificação, um controle de UI que bloqueia edição interativa — nunca afeta
o cálculo de fórmulas por nenhum motor (Excel, LibreOffice, openpyxl com
`data_only=True` após recálculo externo), então não há mecanismo pelo qual
essa mudança poderia quebrar a leitura de valores pelo pipeline. Ocultar
colunas (`hidden = True`) também é puramente de exibição — openpyxl continua
lendo e escrevendo essas colunas normalmente, como os testes deste PR
confirmam (todos os testes que leem colunas R:AM continuam passando).

Teste: `test_support_columns_are_hidden_and_sheet_is_protected` em
`tests/test_inms_1_1_audit.py`, verificando colunas R e AM ocultas, proteção
ativa, uma célula de fórmula comum (`A13`) bloqueada, e a célula de
justificativa da Seção 4 desbloqueada.

## Addendum (revisão 81c9a6e)

**Consenso C-02 × B-03**: o ocultamento passou a excluir a coluna `AJ`
("Situação dos dados"). Ocultá-la anularia o indicador visual exigido pelo
ticket 02 (C-02); ela é preenchida em Python, não alimenta fórmula alguma, e
carrega o preenchimento vermelho das linhas com data inválida. O teste acima
passou a afirmar que `AJ` não fica oculta.
