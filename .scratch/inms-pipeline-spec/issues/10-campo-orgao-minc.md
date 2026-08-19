Type: research
Status: resolved

## Question

`docs/spreadsheet.md` assume segregação MinC/MTur por linha na aba `INMS_BASE` e nas abas por grupo operacional. Os datasets reais de produção (`/Users/joao/dev/pyauditor/input/`, 14 pares) têm essa segregação? Se não, a spec deve fingir que existe (fog), ou modelar o campo com um valor fixo desde já?

## Answer

Inspecionados os 14 CSVs reais em `/Users/joao/dev/pyauditor/input/`: nenhum tem segregação MinC/MTur — todo registro com campo `Contrato` mostra apenas `"40/2022 - Ministério Cultura"`. Isso contradiz a estrutura assumida por `docs/spreadsheet.md`.

Decisão: **modelar o campo `orgao` desde já no schema, com valor fixo `"MinC"`** (evita retrabalho de schema quando/se aparecer dado de MTur), mas a *lógica* de consolidação ponderada MinC+MTur (fórmula em `docs/spreadsheet.md`: `(Numerador MinC + Numerador MTur) / (Denominador MinC + Denominador MTur)`) fica fora do destino atual — é fog até existir um dataset real com os dois órgãos (ver "Not yet specified" no mapa).
