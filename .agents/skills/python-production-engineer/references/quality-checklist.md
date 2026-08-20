# Checklist de qualidade

## Design
- [ ] Criterios de aceite atendidos
- [ ] Mudanca minima e coerente
- [ ] Dominio desacoplado de infraestrutura quando relevante
- [ ] Interfaces publicas e compatibilidade avaliadas

## Corretude
- [ ] Entradas e outputs validados
- [ ] Casos limite e estados invalidos tratados
- [ ] Recursos fechados deterministicamente
- [ ] Tempo, aleatoriedade e unidades explicitos

## Tipagem
- [ ] Interfaces publicas tipadas
- [ ] Sem `Any` evitavel
- [ ] Casts e ignores justificados e localizados
- [ ] Type checker executado

## Resiliencia
- [ ] Timeouts em chamadas remotas
- [ ] Retries limitados apenas para falhas transientes
- [ ] Idempotencia considerada
- [ ] Cancelamento e shutdown tratados quando aplicavel

## Seguranca
- [ ] Sem secrets ou PII em codigo e logs
- [ ] Entradas nao confiaveis validadas
- [ ] SQL parametrizado e subprocess seguro
- [ ] Menor privilegio aplicado
- [ ] Dependencias novas avaliadas

## Observabilidade
- [ ] Logs estruturados e acionaveis
- [ ] Correlation ID propagado quando aplicavel
- [ ] Metricas de taxa, erro e duracao consideradas
- [ ] Sem labels de alta cardinalidade

## Testes
- [ ] Caminho feliz
- [ ] Entradas invalidas
- [ ] Falha de dependencia
- [ ] Timeout/retry/cancelamento quando relevantes
- [ ] Duplicidade e falha parcial quando relevantes
- [ ] Testes deterministas

## Entrega
- [ ] Format, lint e typing aprovados
- [ ] Testes aprovados
- [ ] Build/package aprovado
- [ ] Documentacao atualizada
- [ ] Migrations e rollout avaliados
- [ ] Commit Conventional Commits sugerido
