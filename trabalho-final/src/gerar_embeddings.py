"""
Gera os embeddings (vetores) dos jogos com a API do Gemini e os salva em
sql/04_embeddings.sql, para que a carga inicial possa ser reproduzida a
partir de um banco vazio SEM chave de API e sem rede.

Uso (dentro da pasta trabalho-final/, com o banco já criado e carregado):
    python src/gerar_embeddings.py              # só gera sql/04_embeddings.sql
    python src/gerar_embeddings.py --aplicar    # gera o arquivo e atualiza o banco

Variáveis lidas do arquivo .env (veja .env.example):
    GEMINI_API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""
import argparse
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent          # pasta trabalho-final/
ARQUIVO_SAIDA = RAIZ / "sql" / "04_embeddings.sql"
MODELO = "gemini-embedding-001"
DIMENSAO = 768                                         # deve bater com vector(768)


def conectar():
    """Abre a conexão com o PostgreSQL usando as variáveis do .env."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "bd"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        options="-c timezone=America/Sao_Paulo",
    )


def montar_textos(conn):
    """Retorna [(id_jogo, titulo, texto)] com o texto que será vetorizado."""
    sql = """
        SELECT j.id_jogo, j.titulo, j.descricao, d.nome AS desenvolvedora,
               COALESCE(string_agg(g.nome, ', ' ORDER BY g.nome), '') AS generos
          FROM jogo j
          JOIN desenvolvedora d ON d.id_desenvolvedora = j.id_desenvolvedora
          LEFT JOIN jogo_genero jg ON jg.id_jogo = j.id_jogo
          LEFT JOIN genero g ON g.id_genero = jg.id_genero
         GROUP BY j.id_jogo, j.titulo, j.descricao, d.nome
         ORDER BY j.id_jogo
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        linhas = cur.fetchall()
    return [
        (i, titulo,
         f"{titulo}. Gêneros: {generos}. Desenvolvedora: {dev}. {descricao or ''}".strip())
        for i, titulo, descricao, dev, generos in linhas
    ]


def normalizar(v):
    """Deixa o vetor com comprimento 1 (embeddings reduzidos não vêm normalizados)."""
    norma = math.sqrt(sum(x * x for x in v))
    return [x / norma for x in v] if norma else v


def gerar_embeddings(textos, tentativas=4):
    """Chama a API do Gemini e devolve uma lista de vetores (um por texto)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.EmbedContentConfig(
        task_type="SEMANTIC_SIMILARITY", output_dimensionality=DIMENSAO)
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.models.embed_content(
                model=MODELO, contents=textos, config=config)
            vetores = [normalizar(list(e.values)) for e in resposta.embeddings]
            break
        except Exception as erro:                       # limite de uso, rede etc.
            if tentativa == tentativas:
                raise
            espera = 5 * tentativa
            print(f"  falha ({type(erro).__name__}); nova tentativa em {espera}s...")
            time.sleep(espera)
    if len(vetores) != len(textos) or any(len(v) != DIMENSAO for v in vetores):
        raise RuntimeError(f"Resposta inesperada: esperado {len(textos)} vetores de {DIMENSAO} dimensões.")
    return vetores


def escrever_sql(jogos, vetores, caminho=ARQUIVO_SAIDA):
    """Grava o arquivo 04_embeddings.sql com um UPDATE por jogo."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("-- =====================================================================\n")
        f.write(f"-- Embeddings dos jogos (modelo {MODELO}, {DIMENSAO} dimensões)\n")
        f.write(f"-- Gerado por src/gerar_embeddings.py em {datetime.now():%d/%m/%Y %H:%M}.\n")
        f.write("-- Executar APÓS 01_schema.sql, 02_pgvector.sql e 03_carga.sql.\n")
        f.write("-- Não editar à mão: gere novamente com o script se a descrição de um jogo mudar.\n")
        f.write("-- =====================================================================\n")
        f.write("BEGIN;\n\n")
        for (id_jogo, titulo, _), v in zip(jogos, vetores):
            literal = "[" + ",".join(f"{x:.7g}" for x in v) + "]"
            f.write(f"-- {titulo}\n")
            f.write(f"UPDATE jogo SET embedding = '{literal}' WHERE id_jogo = {id_jogo};\n\n")
        f.write("COMMIT;\n")
    return caminho


def aplicar(conn, jogos, vetores):
    """Atualiza a coluna jogo.embedding diretamente no banco."""
    with conn.cursor() as cur:
        for (id_jogo, _, _), v in zip(jogos, vetores):
            cur.execute("UPDATE jogo SET embedding = %s::vector WHERE id_jogo = %s",
                        ("[" + ",".join(f"{x:.7g}" for x in v) + "]", id_jogo))
    conn.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera os embeddings dos jogos.")
    parser.add_argument("--aplicar", action="store_true",
                        help="além de gerar o arquivo, atualiza a coluna embedding no banco")
    args = parser.parse_args(argv)

    load_dotenv(RAIZ / ".env")
    for var in ("GEMINI_API_KEY", "DB_PASSWORD"):
        if not os.environ.get(var):
            sys.exit(f"Variável {var} não encontrada. Confira o arquivo .env (veja .env.example).")

    conn = conectar()
    try:
        jogos = montar_textos(conn)
        if not jogos:
            sys.exit("Nenhum jogo no banco. Execute 01_schema.sql, 02_pgvector.sql e 03_carga.sql antes.")
        print(f"{len(jogos)} jogos encontrados. Gerando embeddings ({MODELO}, {DIMENSAO} dimensões)...")
        vetores = gerar_embeddings([t for _, _, t in jogos])
        caminho = escrever_sql(jogos, vetores)
        print(f"Arquivo gerado: {caminho}")
        if args.aplicar:
            aplicar(conn, jogos, vetores)
            print("Banco atualizado.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
