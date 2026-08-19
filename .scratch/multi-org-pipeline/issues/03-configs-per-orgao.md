Type: grilling
Status: resolved
Blocked by: 01

## Question

Decidir o **layout de configs por órgão** (`configs/<órgão>/inms-*.yaml`):

- Como `discover_configs` se torna órgão-aware: o `measure`/`report` com `--orgao MinC` lê `configs/MinC/`, com `both` lê os dois? O manifesto `datasets.yaml` também fica por órgão?
- MTur: os configs MTur são cópias idênticas dos MinC por agora, ou já diferem (metas, penalidades, valores)? Há algum órgão que não implementa algum INMS?
- Como evitar drift entre MinC e MTur: copia literal, o compartilhado + overrides por órgão, ou outra mecánica?
- Relação com `Scope.orgao` atual (`Literal["MinC","MTur"]`): o `--orgao` substitue o campo do config, ou o valida (mismatch = erro)?

## Answer

Layout de configs por órgão decidido em grilling (19/08/2026):

- **Diretórios**: `configs/<órgão>/inms-*.yaml`, já criados no disco pelo usuário (MinC e MTur, 14 configs cada). `discover_configs` deriva o diretório do `--orgao`; `both` = união MinC+MTur. Ausência de arquivo = indicador não implementado naquele órgão (sem registry extra).
- **`scope.orgao`**: mantido no YAML e **validado** contra o `--orgao`/diretório (mismatch = erro claro). Todos os 14 configs MTur atualizados para `orgao: MTur` (MinC já estava correto).
- **MTur hoje**: cópia literal dos 14 configs MinC (metas/penalidades idênticos), divergência legítima só nasce com dados reais do MTur. O CTé o mesmo instrumento (`contract: "40/2022 - Ministério Cultura"` fica como rótulo único do contrato); nome do órgão na capa é assunto do `capa_<orgao>.xlsx`.
- **INMS 1.2**: `%Ajuste` surge da engine (`segmented_ratio` com step_points por categoria 20/15/10); desvio manual entra pela **decisão de anistia/edição do fiscal** (ticket 02), sem override manual no config.
- **Manifest `datasets.yaml`**: por órgão (`configs/<órgão>/datasets.yaml`), criado pelo usuário — hoje cópias idênticas; divergência de nome de arquivo por órgão fica suportada por construção.