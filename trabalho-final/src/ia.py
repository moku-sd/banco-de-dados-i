"""
Recomendação de jogos com IA generativa (item 7f), em duas etapas (padrão RAG):

 1. RECUPERAÇÃO (pgvector): o perfil do usuário é a média dos embeddings dos jogos que
    ele finalizou/está jogando; o banco devolve, por distância de cosseno, os jogos mais
    parecidos que ele ainda NÃO tem na biblioteca (os "candidatos").
 2. GERAÇÃO (Gemini): o LLM recebe o histórico do usuário e SÓ os candidatos, escolhe os
    melhores e escreve a justificativa em português. O resultado é gravado em
    recomendacao e recomendacao_jogo.
"""
import json
import os
import re
import time

import db
import gerar_embeddings as ge

MODELO_TEXTO = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")


class ErroIA(Exception):
    """Falha esperada (sem chave, sem embeddings, API fora do ar) com mensagem para o usuário."""


# ---------------------------------------------------------------------
# Embeddings de jogos novos ou alterados
# ---------------------------------------------------------------------
def jogos_sem_embedding():
    return db.consultar("SELECT id_jogo, titulo FROM jogo WHERE embedding IS NULL ORDER BY id_jogo")


def atualizar_embeddings(ids=None):
    """Gera e grava o embedding dos jogos indicados (ou de todos os que não têm). Devolve a quantidade."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ErroIA("GEMINI_API_KEY não configurada no arquivo .env.")
    conn = ge.conectar()
    try:
        jogos = ge.montar_textos(conn)
        if ids is None:
            ids = set(jogos_sem_embedding()["id_jogo"].astype(int))
        jogos = [j for j in jogos if j[0] in set(ids)]
        if not jogos:
            return 0
        try:
            vetores = ge.gerar_embeddings([t for _, _, t in jogos])
        except Exception as erro:
            raise ErroIA(f"Não consegui gerar os embeddings ({type(erro).__name__}): {erro}") from erro
        ge.aplicar(conn, jogos, vetores)
        return len(jogos)
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Etapa 1: recuperação por similaridade
# ---------------------------------------------------------------------
SQL_CANDIDATOS = """
WITH perfil AS (
    SELECT avg(j.embedding) AS v
      FROM item_biblioteca ib
      JOIN jogo_plataforma jp ON jp.id_jogo_plataforma = ib.id_jogo_plataforma
      JOIN jogo j             ON j.id_jogo = jp.id_jogo
     WHERE ib.id_usuario = %(u)s AND ib.status = ANY(%(status)s) AND j.embedding IS NOT NULL
)
SELECT j.id_jogo, j.titulo, j.descricao, j.url_capa,
       1 - (j.embedding <=> p.v) AS similaridade,
       (SELECT string_agg(g.nome, ', ' ORDER BY g.nome)
          FROM jogo_genero jg JOIN genero g ON g.id_genero = jg.id_genero
         WHERE jg.id_jogo = j.id_jogo) AS generos
  FROM jogo j, perfil p
 WHERE p.v IS NOT NULL AND j.embedding IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM item_biblioteca ib
                     JOIN jogo_plataforma jp ON jp.id_jogo_plataforma = ib.id_jogo_plataforma
                    WHERE ib.id_usuario = %(u)s AND jp.id_jogo = j.id_jogo)
 ORDER BY j.embedding <=> p.v
 LIMIT %(n)s
