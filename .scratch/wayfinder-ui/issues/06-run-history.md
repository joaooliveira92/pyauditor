# 06 — Histórico de execuções passadas

- **Type:** grilling
- **Status:** resolved
- **Blocked by:** —

## Question

`App.jobs` em `src/ui/server.py` já mantém todo job em memória pela vida do
processo do servidor, mas o cliente não tem como redescobrir `job_id`s
passados depois de recarregar/fechar a aba (sem endpoint de listagem, sem
memória no cliente). Vale expor isso como histórico de execuções? Se sim,
com que escopo, retenção, superfície de UI e forma de API?

## Answer

Vale expor — o dado já existe, então é ticket pequeno, não subsistema novo.

- **Escopo:** lista curta (últimas ~20 execuções), não só a última — útil
  pra comparar "essa mudança ajudou?" no loop de corrigir-e-tentar-de-novo.
- **Retenção:** `App.jobs` ganha um cap (últimos 20, evict do mais antigo) —
  trivial de adicionar junto do endpoint de listagem; remove a dependência
  de "o usuário reinicia com frequência".
- **UI:** dobrado dentro do painel Pipeline existente (lista
  colapsável) — feature leve e escopada à sessão, uma aba separada é mais
  chrome do que o valor justifica.
- **API:** novo `GET /api/pipeline` (listagem) — retorna job ids + resumo
  (command, status, started-at) dos jobs retidos; `GET
  /api/pipeline/<job_id>` existente não muda (segue servindo output/warnings
  completos de um job).
