# Plataforma de Acompanhamento de Conquistas de Jogos (Xbox)

Trabalho final da disciplina **DEC7129 – Banco de Dados I** (UFSC, Campus Araranguá, 2026.2)
Professor: Alexandre Leopoldo Gonçalves

## Sobre o projeto
Banco de dados relacional e aplicação web para acompanhamento de jogos e conquistas no ecossistema Xbox, inspirados em plataformas como o TrueAchievements.

O sistema organiza a biblioteca pessoal de cada usuário, registra as conquistas desbloqueadas e mostra o progresso individual, com pontuação acumulada (*Gamerscore*), tempo de jogo, rankings e gráficos. Uma funcionalidade de **IA generativa** recomenda jogos a partir do histórico do usuário, combinando busca por similaridade (**pgvector**) com um modelo de linguagem (**Gemini**).

> **Nota:** o sistema usa dados demonstrativos e não depende da API do Xbox Live.

## Funcionalidades
- **Biblioteca:** cartões com capa, status, horas jogadas, barra de progresso (conquistas desbloqueadas sobre o total) e Gamerscore; registro de desbloqueios.
- **Cadastros:** inserir, consultar, alterar e excluir em todas as 14 tabelas, com listas suspensas nas chaves estrangeiras e mensagens de erro que citam a regra de negócio violada.
- **Consultas:** três consultas agregadas (ranking de Gamerscore, conquistas por trimestre e jogos concluídos por ano), cada uma com SQL, tabela e gráfico exportável em PNG.
- **Recomendação por IA:** perfil do usuário por embeddings, candidatos por distância de cosseno no pgvector e justificativas geradas pelo Gemini, gravadas no banco.
- **Banco de dados:** criar as tabelas, carregar os dados e eliminar tudo a partir de um banco vazio.

## Como executar
Pré-requisitos: **Docker Desktop** e **Python 3.10 ou superior**.

**1. Subir o PostgreSQL e o pgAdmin.** O `compose.yaml` fica na **raiz do repositório** (fora de `trabalho-final/`), pois o mesmo banco serve às demais atividades da disciplina:
```bash
docker compose up -d
```
A imagem é a `pgvector/pgvector:pg18`, que já inclui a extensão pgvector. Os próximos passos são executados dentro da pasta `trabalho-final/`:
```bash
cd trabalho-final
```

**2. Instalar as dependências do Python:**
```bash
python -m pip install -r requirements.txt
```

**3. Criar o arquivo `.env`** a partir do modelo e preencher a chave do Gemini:
```bash
cp .env.example .env            # no PowerShell: Copy-Item .env.example .env
```
A chave é gratuita em <https://aistudio.google.com/apikey>. Sem ela, tudo funciona, exceto a recomendação por IA e a geração de novos embeddings.

**4. Abrir a aplicação:**
```bash
python -m streamlit run src/app.py
```
O navegador abre em <http://localhost:8501>. Na primeira execução o Streamlit pode pedir um e-mail: basta deixar em branco.

**5. Montar o banco:** na página **Banco de dados**, clique em *Criar tabelas* e depois em *Carregar dados*. O botão *Recriar tudo* elimina, cria e carrega de novo, e *Eliminar tudo* remove todas as tabelas.

### Acessos do ambiente Docker
| Serviço | Endereço | Credenciais |
|---|---|---|
| PostgreSQL | `localhost:5432`, banco `bd1` | usuário `postgres`, senha `postgres` |
| pgAdmin | <http://localhost:5050> | `admin@mateus.com` / `admin` |

No pgAdmin, o servidor se conecta pelo nome `postgres` (rede interna do Docker). Todos são valores de desenvolvimento local, sem dados sensíveis.