"""


def candidatos(id_usuario, n=8):
    """Jogos mais parecidos com o gosto do usuário que ele ainda não tem."""
    for status in (["FINALIZADO", "JOGANDO"], ["FINALIZADO", "JOGANDO", "PAUSADO", "ABANDONADO", "QUERO_JOGAR"]):
        df = db.consultar(SQL_CANDIDATOS, {"u": id_usuario, "status": status, "n": n})
        if not df.empty:
            return df
    return df


def historico_usuario(id_usuario):
    return db.consultar("""
        SELECT j.titulo, p.nome AS plataforma, ib.status, ib.horas_jogadas,
               (SELECT string_agg(g.nome, ', ' ORDER BY g.nome)
                  FROM jogo_genero jg JOIN genero g ON g.id_genero = jg.id_genero
                 WHERE jg.id_jogo = j.id_jogo) AS generos
          FROM item_biblioteca ib
          JOIN jogo_plataforma jp ON jp.id_jogo_plataforma = ib.id_jogo_plataforma
          JOIN jogo j             ON j.id_jogo = jp.id_jogo
          JOIN plataforma p       ON p.id_plataforma = jp.id_plataforma
         WHERE ib.id_usuario = %s
         ORDER BY ib.horas_jogadas DESC""", (id_usuario,))


# ---------------------------------------------------------------------
# Etapa 2: geração com o Gemini
# ---------------------------------------------------------------------
def montar_prompt(gamertag, historico, cands, quantidade):
    linhas_hist = [
        f"- {r.titulo} ({r.plataforma}) | status: {r.status} | {float(r.horas_jogadas):g} h | gêneros: {r.generos or '-'}"
        for r in historico.itertuples()]
    linhas_cand = [
        f"- id_jogo={r.id_jogo} | {r.titulo} | gêneros: {r.generos or '-'} | similaridade: {r.similaridade:.2f} | {r.descricao or ''}"
        for r in cands.itertuples()]
    return (
        "Você é um consultor de jogos de Xbox em um sistema de acompanhamento de conquistas.\n"
        f"Escolha exatamente {quantidade} jogos para recomendar ao jogador {gamertag}, usando SOMENTE "
        "os candidatos listados abaixo (não invente jogos nem ids). Ordene do mais ao menos indicado.\n"
        "Para cada um escreva uma justificativa curta (1 a 2 frases, em português do Brasil) que cite "
        "jogos que o jogador já tem e o que há em comum (gênero, estilo, ritmo, horas dedicadas).\n\n"
        f"HISTÓRICO DO JOGADOR:\n" + "\n".join(linhas_hist) + "\n\n"
        "CANDIDATOS (ordenados por similaridade com o gosto do jogador):\n" + "\n".join(linhas_cand) + "\n\n"
        'Responda apenas com JSON no formato {"recomendacoes":[{"id_jogo":<int>,"justificativa":"<texto>"}]}.')


MODELOS_RESERVA = ["gemini-2.5-flash", "gemini-flash-lite-latest"]


def _chamar_gemini(prompt, tentativas=3):
    """Devolve (texto_json, nome_do_modelo). Os apelidos '-latest' só existem na API v1beta,
    por isso ela é pedida explicitamente. Se o modelo não existir (404), tenta o próximo."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                          http_options=types.HttpOptions(api_version="v1beta"))
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4)
    modelos = list(dict.fromkeys([MODELO_TEXTO] + MODELOS_RESERVA))
    ultimo = None
    for modelo in modelos:
        for tentativa in range(1, tentativas + 1):
            try:
                resp = client.models.generate_content(model=modelo, contents=prompt, config=config)
                return resp.text, (getattr(resp, "model_version", None) or modelo)
            except Exception as erro:
                ultimo = erro
                codigo = getattr(erro, "code", None)
                if codigo == 404:
                    break                                   # modelo inexistente: vai para o próximo
                definitivo = isinstance(codigo, int) and 400 <= codigo < 500 and codigo != 429
                if definitivo or tentativa == tentativas:
                    raise ErroIA(_texto_erro(erro)) from erro
                time.sleep(4 * tentativa)
    disponiveis = ""
    try:
        nomes = [m.name.replace("models/", "") for m in client.models.list()
                 if "generateContent" in (getattr(m, "supported_actions", None) or [])]
        disponiveis = " Modelos disponíveis para sua chave: " + ", ".join(nomes[:12]) + "."
    except Exception:
        pass
    raise ErroIA(_texto_erro(ultimo) + disponiveis) from ultimo


