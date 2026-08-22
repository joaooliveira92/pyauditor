Atue como um engenheiro de software sênior especializado em Python 3.12+, arquitetura limpa, SOLID e refatoração segura.

Analise recursivamente este repositório e identifique arquivos Python que apresentam sinais de precisar de refatoração ou divisão, especialmente por possível violação do Single Responsibility Principle, SRP.

Nesta etapa, não modifique nenhum arquivo. Produza apenas um relatório técnico baseado em evidências encontradas no código.

use a skill: `.agents/skills/python-production-engineer/SKILL.md` 

## Escopo

1. Analise todos os arquivos `*.py` do projeto.
2. Ignore:
   - `.venv/`
   - `venv/`
   - `build/`
   - `docs/`
   - `.git/`
   - `.tox/`
   - `.mypy_cache/`
   - `.pytest_cache/`
   - `__pycache__/`
   - dependências vendorizadas;
   - arquivos gerados automaticamente;
   - migrations, salvo quando contiverem lógica manual relevante;
   - snapshots e fixtures compostas principalmente por dados.
3. Considere separadamente:
   - código de produção;
   - testes;
   - scripts;
   - arquivos gerados;
   - configurações Python.

Não classifique um arquivo como problemático apenas por possuir muitas linhas. A contagem de linhas deve funcionar somente como um sinal inicial. A conclusão precisa considerar coesão, acoplamento, complexidade e quantidade de motivos independentes para mudança.

## Sinais quantitativos

Utilize as seguintes faixas como heurísticas, não como regras absolutas:

- arquivo com mais de 300 linhas: observar;
- arquivo com mais de 500 linhas: candidato relevante à revisão;
- arquivo com mais de 800 linhas: candidato prioritário à divisão;
- função ou método com mais de 40 linhas: revisar possibilidade de extração;
- classe com mais de 200 linhas: revisar acúmulo de responsabilidades;
- função com muitos níveis de indentação;
- complexidade ciclomática elevada;
- grande quantidade de imports;
- grande quantidade de símbolos públicos;
- muitos parâmetros;
- uso frequente de condicionais para selecionar comportamentos distintos;
- baixa cobertura de testes em código complexo, caso dados de cobertura estejam disponíveis.

Desconsidere linhas em branco e comentários ao avaliar o tamanho lógico, mas informe também o total físico quando for possível.

## Sinais arquiteturais e qualitativos

Procure evidências de:

1. Um mesmo arquivo contendo múltiplas responsabilidades, como:
   - regras de negócio;
   - acesso a banco de dados;
   - chamadas HTTP;
   - serialização;
   - validação;
   - logging;
   - configuração;
   - interface CLI;
   - apresentação ou formatação;
   - integração com sistema operacional.

2. Múltiplos motivos independentes para o arquivo mudar.

3. Classes do tipo God Object ou Manager que:
   - conhecem muitos subsistemas;
   - mantêm estado de domínios diferentes;
   - coordenam e também executam detalhes de infraestrutura;
   - concentram muitos métodos não relacionados.

4. Funções ou classes com baixa coesão.

5. Dependências entre camadas em direção inadequada.

6. Mistura entre domínio, aplicação, infraestrutura e interface.

7. Código duplicado ou blocos semelhantes.

8. Funções privadas que formam grupos coesos e poderiam ser extraídas para módulos próprios.

9. Arquivos genéricos como:
   - `utils.py`;
   - `helpers.py`;
   - `common.py`;
   - `manager.py`;
   - `service.py`.

   Não considere o nome, isoladamente, como evidência de problema. Verifique se o conteúdo realmente mistura conceitos não relacionados.

10. Inicializadores, handlers, controllers ou services que concentram orquestração, validação, persistência e transformação de dados.

11. Alterações que aparentemente exigiriam modificar muitas partes do mesmo arquivo.

12. Testes difíceis de isolar devido a dependências globais, efeitos colaterais ou construção excessiva de objetos.

## Critérios de classificação

Classifique cada candidato com uma prioridade:

