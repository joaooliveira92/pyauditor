Type: grilling
Status: claimed
Claimed by: wayfinder session (opencode)

## Question

Decidir o **layout de configs por órgão** (`configs/<órgão>/inms-*.yaml`):

- Como `discover_configs` se torna órgão-aware: o `measure`/`report` com `--orgao MinC` lê `configs/MinC/`, com `both` lê os dois? O manifesto `datasets.yaml` também fica por órgão?
- MTur: os configs MTur são cópias idênticas dos MinC por agora, ou já diferem (metas, penalidades, valores)? Há algum órgão que não implementa algum INMS?
- Como evitar drift entre MinC e MTur: copia literal, o compartilhado + overrides por órgão, ou outra mecánica?
- Relação com `Scope.orgao` atual (`Literal["MinC","MTur"]`): o `--orgao` substitue o campo do config, ou o valida (mismatch = erro)?

## Answer

(aberto)