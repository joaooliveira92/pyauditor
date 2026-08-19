# Pesquisa: conversão de pontuação de penalidade INMS em glosa monetária (item 35 do TR)

Ticket: `.scratch/inms-pipeline-spec/issues/12-research-glosa-item-35.md`

## Localização do "item 35"

Duas referências cruzadas apontam para o mesmo item:

- `docs/termo_de_referencia/06_modelo_de_execucao.html:1093` — "...aferidos conforme **ITEM 35** deste TR."
- `docs/termo_de_referencia/anexo_d_prazos.html:191` — "...e as especificações do item 35 do Termo de Referência."

O conteúdo correspondente está em `docs/termo_de_referencia/07_modelo_de_gestao.html`, na seção **"Sanções Administrativas e Procedimentos para retenção ou glosa no pagamento"** (a partir da linha 196) e reforçado na subseção de pagamento/aceite (linhas ~893–1060). Os arquivos HTML não numeram os itens no markup (sem atributo/numeração visível por `<p class="Item_Nivel1">`), mas o conteúdo — única seção do TR que define a fórmula de conversão pontuação→glosa — bate exatamente com o que ambas as referências descrevem.

## 1. Fórmula de conversão pontuação → glosa

Texto literal (`07_modelo_de_gestao.html:218-221`):

> "As glosas incidirão sobre o pagamento mensal, considerando as pontuações resultantes dos cálculos dos indicadores de níveis mínimos de serviço, em que 1 (um) ponto representa 0,001% de glosa (desconto);"

Fórmula formal, reafirmada na tabela em `07_modelo_de_gestao.html:936-961` (dentro do trecho sobre recebimento definitivo/pagamento):

```
Ajuste_NMS (%) = Σ Pontos_NMS × 0,001
```

Onde (definições do próprio documento, linhas 942-957):

- **Ajuste_NMS**: ajuste (glosa) em função dos resultados aferidos pelos Indicadores de Níveis Mínimos de Serviço (INMS).
- **Pontos_NMS**: pontuação acumulada como penalidade em função do descumprimento dos Níveis Mínimos de Serviço, **considerando os indicadores dispostos nos Anexos D e E** (ou seja, é a soma agregada de todos os indicadores, não um valor por indicador).

Isso confirma numericamente a regra em prosa: 1 ponto de penalidade = 0,001 (percentual) de glosa sobre o pagamento mensal. Ex.: 100 pontos acumulados no mês = 0,1% de glosa; 1000 pontos = 1% de glosa.

## 2. Faixas/degraus, teto e o que acontece acima do teto

**Não há faixas/degraus** — é uma fórmula linear contínua (pontos × 0,001%, sem tabela de tiers).

Há, porém, um **teto (cap) de 30% do valor mensal** (`07_modelo_de_gestao.html:229-236`, repetido em `1054-1062`):

> "A glosa sobre o pagamento mensal será aplicada atê o limite de 30% do valor total mensal, podendo o CONTRATANTE aplicar acumuladamente outras sanções administrativas cabíveis. Caso o saldo devedor, ultrapasse o limite de 30% de glosa estabelecido, **o restante poderá ser aplicado na fatura do mês subsequente**, com a exceção do último mês de vigência do contrato;"

Regra adicional de escalonamento para reincidência (`07_modelo_de_gestao.html:243-247`):

> "Caso o percentual de glosa ultrapasse o limite acima de 03 (três) vezes em um período de 06 (seis) meses, será caracterizada **INEXECUÇÃO PARCIAL DO CONTRATO**, sujeitando a CONTRATADA às sanções cabíveis;"

Resumo do comportamento acima do teto:
1. Glosa do mês é limitada a 30% do valor mensal.
2. O excedente (saldo devedor) rola para a fatura do mês seguinte — exceto se for o último mês de vigência do contrato (nesse caso não há "mês seguinte" para rolar).
3. Se isso (ultrapassar 30%) acontecer 3+ vezes em uma janela de 6 meses, o evento é requalificado como inexecução parcial contratual, disparando outras sanções administrativas (fora do escopo do cálculo de glosa em si).

## 3. Agregação: por indicador ou pontuação total do mês?