- CRÍTICA: responsabilidades claramente distintas, forte acoplamento e alto risco de manutenção;
- ALTA: múltiplos sinais fortes de violação de SRP ou complexidade excessiva;
- MÉDIA: arquivo grande ou complexo, mas ainda relativamente coeso;
- BAIXA: oportunidade de melhoria sem urgência;
- NÃO RECOMENDADA: arquivo grande cuja divisão provavelmente reduziria a clareza ou aumentaria a fragmentação.

Para cada classificação, explique as evidências. Não atribua prioridade apenas com base em quantidade de linhas.

## Processo obrigatório

1. Identifique a estrutura e as camadas do projeto.
2. Determine a finalidade aparente de cada pacote.
3. Analise os maiores arquivos primeiro.
4. Examine classes, funções, imports e dependências.
5. Identifique responsabilidades reais em cada candidato.
6. Verifique referências e consumidores antes de sugerir divisões.
7. Considere o impacto sobre APIs públicas.
8. Considere riscos de ciclos de importação.
9. Verifique os testes relacionados.
10. Ordene os candidatos por prioridade e benefício esperado.

Se ferramentas estiverem disponíveis, utilize preferencialmente:

- `ruff`;
- `mypy`;
- `radon`;
- `xenon`;
- `pytest`;
- cobertura de testes;
- análise da árvore sintática com `ast`.

Não instale dependências e não altere configurações sem necessidade. Se uma ferramenta não estiver disponível, continue com análise estática e registre essa limitação.

## Formato da saída

Produza o relatório nas seguintes seções:

### 1. Resumo executivo

Informe:

- quantidade de arquivos Python analisados;
- quantidade total aproximada de linhas;
- quantidade de candidatos encontrados por prioridade;
- principais riscos arquiteturais;
- cinco arquivos com maior retorno potencial de refatoração.

### 2. Ranking dos candidatos

Para cada arquivo, informe:

- caminho;
- prioridade;
- linhas físicas e lógicas;
- principais classes e funções envolvidas;
- responsabilidades identificadas;
- motivos independentes para mudança;
- sinais quantitativos;
- evidências qualitativas;
- dependências relevantes;
- risco da refatoração;
- benefício esperado;
- confiança da análise: alta, média ou baixa.

### 3. Plano sugerido por arquivo

Para cada candidato relevante, proponha:

- quais responsabilidades separar;
- possíveis nomes e caminhos para os novos módulos;
- quais símbolos seriam movidos;
- o que deveria permanecer no arquivo original;
- dependências que precisariam ser invertidas ou injetadas;
- estratégia para preservar a API pública;
- testes necessários antes da alteração;
- testes necessários depois da alteração;
- ordem segura de execução.

Não proponha divisões artificiais baseadas somente em quantidade de linhas. Cada módulo sugerido deve possuir responsabilidade clara, alta coesão e nome representativo.

### 4. Falsos positivos e arquivos grandes aceitáveis

Liste arquivos grandes que não recomenda dividir e explique por quê.

### 5. Plano incremental

Organize as recomendações em pequenas etapas, priorizando:

1. criação ou fortalecimento de testes;
2. extrações sem alteração de comportamento;
3. redução de dependências;
4. divisão de módulos;
5. melhoria de nomes e APIs;
6. remoção de duplicações.

### 6. Validações recomendadas

Informe os comandos exatos para validar cada etapa, respeitando as ferramentas e o gerenciador de dependências já adotados pelo projeto.

## Restrições

- Não altere comportamento observável.
- Não crie abstrações sem necessidade concreta.
- Não transforme automaticamente funções em classes.
- Não mova código sem analisar consumidores e imports.
- Não sugira `utils.py`, `helpers.py` ou `common.py` como destino genérico.
- Não considere arquivos de teste grandes automaticamente problemáticos.
- Não invente métricas, dependências ou resultados.
- Diferencie fatos observados de hipóteses.
- Inclua referências precisas a arquivos, classes, funções e linhas.
- Quando houver incerteza, declare-a explicitamente.