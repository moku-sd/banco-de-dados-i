# Banco de Dados I

Repositório destinado às atividades, exercícios e ao trabalho prático da disciplina **DEC7129 — Banco de Dados I**, do curso de Engenharia de Computação da Universidade Federal de Santa Catarina (UFSC).

## Estrutura

- `modelagem/` - exercícios e arquivos de modelagem conceitual e lógica;
- `sql/` - scripts SQL desenvolvidos durante a disciplina;
- `dumps/` - dumps locais dos bancos de dados;
- `trabalho-final/` - arquivos relacionados ao trabalho prático da disciplina.

## Ambiente

O ambiente de banco de dados é executado com Docker Compose e utiliza:

- PostgreSQL 18;
- pgAdmin 4;
- volumes Docker para persistência dos dados.

O PostgreSQL fica disponível localmente na porta `5432` e o pgAdmin pode ser acessado pelo navegador na porta `5050`.

### Iniciar o ambiente

```bash
docker compose up -d
```

### Verificar os serviços

```bash
docker compose ps
```

### Encerrar o ambiente

```bash
docker compose down
```

Os dados do PostgreSQL e as configurações do pgAdmin são mantidos em volumes Docker.

## Credenciais locais

As credenciais abaixo são utilizadas exclusivamente no ambiente local de desenvolvimento criado pelo Docker Compose.

### PostgreSQL

- **Host (Windows):** `localhost`
- **Host (Docker):** `postgres`
- **Porta:** `5432`
- **Banco:** `bd1`
- **Usuário:** `postgres`
- **Senha:** `postgres`

### pgAdmin

- **URL:** `http://localhost:5050`
- **E-mail:** `admin@mateus.com`
- **Senha:** `admin`

> [!WARNING]
> Estas credenciais são destinadas exclusivamente ao ambiente local da disciplina e não devem ser reutilizadas em ambientes de produção ou serviços externos.