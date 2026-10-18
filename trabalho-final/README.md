# Plataforma de Acompanhamento de Conquistas de Jogos (Xbox)

Trabalho final da disciplina **DEC7129 – Banco de Dados I** (UFSC, Campus Araranguá, 2026.2)
Professor: Alexandre Leopoldo Gonçalves

## Sobre o projeto
O projeto consiste no desenvolvimento de um banco de dados relacional e de uma aplicação para acompanhamento de jogos eletrônicos e conquistas no ecossistema Xbox, inspirado em plataformas como o TrueAchievements.

O sistema permitirá organizar bibliotecas pessoais de jogos, registrar conquistas desbloqueadas e acompanhar o progresso individual dos jogadores, incluindo pontuação acumulada (*Gamerscore*), tempo de jogo e estatísticas de desempenho.

Também está prevista a utilização de **Inteligência Artificial Generativa** para recomendar jogos com base no histórico e nas preferências dos usuários.

## Funcionalidades previstas
- **Catálogo de jogos:** gerenciamento de jogos, plataformas Xbox, gêneros, desenvolvedoras e publicadoras.
- **Pacotes de conquistas:** organização de conquistas por jogo e plataforma, distinguindo conteúdo base, DLCs e atualizações.
- **Biblioteca pessoal:** acompanhamento dos jogos associados a cada usuário, incluindo status e horas jogadas.
- **Histórico de desbloqueios:** registro das conquistas obtidas, com data e horário.
- **Progresso e Gamerscore:** cálculo de percentual de conclusão e pontuação acumulada.
- **Estatísticas e rankings:** consultas agregadas e visualizações gráficas para análise de desempenho.
- **Recomendação por IA:** sugestões de jogos baseadas no histórico do usuário.

> **Nota:** O sistema utilizará dados demonstrativos e não dependerá de integração com a API do Xbox Live.

## Integrantes
- Manuel Etiene da Silva João (24250046)
- Mateus Mendes Sodré (22215911)
- Zeferino José Paulo Fulano (24250049)

## Status
| Etapa | Situação |
|---|---|
| Definição do tema e escopo | ✅ Concluído |
| Objetivo geral e levantamento de requisitos | ✅ Entrega preliminar concluída |
| Modelagem conceitual (DER) | ✅ Entrega preliminar concluída |
| Modelagem lógica | ⏳ Pendente |
| Script DDL e implementação do banco | ⏳ Pendente |
| Carga inicial de dados | ⏳ Pendente |
| Consultas SQL e gráficos estatísticos | ⏳ Pendente |
| Aplicação em linha de comando (CLI) | ⏳ Pendente |
| Integração com IA generativa | ⏳ Pendente |
| Testes e apresentação final | ⏳ Pendente |

## Documentação
- [Relatório da entrega preliminar](docs/Entrega_Preliminar_DEC7129.pdf)
- [Diagrama ER](docs/modelo-conceitual/DER.png)

A entrega preliminar, contendo o objetivo geral, a descrição detalhada dos requisitos e o modelo conceitual, foi realizada em **17 de outubro de 2026**.

## Tecnologias previstas
- **PostgreSQL 18:** sistema gerenciador de banco de dados relacional.
- **Python:** desenvolvimento da aplicação em linha de comando.
- **Docker:** configuração e execução do ambiente de banco de dados.
- **pgAdmin 4:** administração e consulta ao PostgreSQL.
- **brModelo:** elaboração dos modelos conceitual e lógico.
- **API de LLM (a definir):** funcionalidade de recomendação de jogos com IA generativa.

## Escopo e limitações
O projeto tem finalidade acadêmica e prioriza a aplicação dos conceitos de modelagem conceitual, modelagem lógica, SQL, integridade referencial e manipulação de dados relacionais.

A aplicação será executada em linha de comando, utilizando dados predefinidos e registros fictícios de usuários e desbloqueios.

Não estão previstas autenticação por senha, interface gráfica ou integração automática com serviços externos de jogos.

## Entrega final
**22 de novembro de 2026**, conforme o enunciado da disciplina.

---

Projeto acadêmico desenvolvido na **Universidade Federal de Santa Catarina — Campus Araranguá**.