# 12 - Logs sem dados sensíveis

Type: grilling
Status: open
Blocked by:

## Question

O review pede uma garantia de que os logs (ticket 05: `log_event`, `--log-format json`, `-v`/`-vv`) não vazam dados sensíveis. Isso exige antes uma decisão do domínio: **o que conta como sensível no contrato 40/2022?**

Candidatos, para decidir campo a campo:

- **CNPJ da contratada**: é dado contratual público (consta em processos SEI, editais) — provavelmente não é sensível.
- **Nomes dos fiscais (técnico, requisitante, administrativo) e gestor do contrato**: são servidores públicos identificados no processo — sensível no sentido de dado pessoal (LGPD), mesmo que o vínculo funcional seja público?
- **Caminhos de arquivo** (`arquivo=/home/usuario/...`): já aparecem nos logs hoje (ex.: `capa criada | arquivo=...`) — revelam estrutura de diretório local/nome de usuário do SO, não dado do domínio, mas ainda potencialmente informação a evitar em log compartilhado.
- **Valores monetários e pontuação de glosa**: são o próprio objeto do relatório — claramente não sensíveis nesse sentido.

Sem essa definição, não há o que um teste automatizado verifique — "sem dados sensíveis" não é checável até virar uma lista concreta de campos a redigir (ou a decisão explícita de que nada aqui precisa de redaction).

Contexto: review.md §"Operação" ("logs sem dados sensíveis"); ticket 05 (observabilidade, já implementado, sem política de redaction); graduado da névoa do mapa (ajuste-cli) ao fechar o ticket 09 (suíte de testes) e constatar que não há definição do que testar.