def _texto_erro(erro):
    codigo = getattr(erro, "code", None)
    detalhe = str(getattr(erro, "message", "") or erro)[:400]
    dica = {404: " (modelo não encontrado: ajuste GEMINI_MODEL no .env)",
            429: " (limite de uso atingido: aguarde um minuto e tente de novo)",
            400: " (requisição recusada pela API)",
            403: " (chave sem permissão: confira GEMINI_API_KEY)"}.get(codigo, "")
    return f"Gemini [{type(erro).__name__} {codigo or ''}]{dica}: {detalhe}"


def _ler_json(texto):
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    try:
        return json.loads(texto)["recomendacoes"]
    except Exception as erro:
        raise ErroIA("A resposta do Gemini veio em formato inesperado. Tente gerar de novo.") from erro


def recomendar(id_usuario, quantidade=3, n_candidatos=8):
    """Executa as duas etapas e grava o resultado. Devolve um dicionário com tudo que foi usado."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ErroIA("GEMINI_API_KEY não configurada no arquivo .env.")
    cands = candidatos(id_usuario, n_candidatos)
    if cands.empty:
        raise ErroIA("Não há candidatos: o usuário não tem jogos finalizados/em andamento com embedding, "
                     "ou já possui todos os jogos. Gere os embeddings na página Banco de dados.")
    quantidade = min(quantidade, len(cands))
    historico = historico_usuario(id_usuario)
    gamertag = db.consultar("SELECT gamertag FROM usuario WHERE id_usuario = %s", (id_usuario,))["gamertag"][0]
    prompt = montar_prompt(gamertag, historico, cands, quantidade)
    texto, modelo = _chamar_gemini(prompt)
    itens = _ler_json(texto)

    # valida: ids precisam estar entre os candidatos, sem repetição
    validos = set(cands["id_jogo"].astype(int))
    escolhidos, vistos = [], set()
    for it in itens:
        try:
            idj = int(it["id_jogo"])
            just = str(it["justificativa"]).strip()
        except Exception:
            continue
        if idj in validos and idj not in vistos and just:
            vistos.add(idj)
            escolhidos.append((idj, just))
    escolhidos = escolhidos[:quantidade]
    if not escolhidos:
        raise ErroIA("O Gemini não devolveu nenhum jogo válido entre os candidatos. Tente gerar de novo.")

    with db.transacao() as cur:                                     # tudo ou nada (RN23: ≥ 1 jogo)
        cur.execute("INSERT INTO recomendacao (id_usuario, modelo_ia) VALUES (%s, %s) RETURNING id_recomendacao",
                    (id_usuario, modelo[:80]))
        id_rec = cur.fetchone()[0]
        for pos, (idj, just) in enumerate(escolhidos, start=1):
            cur.execute("INSERT INTO recomendacao_jogo (id_recomendacao, id_jogo, posicao, justificativa) "
                        "VALUES (%s, %s, %s, %s)", (id_rec, idj, pos, just))
    return dict(id_recomendacao=id_rec, modelo=modelo, candidatos=cands, historico=historico, prompt=prompt)


def ler_recomendacao(id_recomendacao):
    return db.consultar("""
        SELECT rj.posicao, j.id_jogo, j.titulo, j.url_capa, rj.justificativa,
               (SELECT string_agg(g.nome, ', ' ORDER BY g.nome)
                  FROM jogo_genero jg JOIN genero g ON g.id_genero = jg.id_genero
                 WHERE jg.id_jogo = j.id_jogo) AS generos
          FROM recomendacao_jogo rj JOIN jogo j ON j.id_jogo = rj.id_jogo
         WHERE rj.id_recomendacao = %s ORDER BY rj.posicao""", (id_recomendacao,))


def historico_recomendacoes(id_usuario):
    return db.consultar("""
        SELECT id_recomendacao, data_geracao, modelo_ia FROM recomendacao
         WHERE id_usuario = %s ORDER BY data_geracao DESC, id_recomendacao DESC""", (id_usuario,))
