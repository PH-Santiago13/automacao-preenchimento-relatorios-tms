# Automação RPA de relatórios e fechamento de dezena (TMS SSW)

Automatizei com Python a extração, a consolidação e a conferência dos relatórios operacionais de um TMS (SSW) usado em uma operação logística com três unidades (BHZ, SPT e SPO). Troquei um processo manual, veículo por veículo, por um fluxo supervisionado que roda do login até o arquivo final.

## Resultado

| Rotina | Antes | Depois | Redução |
|---|---|---|---|
| Relatório diário consolidado | 4–6 h, manual | ~1 h, supervisionado | ~75–80% |
| Fechamento de dezena | 12 h | 6 h | ~50% |

Medi os tempos na minha própria rotina de trabalho, comparando a execução manual com a execução automatizada.

## O que eu fiz

- **Automatizei o acesso ao TMS** com PyAutoGUI: login, navegação entre telas, solicitação dos relatórios das três unidades e download dos arquivos.
- **Criei o fluxo diário** (`preenchimento_diario_v1.py`) em etapas independentes. Cada etapa é registrada em log e, se uma delas falha, o script para e salva uma captura da tela, em vez de continuar digitando às cegas.
- **Estruturei o processamento com pandas** (`processar_relatorios.py`): li os arquivos `.sswweb` (texto separado por `;`, codificação latin-1), normalizei nomes de colunas, converti valores no padrão brasileiro (`1.234,56`) e separei as linhas válidas das que precisam de revisão.
- **Consolidei os dados por placa**: uma linha por veículo, com coletas e entregas lado a lado, e gerei um arquivo de revisão para os registros com problema.
- **Validei as placas** com expressão regular (formato antigo e Mercosul) e tratei placas vazias e repetidas.
- **Implementei o fechamento de dezena** (`fechamento_dezena.py`): calculei a última dezena encerrada, somei os pagamentos por placa, conferi a produção por veículo e unidade, extraí os KMs percorridos e montei um PDF consolidado com uma captura por veículo, além de um ZIP com os relatórios do período.
- **Escolhi falhar de forma explícita**: se falta o relatório de uma das três unidades, o processamento para com erro, em vez de somar só duas e entregar um número errado sem aviso.
- **Protegi o ambiente de execução**: antes de cada ação, o script confirma que a janela esperada está ativa, espera o título da tela aparecer e volta ao menu com `ESC` quando necessário.
- **Defini o dia de referência automaticamente**: de segunda-feira o relatório é o de sexta; nos demais dias, o de ontem.

## Por que RPA e não API

O SSW não expõe uma API para os relatórios de que eu precisava; o único ponto de acesso é a interface web. Por isso automatizei a interface, com os cuidados de espera e conferência de tela descritos acima.

## Estrutura do projeto

| Arquivo | Função |
|---|---|
| `preenchimento_diario_v1.py` | Fluxo diário: login, extração por unidade, download, organização e processamento |
| `coletar_downloads.py` | Move e renomeia os downloads para `entrada/AAAA-MM-DD/` |
| `processar_relatorios.py` | Lê, valida e consolida os relatórios (gera `producao_consolidada.csv`, `revisao.csv` e `manifesto.csv`) |
| `fechamento_dezena.py` | Fechamento de dezena, conferência por veículo, PDF de KMs e ZIP do período |
| `utils.py` | Log diário, dia de referência, captura de tela no erro e espera por janelas |
| `descobrir_titulos.py` | Utilitário para listar os títulos das janelas abertas e mapear as telas |
| `.env.example` | Modelo das variáveis de ambiente (sem valores reais) |
| `dados_placas.exemplo.xlsx` | Modelo da planilha de placas, com dados fictícios |

## Tecnologias

- **Python** com **pandas** e **numpy** para tratamento de dados
- **PyAutoGUI** e **PyGetWindow** para automação de interface
- **python-dotenv** para credenciais
- **ReportLab** para o PDF consolidado
- **openpyxl** para leitura de planilhas Excel

## Como executar

1. Clone o repositório e crie um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copie `.env.example` para `.env` e preencha com as suas credenciais e o caminho da planilha de produção:
   ```bash
   copy .env.example .env
   ```
3. Copie `dados_placas.exemplo.xlsx` para `dados_placas.xlsx` e preencha com as suas placas (aba `Planilha1`).
4. Execute o fluxo diário ou o fechamento de dezena, com o TMS acessível e a tela livre:
   ```bash
   python preenchimento_diario_v1.py
   python fechamento_dezena.py
   ```

Desenvolvi e usei o projeto no Windows. Durante a execução, deixo a tela livre, sem mexer no mouse ou no teclado.

## Segurança e privacidade

- Mantive login, senha e CPF fora do código, em variáveis de ambiente (`.env`), e o `.gitignore` impede que o arquivo suba para o repositório.
- Deixei fora do repositório todos os dados reais: placas, motoristas, valores, relatórios baixados do TMS, logs e capturas de tela.
- O repositório contém só o código e um exemplo com dados fictícios.

## Limitações conhecidas

RPA que simula teclado e mouse é frágil a mudanças de layout do sistema: um campo em outra posição, um pop-up novo ou um tempo de carregamento maior podem exigir ajuste. Por isso o fluxo é supervisionado e para na primeira falha, com log e captura de tela para diagnóstico.

## Autor

Paulo Henrique Santiago da Silva — [LinkedIn](https://www.linkedin.com/in/hpaulo13/)
