# Termo de Referência modularizado

O arquivo `termo_de_referência.html` é o documento pai e carrega todos os arquivos HTML filhos por meio do atributo `data-include`.

## Execução

Sirva esta pasta por HTTP. Exemplo:

```bash
python3 -m http.server 8000
```

Depois abra `http://localhost:8000/termo_de_referência.html`.

## Observação sobre `prazos.html`

O documento enviado apenas referenciava `prazos.html`. O conteúdo desse filho não estava incorporado no arquivo e não foi enviado separadamente. Por isso, o pacote contém um arquivo marcador. Substitua-o pelo `prazos.html` original do projeto.
