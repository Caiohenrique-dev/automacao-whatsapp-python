# Automação de Contatos e Convites para WhatsApp com Python

Projeto desenvolvido para um cliente do segmento de perfumaria, utilizando Python, Selenium e SQLite para organizar contatos e automatizar o envio de convites para seu grupo VIP no WhatsApp.

## Contexto do projeto

O cliente já participava de uma comunidade de pessoas interessadas em perfumes e buscava ampliar seu próprio grupo VIP, reduzindo a dependência de investimentos em tráfego pago.

Para apoiar esse processo, foi desenvolvida uma automação em duas etapas: a primeira identifica os números visíveis na lista de participantes e os armazena em um banco SQLite; a segunda utiliza os contatos cadastrados para enviar uma mensagem com a apresentação da loja e um convite para o grupo VIP.

A ferramenta permite organizar os contatos, reduzir tarefas repetitivas e registrar as tentativas de envio. O objetivo comercial é aproximar pessoas interessadas em perfumaria das novidades, ofertas e ações da loja. A redução dos gastos com anúncios é um resultado esperado, ainda não mensurado.

## Funcionalidades

- Leitura de números exibidos na lista de participantes aberta pelo usuário.
- Rolagem da lista para procurar novos números visíveis.
- Armazenamento de contatos em SQLite.
- Prevenção de duplicidade por telefone no cadastro.
- Exportação de contatos para CSV.
- Carregamento de contatos pelo banco de dados ou CSV.
- Envio automático de mensagens de texto.
- Intervalo configurável entre os contatos.
- Registro de tentativas por campanha e telefone.
- Reutilização da sessão do WhatsApp em um perfil dedicado do Edge.

## Tecnologias utilizadas

- Python
- Selenium
- SQLite
- Microsoft Edge
- CSV

## Funcionamento

### Organização dos contatos

O usuário abre o WhatsApp Web, seleciona o grupo e acessa a lista completa de participantes.

O script tenta identificar a área da lista, percorre os itens e extrai sequências com formato de telefone. Os números encontrados são armazenados no banco e exportados para CSV.

A ferramenta não revela números ocultos. Quando um participante aparece somente pelo nome, seu telefone pode não ser capturado.

### Envio das mensagens

O script de envio carrega os contatos, abre as conversas e tenta enviar a mensagem configurada automaticamente.

Cada tentativa é registrada por campanha e telefone. O tratamento dos registros evita repetir automaticamente tentativas já processadas ou cujo resultado seja incerto.

O campo de mensagem vazio indica que a interface processou a ação, mas não comprova a entrega ao destinatário.

## Requisitos

- Python 3 instalado.
- Microsoft Edge instalado.
- Conexão com a internet.
- Conta do WhatsApp conectada ao perfil utilizado pelo script.

## Instalação

Instale a dependência:

    python -m pip install --upgrade selenium

Os demais módulos utilizados fazem parte da biblioteca padrão do Python.

## Configuração

No script de envio, ajuste:

- `ORIGEM`: escolha entre banco de dados e CSV.
- `BANCO`: caminho do banco de contatos.
- `CSV`: caminho do arquivo de contatos.
- `TABELA`: nome da tabela no SQLite.
- `COLUNA_TELEFONE`: coluna que contém os números.
- `CAMPANHA`: identificador da campanha.
- `MENSAGEM`: texto que será enviado.
- `INTERVALO`: pausa entre contatos.

Use uma mensagem de demonstração na versão pública do código. Mantenha dados e configurações reais do cliente fora do repositório.

## Execução

Execute o arquivo desejado pelo terminal:

    python nome_do_arquivo.py

Substitua `nome_do_arquivo.py` pelo nome do script de captura ou envio.

Na primeira execução, escaneie o QR Code na janela do Edge aberta pela automação.

No capturador, abra o grupo e a lista completa de participantes antes de confirmar a continuação no terminal.

No envio, o processamento começa automaticamente após a conexão e o carregamento dos contatos.

Não execute os dois scripts simultaneamente utilizando o mesmo perfil do navegador.

## Arquivos locais

Os seguintes arquivos e diretórios não devem ser publicados:

- Bancos de dados com contatos.
- Históricos de tentativas de envio.
- Arquivos CSV com números de telefone.
- Perfis do navegador e dados de sessão.
- Credenciais e configurações privadas.
- Arquivos pessoais ou comerciais do cliente.

Esses dados devem permanecer protegidos pelo `.gitignore`. Arquivos já rastreados pelo Git precisam ser removidos do controle de versão separadamente.

## Limitações

- O projeto utiliza a interface do WhatsApp Web e não a API oficial.
- Mudanças na página podem exigir atualização dos seletores.
- A captura depende dos números que a interface disponibiliza.
- O formato numérico encontrado não comprova que o telefone é válido.
- A conexão e o carregamento da página podem causar falhas.
- O histórico de tentativas não é um comprovante de entrega.
- O intervalo entre mensagens não garante proteção contra restrições da plataforma.
- O envio de áudio não está implementado na versão aqui documentada.

## Aprendizados

O desenvolvimento envolveu automação de navegador, manipulação de elementos dinâmicos, expressões regulares, persistência em SQLite, exportação de dados e tratamento de falhas.

Também demonstrou a importância de registrar o estado das operações para evitar repetições quando uma automação é interrompida.

## Autor

**Caio Henrique Pereira da Silva**

Estudante de Engenharia de Software.