"""Pacote de contratos de comando — camada neutra entre `cli` e
`orchestration` (ticket 11 SRP). `contracts` segura as dataclasses de
resultado; `cli/*.py` reexportam e `orchestration/summary*.py` dependem
daqui, sem importar módulos `cli/*`.
"""
