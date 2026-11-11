"""
Camada de acesso ao PostgreSQL: conexão, criação, carga e eliminação do banco.

As credenciais vêm do arquivo .env (veja .env.example). Todas as consultas
usam parâmetros (%s), nunca concatenação de texto.
"""
import os
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent          # pasta trabalho-final/
PASTA_SQL = RAIZ / "sql"
load_dotenv(RAIZ / ".env")

# Ordem de execução. "criar" monta o esquema; "carregar" popula com dados.
SCRIPTS_CRIAR = ["01_schema.sql", "02_pgvector.sql"]
SCRIPTS_CARGA = ["03_carga.sql", "04_embeddings.sql", "05_capas.sql"]   # os dois últimos são opcionais
SCRIPT_ELIMINAR = "99_drop.sql"

# Ordem das tabelas respeitando as dependências (pais antes dos filhos).
TABELAS = [
    "usuario", "desenvolvedora", "publicadora", "genero", "plataforma",
    "jogo", "jogo_genero", "jogo_plataforma", "pacote_conquistas", "conquista",
    "item_biblioteca", "desbloqueio", "recomendacao", "recomendacao_jogo",
]


def _parametros():
    host = os.environ.get("DB_HOST", "127.0.0.1")
    if host == "localhost":       # no Windows, "localhost" tenta IPv6 primeiro e cada conexão demora
        host = "127.0.0.1"
    return dict(
        host=host,
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "bd1"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        options="-c timezone=America/Sao_Paulo",
    )


def conectar(autocommit=False):
    """Abre uma conexão nova com o banco."""
    conn = psycopg2.connect(**_parametros())
    conn.autocommit = autocommit
    return conn


_pool = None


def _pegar():
    """Pega uma conexão do pool (conexões reaproveitadas são muito mais rápidas)."""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 8, **_parametros())
    conn = _pool.getconn()
    if conn.closed:                                   # caiu (ex.: container reiniciado)
        _pool.putconn(conn, close=True)
        conn = _pool.getconn()
    return conn


def _devolver(conn):
    try:
        conn.rollback()                               # nunca deixa transação aberta (evita travar o DROP)
    except Exception:
        pass
    _pool.putconn(conn, close=bool(conn.closed))


def fechar_pool():
    """Fecha as conexões do pool (usado antes de eliminar o banco)."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def transacao():
    """Executa um bloco em uma transação: confirma no fim, desfaz se der erro."""
    conn = _pegar()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _devolver(conn)


def consultar(sql, params=None):
    """Executa um SELECT e devolve um DataFrame do pandas."""
    conn = _pegar()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            colunas = [c.name for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=colunas)
    finally:
        _devolver(conn)


def executar(sql, params=None):
    """Executa INSERT/UPDATE/DELETE em transação própria. Devolve o nº de linhas afetadas."""
    with transacao() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def testar_conexao():
    """Devolve (ok, mensagem)."""
    try:
        conn = conectar()
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            versao = cur.fetchone()[0].split(",")[0]
        conn.close()
        return True, versao
    except Exception as erro:
        return False, str(erro).strip()


# ---------------------------------------------------------------------
# Criar / carregar / eliminar
# ---------------------------------------------------------------------
def _rodar_script(nome, opcional=False):
    caminho = PASTA_SQL / nome
    if not caminho.exists():
        if opcional:
            return False
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    texto = caminho.read_text(encoding="utf-8")
    conn = conectar(autocommit=True)       # os scripts controlam BEGIN/COMMIT por conta própria
    try:
        with conn.cursor() as cur:
            cur.execute(texto)             # sem parâmetros: '%' do script não é interpretado
    finally:
        conn.close()
    return True


def tabelas_existentes():
    """Nomes (da lista oficial) que existem hoje no esquema public."""
    df = consultar("SELECT table_name FROM information_schema.tables "
                   "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
    existentes = set(df["table_name"])
    return [t for t in TABELAS if t in existentes]


def criar_tabelas():
    """Cria as 14 tabelas, restrições, gatilhos e a extensão pgvector."""
    if tabelas_existentes():
        raise RuntimeError("Já existem tabelas no banco. Elimine-as antes de criar de novo.")
    for nome in SCRIPTS_CRIAR:
        _rodar_script(nome)
    return SCRIPTS_CRIAR


def carregar_dados():
    """Popula as tabelas (dados, embeddings e capas) respeitando as dependências."""
    if len(tabelas_existentes()) < len(TABELAS):
        raise RuntimeError("As tabelas ainda não foram criadas. Use 'Criar tabelas' primeiro.")
    if contagens().get("usuario", 0) > 0:
        raise RuntimeError("O banco já contém dados. Elimine e recrie para carregar de novo.")
    usados = []
    for nome in SCRIPTS_CARGA:
        if _rodar_script(nome, opcional=nome != SCRIPTS_CARGA[0]):
            usados.append(nome)
    return usados


def eliminar_tudo():
    """Remove tabelas, visão e funções (a extensão vector permanece)."""
    fechar_pool()
    _rodar_script(SCRIPT_ELIMINAR)


def migrar():
    """Bancos criados com um 02_pgvector.sql antigo: acrescenta colunas que o app usa."""
    if "jogo" in tabelas_existentes():
        executar("ALTER TABLE jogo ADD COLUMN IF NOT EXISTS url_capa TEXT")


def contagens():
    """{tabela: nº de linhas} para as tabelas existentes."""
    resultado = {}
    for t in tabelas_existentes():
        resultado[t] = int(consultar(f"SELECT count(*) AS n FROM {t}")["n"][0])   # nome vem da lista fixa
    return resultado
