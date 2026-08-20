Type: task
Status: resolved

## Question

INMS 1.8 (desconformidades técnicas, Anexo E) e INMS 1.10 (controles de segurança) têm schemas de preenchimento manual provisórios, testados e documentados (`docs/spec/inms-pipeline.md` §11.3, §2.2), mas nenhuma fonte primária confirma que sistema real, se algum, deveria alimentar esses dados — fog documentado desde a spec original, ainda aberto. Em 2026-06 ambos vieram vazios (confirmado pela fiscalização como "sem ocorrências"/zero atividade, não gap de dado — ver [[project-inms-pipeline-data-quality]] na memória), então isso não bloqueia a competência atual. Mas para competências futuras com desconformidades ou controles reais, alguém precisa perguntar à equipe de fiscalização/gestor do contrato qual sistema (CITSmart? outro?) registra isso, e revisar o schema provisório contra o formato real desse sistema.

## Answer

**Reenquadrado (2026-08-19)**: "qual sistema alimenta os dados" é a pergunta errada — pyauditor só consome o CSV num schema definido, não importa qual sistema upstream (CITSmart ou não) o gera. Checagem do padrão sugerido pelo usuário (INMS 1.4/`sistema_servico_nome`) mostrou que ele também usa nomes sintéticos hoje (`Barramento de Integracao` etc., não os nomes reais do Anexo G/Tabela 31) — ou seja, nem INMS 1.4 resolveu "sistema real", está no mesmo estado provisório.

Estado real, confirmado nos arquivos: `configs/MinC/inms-08.yaml` e `inms-10.yaml` (commit `a0d182e`, 2026-08-19) já têm schema definitivo (`precomputed_table`, colunas `servico_nome`/`dominio_controle`, `pontos_acima_meta`/`penalidade_pontos`) com acceptance tests passando. `input/.../inms-08.csv` e `inms-10.csv` já têm linhas nesse schema, marcadas `"Dados sinteticos"` na coluna `observacao` — sinal explícito de que fiscalização deve substituir os valores, mantendo a estrutura.

Gap remanescente, mais estreito que a pergunta original: **confirmar com fiscalização que esse schema (catálogo de serviço/domínio, pontos por item vs. total pré-agregado, colunas de framework de segurança) é de fato o que será preenchido** — não "qual sistema alimenta", mas "este layout está certo". Mesmo bloqueio externo de antes (resposta de fiscalização/gestor do contrato), só que agora com um artefato concreto (o schema já implementado) para validar, em vez de uma pergunta em aberto sem candidato.

**Atualização (2026-08-19) — fonte primária encontrada**: o RAS oficial (`docs/processo_de_pagamento_junho_2026/relatório_de_acompanhamento_de_serviço.html`, período 01/06/2026-30/06/2026) declara explicitamente: *"Foram utilizadas para conferência a ferramenta CITSmart... referente ao período de 01/06/2026 a 30/06/2026"* — resposta primária real para "qual sistema", pelo menos no nível geral da aferição mensal (não confirma se é indicador-específico para 1.8/1.10 particularmente).

Cross-checagem por indicador: a tabela do RAS para **INMS 1.14** lista exatamente os mesmos seis serviços, na mesma ordem, do `inms-14.csv` — (a) File Server, (b) Telefonia, (c) Mensageria, (d) Servidores de impressão, (e) WI-FI, (f) Rede — com resultado agregado **98,49%**, batendo exatamente com o CSV e com o comentário do config (`configs/MinC/inms-14.yaml`) sobre correção a partir do RAS. **Confirma que os dados de INMS 1.14 já são reais**, apesar de o `observacao` de cada linha ainda dizer "Dados sinteticos" (rótulo obsoleto de antes da correção) — corrigido nesta sessão para citar o RAS/CITSmart como fonte.

Em contraste, **INMS 1.4 não bate**: o RAS só dá um valor agregado único (99,92%), sem quebra por sistema, enquanto `inms-04.csv` tem 5 linhas sintéticas por `sistema_servico_nome` sem correspondência no RAS. INMS 1.4, 1.8 e 1.10 seguem não confirmados; só 1.14 tem fonte primária validada.
