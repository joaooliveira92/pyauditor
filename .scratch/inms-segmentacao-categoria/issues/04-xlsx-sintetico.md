# 04 — Design do xlsx sintético por INMS

Type: prototype
Status: resolved

Blocked by: 01

## Question

O ticket 01 decidiu que, além dos ROMs Markdown (um por categoria), o pipeline deve gerar um xlsx "sintético" por INMS — uma linha por valor único de `Grupo_executor` daquele INMS, com a categoria como coluna — distinto do Excel final consolidado já especificado. Falta decidir, com um protótipo concreto pra reagir: colunas exatas (contagem de incidentes? dentro-do-prazo/fora-do-prazo? soma de pontuação apurada?), nome/localização do arquivo, e se ele é gerado pelo `measure` ou por um passo separado.

Também precisa cobrir a mecânica decidida no ticket 01 (itens 14–16): quando o CSV de entrada de um INMS não existe pra competência (ausência = "não ativado", não erro — vale pra qualquer indicador, não só 1.3/1.8/1.10), o xlsx ainda deve listar esse INMS, com uma frase placeholder tipo `"Esse serviço não foi requisitado no período selecionado"` no lugar das linhas de dados. Decidir o texto exato, onde aparece no layout, e como isso aparece também no log/saída do CLI durante a execução do `pyauditor` (não pode passar batido silenciosamente).

Nota adicional do ticket 02: vários INMS (1.6/MinC, 1.9, 1.11, 1.12, 1.13) rodam em modo `whole_indicator` — sem `Grupo_executor` nenhum, então "uma linha por valor único de `Grupo_executor`" não se aplica a eles. O layout precisa decidir como esses INMS aparecem no xlsx sintético (provavelmente uma linha única, rotulada com a categoria inteira, no lugar das N linhas por grupo). Ver ticket 02 para a lista completa e o schema `categorias.yaml`.

## Answer

Resolvido via protótipo (`prototype/inms-xlsx-sintetico-04`, commit `582d23e`) — o usuário reagiu ao xlsx gerado e aprovou com dois ajustes.

1. **Um único xlsx por órgão/competência** (`sintetico.xlsx`; localização exata — provavelmente `roms/<orgao>/<ano>/<mes>/` — fica pro ticket de implementação), **uma aba por INMS** que tem entrada em `categorias.yaml` (exclui 1.8/1.10, sem categoria).
2. **Colunas da aba** (INMS em modo `grupo_executor`, uma linha por (categoria, valor de `Grupo_executor`)): `Categoria` | `Nível` | `Grupo executor` | `Linhas` | `Dentro do prazo` | `Fora do prazo` | `% bruto` | `Tempo médio criação→resolução`. Contagens são **brutas, pré-quality-gate** — conferência rápida, não substitui o resultado oficial do ROM da categoria.
3. **Coluna `Nível`**: derivada da categoria da linha — `ATENDIMENTO_N1`→N1, `ATENDIMENTO_N2`→N2, `OPERACAO_N3`→N3, **`MONITORAMENTO_NOC_SOC`→N3** (confirmado pelo usuário — NOC/SOC conta como N3, não fica sem Nível); `outros` não tem Nível (célula vazia).
4. **`Tempo médio criação→resolução`**: média de `DataHoraFim − DataHoraSolicitacao` das linhas aprovadas pelo quality gate daquela linha da tabela. Colunas confirmadas existentes no CSV bruto do fornecedor: `DataHoraSolicitacao`, `DataHoraLimite`, `DataHoraFim` (`DataHoraLimite` já alimenta o cálculo existente de "dentro do prazo"; não é fog).
5. **Subtotais por Nível** (bloco abaixo da tabela, só nas abas em modo `grupo_executor`): soma de `Linhas`/`Dentro do prazo`/`Fora do prazo`, `% bruto` agregado e `Tempo médio criação→resolução` agregado, um subtotal por N1/N2/N3 presente na aba.
6. **`whole_indicator`**: linha única, `Grupo executor` = `"(indicador inteiro)"`, mesmas colunas preenchidas a partir do dataset inteiro — **sem** bloco de subtotais por Nível (não há granularidade pra subtotalizar numa aba de uma linha só).
7. **"Não ativado"** (dataset ausente na competência): linha única mesclada com a frase `"Esse serviço não foi requisitado no período selecionado."` no lugar da tabela — mesmo texto no log do CLI durante `split`/`measure` (texto exato do log, se distinto do xlsx, seguiu não decidido — não bloqueia o ticket 06).
8. **Quem gera**: proposto que seja o `split` (já lê `categorias.yaml` por completo, incluindo os INMS em `whole_indicator` que ele mesmo pula) — não formalmente re-perguntado ao usuário nesta sessão, mas não contestado; considerar confirmado por omissão, revisar no ticket de implementação se necessário.

Protótipo primário: branch `prototype/inms-xlsx-sintetico-04` (script `gerar_sintetico.py` + xlsx de exemplo gerado), fora de `master`.