A pontuação usada na fórmula é o **somatório (Σ) de todos os `Pontos_NMS`** — soma agregada de todos os INMS do mês (Anexos D e E), não uma glosa calculada indicador-a-indicador e depois somada percentual a percentual. Texto de apoio (`07_modelo_de_gestao.html:941-946`, alínea de cálculo):

> "Cálculo e encaminhamento à CONTRATADA de indicação de eventuais glosas e sanções por descumprimento de níveis mínimos de serviço exigidos... **Será descontado da parcela mensal o somatório de pontos acumulados na aferição dos níveis mínimos de serviço multiplicados por 0,001** conforme fórmula a seguir."

Ou seja: soma os `penalty_points` de todos os 14 INMS do mês primeiro → multiplica o total por 0,001% → aplica isso como um único percentual de glosa sobre o pagamento mensal (ou por item de contrato, ver seção 4).

## 4. É suficiente para especificar a aba GLOSAS do Excel final?

**Sim, para o núcleo do cálculo.** As três colunas descritas no ticket ficam assim:

- **percentual de ajuste** = `min(30%, Σ penalty_points_do_mês × 0,001%)`
- **valor-base** = valor/parcela mensal a que a glosa se aplica (ver ambiguidade abaixo sobre granularidade "por item")
- **valor da glosa** = `percentual de ajuste × valor-base`

Isso está confirmado por uma segunda fórmula, na mesma seção (`07_modelo_de_gestao.html:965-1010`), que expressa o desconto monetário final:

```
Desconto Regulatório_Anual = max[0; min(Desconto Máximo_Anual; Ajuste_NMS(%) × RB)]
```

com `Pagamento_mensal` e `PM_por_item` (parcela mensal de cada item contratado do grupo, conforme Ordem de Serviço) definidos ao lado (linhas 1013-1030).

**Ambiguidade residual a reportar:**

- Os termos `RB` e `Desconto Máximo Anual` (e o rótulo "Desconto Regulatório **Anual**") usados nesta segunda fórmula **não são definidos em nenhum outro lugar do documento** — não há grep hit para "Receita Bruta" nem para "Desconto Máximo" fora dessa própria tabela (`grep -n "RB\b\|Receita Bruta\|Desconto Máximo" 07_modelo_de_gestao.html` só retorna as 3 ocorrências dentro da própria fórmula MathML). Isso tem cheiro de boilerplate copiado de um template de contrato regulatório genérico (o rótulo "Anual" também destoa do resto do item, que é inteiramente mensal — glosa mensal, teto de 30% do valor mensal, fatura do mês subsequente). **Não é seguro tratar essa segunda fórmula como a fonte de verdade operacional** para o cálculo mensal; a primeira fórmula (`Ajuste_NMS(%) = Σ Pontos_NMS × 0,001`, com teto de 30% do valor mensal, tudo em base mensal) é a que tem definições completas e consistentes com o resto do item 35 e deve ser a usada no spec.md.
- Não fica explícito no texto lido se "valor mensal"/"valor total mensal" é o valor do contrato inteiro ou o valor de cada item/Ordem de Serviço separadamente (o texto usa ambos "pagamento mensal" e, na segunda fórmula, "PM_por_item"/"parcela mensal de cada item contratado do grupo"). Para a spec, a leitura mais segura e conservadora é: a glosa percentual (`Ajuste_NMS`) é um único percentual mensal, agregado sobre todos os INMS, aplicado sobre a base de pagamento mensal relevante (a definir se é por item ou total — recomenda-se assumir "valor total mensal" citado explicitamente nas regras de teto, salvo indicação em contrário do gestor).

**Conclusão:** a informação é suficiente para especificar a fórmula central da aba GLOSAS (pontos → percentual → valor de glosa, com teto de 30% e rollover), com uma ressalva documentada sobre a segunda fórmula (RB/Desconto Máximo Anual) que aparenta ser um artefato de template não aplicável literalmente aqui, e uma ambiguidade menor sobre granularidade de "valor-base" (contrato total vs. por item) que pode ser resolvida por convenção no spec.md sem precisar de esclarecimento externo.
