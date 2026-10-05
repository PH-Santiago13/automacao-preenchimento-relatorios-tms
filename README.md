[README.md](https://github.com/user-attachments/files/33055965/README.md)

# Automação de Relatórios e Fechamento de Dezena — TMS (RPA + Python)

> **De 4–6 horas para ~1 hora** na geração dos relatórios e **de 12 para 6 horas** no fechamento de dezena — e o tempo que sobrou virou análise de verdade (WoW e MTD), não mais digitação.

Automação em Python que assume o trabalho braçal de extrair, conferir e consolidar relatórios operacionais de um TMS (sistema de gestão de transportes), veículo por veículo, para que o analista foque no que gera valor: **entender os números e antecipar problemas**.

---

## Impacto

| Processo | Antes | Depois | Redução |
|---|---|---|---|
| Geração dos relatórios diários | 4–6 h | ~1 h | **75% a 83%** |
| Fechamento de dezena | ~12 h | ~6 h | **50%** |

**O que isso muda na prática**

- **Menos estresse:** acabou a maratona de copiar e colar placa por placa e o medo de errar um número no meio do caminho. O robô faz a parte repetitiva e o analista só supervisiona e confere.
- **Mais confiança nos números:** toda linha suspeita (placa vazia, fora do padrão, fora da lista, tipo de baixa inválido, peso/valor ilegível) é separada em um arquivo de revisão em vez de passar batida ou travar tudo.
- **Mais tempo para analisar:** as horas liberadas foram reinvestidas nos acompanhamentos **semanais (WoW — *week over week*, comparação com a semana anterior)** e **mensais (MTD — *month to date*, acumulado do mês até hoje)**, que antes ficavam em segundo plano.
- **Rotina previsível:** a cada execução o resultado sai no mesmo formato, na mesma pasta, com log do que aconteceu.

---

## O problema

Todo dia era preciso entrar no TMS, extrair relatórios de três unidades operacionais e consolidar tudo numa planilha de controle, veículo por veículo. No fim de cada dezena (período de 10 dias), o trabalho se repetia em escala maior: conferir os relatórios do período, bater os valores com a planilha de controle e gerar as Ordens de Serviço (O.S.) para o financeiro pagar os agregados (veículos terceirizados).

Era um processo **manual, repetitivo e sujeito a erro humano**, que consumia boa parte do expediente antes de sobrar tempo para olhar o que os números diziam.

## Por que RPA, e não API

O SSW (TMS muito usado em transporte e logística) não expõe API pública para os relatórios necessários — o único ponto de acesso é a interface web. A solução viável foi **RPA**: simular as ações de um usuário (teclado e navegação) de forma programática, com verificações de estado para nunca digitar às cegas.

---

## Como funciona

**Rotina diária** (`preenchimento_diario.py`)

1. O robô abre o sistema, faz login e solicita os relatórios de cada unidade (BHZ, SPT, SPO), romaneios e manifestos.
2. Os arquivos baixados são organizados por dia automaticamente.
3. O Python lê tudo, valida, soma por placa e entrega os arquivos prontos.

O dia-alvo é calculado sozinho: na segunda-feira ele puxa a sexta anterior; nos demais dias, o dia anterior.

**Saídas** em `saida/AAAA-MM-DD/`:

| Arquivo | O que tem |
|---|---|
| `producao_consolidada.csv` | Uma linha por placa: coletas e entregas lado a lado, rota, motorista, cidade e bairro de entrega |
| `manifesto.csv` | Manifesto reduzido às colunas do formato final |
| `revisao.csv` | Linhas que falharam nas validações, com o motivo de cada uma |

**Fechamento de dezena** (`fechamento_dezena.py`)

Calcula sozinho a última dezena encerrada (1–10, 11–20, 21–fim do mês), lê os pagamentos de agregados da planilha de produção e, para cada veículo, executa o ciclo completo:

1. Solicita os relatórios de produção por veículo
2. Captura os KMs percorridos e gera um **PDF** com resumo + uma captura por placa
3. Solicita os manifestos do período
4. Lança as O.S. de pagamento por prestação de serviço
5. Reúne tudo em um **ZIP** pronto do fechamento

---

## Decisões de engenharia que fazem diferença

- **Para na primeira falha:** se algo sai do esperado, o robô interrompe, grava o log e tira um print da tela. Melhor parar do que continuar digitando errado dentro de um sistema financeiro.
- **Espera por estado, não por tempo:** em vez de `sleep` fixo, aguarda a janela certa aparecer (com timeout), o que torna a execução mais rápida e mais estável.
- **Validação antes da consolidação:** placas no padrão antigo e Mercosul, lista de placas da filial, tipo de baixa (C/E) e números no formato brasileiro (`1.234,56`) são tratados antes de somar qualquer coisa.
- **Não soma pela metade:** se faltar o relatório de uma unidade, o processo avisa em vez de consolidar só duas das três.
- **Leitura tolerante a mudanças de layout:** o cabeçalho dos relatórios é localizado dinamicamente e os nomes de coluna são normalizados.
- **Rastreabilidade:** log diário em arquivo e print automático do erro.
- **Segurança:** credenciais em `.env`, nunca no código; dados reais fora do repositório.

---

## Estrutura do projeto

```
preenchimento_diario.py     -> orquestra a rotina diária (RPA + processamento)
├── utils.py                -> log, espera por título de janela, print de erro, dia-alvo
├── coletar_downloads.py    -> move/renomeia os downloads para entrada/AAAA-MM-DD/
└── processar_relatorios.py -> valida, separa linhas problemáticas e consolida por placa (pandas)

fechamento_dezena.py        -> fechamento de dezena (RPA + PDF de KMs + ZIP final)
descobrir_titulos.py        -> utilitário para mapear os títulos das janelas do sistema
exemplos/                   -> dados 100% fictícios para testar sem acessar o sistema
```

## Tecnologias

Python · PyAutoGUI · pygetwindow · pandas · NumPy · openpyxl · ReportLab · python-dotenv · pywin32

---

## Limitações conhecidas

- **Sensível a mudanças de tela:** RPA por interface pode quebrar se o sistema mudar campos, pop-ups ou tempos de carregamento. As esperas por título de janela e a parada na primeira falha reduzem o risco, mas não o eliminam.
- **Exige supervisão e máquina liberada:** o robô usa teclado e mouse reais; durante a execução o computador fica ocupado. É por isso que o tempo final é ~1 h (e ~6 h no fechamento), e não zero.
- **Somente Windows** (clipboard via `pywin32`, janelas via `pygetwindow`).
- **Não substitui uma API**, caso o sistema passe a oferecer uma.

---

## Como rodar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Copie `.env.example` para `.env` e preencha (credenciais e caminho da planilha de produção):
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

O resultado aparece em `saida_teste/`.

---

## Aviso

Os scripts foram desenvolvidos para um processo operacional específico. Credenciais, dados de clientes, motoristas, placas, logs e capturas de tela **não** fazem parte do repositório (ver `.gitignore`); todos os dados em `exemplos/` são fictícios.
