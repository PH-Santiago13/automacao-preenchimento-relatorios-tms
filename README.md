# Automação de Preenchimento e Fechamento de Dezena — SSW (RPA com Python)

Automação em Python que elimina o preenchimento manual, veículo por veículo, de relatórios operacionais em um sistema de gestão de transportes (TMS), reduzindo o tempo da tarefa em **~70%** (de 6–7 horas para 2 horas por execução).

## O problema

Diariamente, era necessário acessar o sistema de gestão de transporte (TMS) da empresa, extrair relatórios de três unidades operacionais e consolidar os dados em uma planilha de controle, veículo por veículo. Ao final de cada dezena (período de 10 dias), o mesmo processo se repetia em escala maior: conferir os relatórios do período, bater os valores com a planilha de controle e gerar as Ordens de Serviço (O.S.) para o financeiro efetuar o pagamento dos agregados.

Esse processo era **100% manual**, repetitivo e sujeito a erro humano — consumindo quase um dia inteiro de trabalho (6 a 7 horas) para ser concluído.

## Por que RPA, e não uma integração via API

O sistema utilizado (SSW, um TMS amplamente usado no setor de transporte e logística) não expõe uma API pública para os relatórios necessários — o único ponto de acesso é a interface web. Diante disso, a solução viável foi automação via RPA (*Robotic Process Automation*): simular as ações de um usuário humano (digitação, navegação, atalhos de teclado) de forma programática e confiável.

## A solução

Dois scripts em Python, usando **PyAutoGUI** para automação de interface e **Pandas** para processamento de dados tabulares:

### 1. `preenchimento_diario.py`
Automatiza o login no sistema, a extração dos relatórios diários das três unidades operacionais (arquivos CSV), a limpeza das colunas desnecessárias e a consolidação dos dados na planilha de controle diária entregue aos gestores.

### 2. `fechamento_dezena.py`
Automatiza o processo de fechamento de dezena: para cada veículo (lido de uma planilha `Placas.csv`), extrai os relatórios de produção, manifestos e pagamento por prestação de serviço do período, preenchendo os dados necessários para a geração das Ordens de Serviço (O.S.) de pagamento aos agregados.

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| Tempo por execução | 6–7 horas | ~2 horas |
| Redução de tempo | — | **~70%** |
| Processo | Manual, veículo por veículo | Automatizado, supervisionado |

## Tecnologias

- **Python**
- **PyAutoGUI** — automação de interface (simulação de teclado/navegação)
- **Pandas** — leitura e processamento de dados tabulares (placas, valores)
- **python-dotenv** — gerenciamento seguro de credenciais

## Limitações conhecidas

RPA baseado em simulação de interface é, por natureza, **frágil a mudanças de layout ou tela** do sistema-alvo: qualquer alteração no SSW (posição de campos, novos pop-ups, tempo de carregamento) pode quebrar o fluxo. É uma solução funcional e de alto ganho imediato, mas não substitui uma integração via API caso ela venha a existir — é o trade-off assumido conscientemente diante da limitação do sistema legado.

## Configuração

1. Clone o repositório
2. Instale as dependências:
   ```bash
   pip install pyautogui pandas python-dotenv
   ```
3. Copie `.env.example` para `.env` e preencha com suas credenciais reais:
   ```bash
   cp .env.example .env
   ```
4. Garanta que o arquivo `Placas.csv` (usado no fechamento de dezena) esteja na mesma pasta do script, com as colunas `Placa` e `Valor`.

## Aviso

Os scripts foram desenvolvidos para uso interno em um processo operacional específico. Credenciais e dados sensíveis foram removidos e substituídos por variáveis de ambiente antes da publicação neste repositório.