## Estrutura do repositório
```
compose.yaml                PostgreSQL (pgvector) e pgAdmin, na raiz do repositório
trabalho-final/
├── README.md
├── requirements.txt
├── .env.example            modelo das variáveis de ambiente (o .env real não é versionado)
├── .streamlit/config.toml  tema da interface
├── docs/                   relatórios e diagramas (conceitual e lógico)
├── sql/
│   ├── 01_schema.sql       14 tabelas, restrições, índices, gatilhos e visão de auditoria
│   ├── 02_pgvector.sql     extensão pgvector e colunas embedding e url_capa
│   ├── 03_carga.sql        dados fictícios de demonstração
│   ├── 04_embeddings.sql   vetores dos jogos (gerado por gerar_embeddings.py)
│   ├── 05_capas.sql        endereços das capas (gerado por capas.py, opcional)
│   └── 99_drop.sql         elimina tabelas, visão e funções
└── src/
    ├── app.py              menu principal (Streamlit)
    ├── paginas.py          páginas: Biblioteca, Consultas, Recomendação IA, Cadastros, Banco de dados
    ├── db.py               conexão, pool, criar/carregar/eliminar
    ├── esquema.py          descrição das 14 tabelas (gera os formulários)
    ├── crud.py             inserir/alterar/excluir genéricos e tradução dos erros do PostgreSQL
    ├── consultas.py        as 3 consultas e os gráficos
    ├── ia.py               recomendação (pgvector + Gemini)
    ├── gerar_embeddings.py geração dos embeddings e do 04_embeddings.sql
    ├── capas.py            busca das capas e geração do 05_capas.sql
    └── ui.py               estilo e elementos visuais
```

## Recomendação por IA
1. Cada jogo vira um texto (título, gêneros, desenvolvedora e descrição), convertido em um vetor de 768 dimensões pelo modelo `gemini-embedding-001` e guardado em `jogo.embedding`.
2. O perfil do usuário é a média dos vetores dos jogos que ele finalizou ou está jogando. O pgvector devolve os jogos mais próximos (distância de cosseno) que ele ainda não tem.
3. O Gemini recebe o histórico e **somente** esses candidatos, escolhe os melhores e justifica em português.
4. A resposta é validada (só jogos candidatos, sem repetição) e gravada em `recomendacao` e `recomendacao_jogo` em uma única transação.

O modelo de texto é configurável pela variável `GEMINI_MODEL` do `.env`.

## Tecnologias
- **PostgreSQL 18 + pgvector:** banco relacional e busca por similaridade.
- **Python:** psycopg2 (acesso ao banco), pandas e matplotlib (consultas e gráficos).
- **Streamlit:** interface web.
- **Google Gemini API:** embeddings e geração de texto.
- **Docker e pgAdmin 4:** ambiente e administração do banco.
- **brModelo:** modelos conceitual e lógico.

## Integrantes
- Manuel Etiene da Silva João (24250046)
- Mateus Mendes Sodré (22215911)
- Zeferino José Paulo Fulano (24250049)

## Status
| Etapa | Situação |
|---|---|
| Definição do tema e escopo | ✅ Concluído |
| Objetivo geral e requisitos | ✅ Entrega preliminar concluída (17/10/2026) |
| Modelagem conceitual e lógica | ✅ Concluído |
| Script DDL, restrições e gatilhos | ✅ Concluído |
| Carga inicial de dados | ✅ Concluído |
| Consultas SQL e gráficos | ✅ Concluído |
| Aplicação web | ✅ Concluído |
| Integração com IA generativa | ✅ Concluído |
| Relatório final e apresentação | ⏳ Em andamento |

## Documentação
- [Relatório da entrega preliminar](docs/Entrega_Preliminar_DEC7129.pdf)
- [Diagrama ER (modelo conceitual)](docs/modelo-conceitual/DER.png)
- [Modelo lógico](docs/modelo-logico/LOGICO.png)
- [Relatório final](docs/Relatorio_Trabalho_Final.pdf)

## Escopo e limitações
O projeto tem finalidade acadêmica e prioriza modelagem conceitual e lógica, SQL, integridade referencial e manipulação de dados relacionais. Os usuários, jogos e desbloqueios são fictícios. Não estão previstas autenticação por senha nem integração automática com serviços externos de jogos. As capas são buscadas na loja do Xbox (ou na Steam, como reserva) apenas para ilustrar a interface; quando não há correspondência, a interface mostra um cartão com as iniciais do jogo.

## Entrega final
**22 de novembro de 2026**, conforme o enunciado da disciplina.

---

Projeto acadêmico desenvolvido na **Universidade Federal de Santa Catarina — Campus Araranguá**.
