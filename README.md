# Automação de Preenchimento e Fechamento de Dezena — SSW (RPA com Python)

Automação em Python que elimina o preenchimento manual, veículo por veículo, de relatórios operacionais em um sistema de gestão de transportes (TMS), reduzindo o tempo da tarefa em **~70%** (de 6–7 horas para ~2 horas por execução).

## O problema

Diariamente era preciso acessar o TMS da empresa, extrair relatórios de três unidades operacionais e consolidar os dados em uma planilha de controle, veículo por veículo. No fim de cada dezena (período de 10 dias) o processo se repetia em escala maior: conferir os relatórios do período, bater os valores com a planilha de controle e gerar as Ordens de Serviço (O.S.) para o financeiro pagar os agregados.

Tudo era **manual**, repetitivo e sujeito a erro humano.

## Por que RPA, e não API

O SSW (TMS muito usado em transporte e logística) não expõe API pública para os relatórios necessários — o único ponto de acesso é a interface web. A solução viável foi RPA: simular as ações de um usuário (teclado, navegação) de forma programática, com verificações de estado para não digitar às cegas.

## Arquitetura

```
preenchimento_diario.py   -> orquestra a rotina diária (RPA + chamadas abaixo)
├── utils.py              -> log em arquivo, espera por título de janela, print do erro
├── coletar_downloads.py  -> move/renomeia os downloads para entrada/AAAA-MM-DD/
└── processar_relatorios.py -> valida, separa linhas problemáticas e consolida por placa (pandas)

fechamento_dezena.py      -> fechamento de dezena (RPA + PDF de KMs + ZIP final)
descobrir_titulos.py      -> utilitário para anotar os títulos das janelas do sistema
```

### `preenchimento_diario.py`
Roda por etapas e **para na primeira falha** (com log e print da tela em `logs/`) — melhor parar do que continuar digitando às cegas:

1. Abre o navegador, acessa o sistema e faz login
2. Exporta romaneios (opção 36)
3. Solicita o relatório da opção 76 para cada unidade (BHZ, SPT, SPO)
4. Exporta manifestos (opção 200)
5. Baixa os relatórios pela fila de processamento (opção 156)
6. Python assume: organiza os arquivos por dia e gera os CSVs finais

Saídas em `saida/AAAA-MM-DD/`:
- `producao_consolidada.csv` — uma linha por placa (coletas e entregas lado a lado, rota, motorista, cidade/bairro de entrega)
- `manifesto.csv` — manifesto reduzido às colunas do formato final
- `revisao.csv` — linhas que falharam nas validações (placa vazia, fora do formato, fora da lista, tipo de baixa inválido, peso/valor ilegível)

O dia-alvo é calculado automaticamente (segunda-feira usa a sexta anterior).

### `fechamento_dezena.py`
Calcula a última dezena encerrada (1–10, 11–20, 21–fim do mês), lê os pagamentos de agregados da planilha de produção e, para cada veículo (exceto "Cavalo"):

1. Solicita relatórios de produção por veículo (opções 76 e 413)
2. Captura os KMs percorridos (opção 93) e gera um PDF com resumo + uma captura por placa
3. Solicita os manifestos do período (opção 200)
4. Lança as O.S. de pagamento por prestação de serviço (opção 118)
5. Coleta os arquivos baixados e compacta tudo em um ZIP do fechamento

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| Tempo por execução | 6–7 horas | ~2 horas |
| Redução de tempo | — | **~70%** |
| Processo | Manual, veículo por veículo | Automatizado, supervisionado |

## Tecnologias

Python · PyAutoGUI · pygetwindow · pandas/NumPy · openpyxl · ReportLab · python-dotenv · pywin32 (clipboard)

## Limitações conhecidas

- **Frágil a mudanças de tela:** RPA por simulação de interface quebra se o SSW mudar campos, pop-ups ou tempos de carregamento. As esperas por título de janela e a parada na primeira falha reduzem o risco, mas não o eliminam.
- **Exige a máquina destravada:** o robô usa teclado e mouse reais; não dá para usar o computador durante a execução.
- **Somente Windows** (clipboard via `pywin32`, títulos de janela via `pygetwindow`).
- **Não substitui uma API**, caso o sistema passe a oferecer uma.

## Configuração

1. Clone o repositório e instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Copie `.env.example` para `.env` e preencha (credenciais, caminho da planilha de produção):
   ```bash
   cp .env.example .env
   ```
3. Forneça a lista de placas (`dados_placas.xlsx`, aba `Planilha1`, colunas `Placa` e `MOTORISTA`). Há um modelo fictício em `exemplos/dados_placas.exemplo.xlsx`.
4. Execute:
   ```bash
   python preenchimento_diario.py
   python fechamento_dezena.py
   ```

### Testando o processamento sem acessar o sistema

O consolidador roda offline com dados fictícios incluídos em `exemplos/`:

```bash
# Windows (PowerShell)
$env:ARQUIVO_PLACAS="exemplos/dados_placas.exemplo.xlsx"
python processar_relatorios.py exemplos/entrada/2026-01-15
```
Resultado em `saida_teste/`.

## Aviso

Os scripts foram desenvolvidos para um processo operacional específico. Credenciais, dados de clientes, motoristas, placas, logs e capturas de tela **não** fazem parte do repositório (ver `.gitignore`); todos os dados em `exemplos/` são fictícios.
