"""
Capas dos jogos. Busca a imagem na loja do Xbox (Microsoft Store, sem chave de API)
e, se não achar, na Steam; guarda o endereço em jogo.url_capa.

Uso (dentro da pasta trabalho-final/):
    python src/capas.py              # busca as capas que faltam e grava sql/05_capas.sql
    python src/capas.py --aplicar    # além disso, atualiza o banco

Se nenhuma fonte responder, a interface mostra um cartão colorido com as iniciais
do jogo, então a ausência de capa nunca quebra a tela.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

import db

CLIENT_ID = "7F27B536-CF6B-4C65-8638-A0F8CBDFCA65"
ARQUIVO_SAIDA = db.PASTA_SQL / "05_capas.sql"
ROXOS = ["#107C10", "#0E6B5C", "#1F4E79", "#5B2A86", "#8A3B12", "#7A1F3D", "#2F4858", "#3B5D0A"]


def _get_json(url, tempo=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto-bd1-ufsc)"})
    with urllib.request.urlopen(req, timeout=tempo) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _norm(txt):
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", txt).strip()


def _https(url):
    return "https:" + url if url and url.startswith("//") else url


def _combina(titulo, candidato):
    """Título igual, ou candidato = título + sufixo (ex.: 'Forza Horizon 5 Edição Padrão')."""
    a, b = _norm(titulo), _norm(candidato)
    if not a or not b:
        return False
    return a == b or (b.startswith(a + " ") and len(a) / len(b) >= 0.5)


# ---------------------------------------------------------------------
# Fonte 1: Xbox / Microsoft Store
# ---------------------------------------------------------------------
def _xbox(titulo):
    """Devolve (url, titulo_encontrado) ou None. Só aceita se o título do PRODUTO conferir."""
    q = urllib.parse.urlencode({
        "market": "pt-br", "clientId": CLIENT_ID,
        "sources": "Microsoft-Terms,Iris-Products,DCatAll-Products",
        "filter": "+ClientType:StoreWeb", "counts": "5,1,5", "query": titulo})
    dados = _get_json("https://www.microsoft.com/msstoreapiprod/api/autosuggest?" + q)
    for conjunto in dados.get("ResultSets", []):
        for s in conjunto.get("Suggests", []):
            big_id = next((m["Value"] for m in s.get("Metas", []) if m.get("Key") == "BigCatalogId"), None)
            if not big_id:
                continue
            achado = _xbox_produto(big_id)
            if achado and _combina(titulo, achado[1]):
                return achado
    return None


def _xbox_produto(big_id):
    """Consulta o catálogo: devolve (url_do_poster, titulo_do_produto) ou None."""
    url = ("https://displaycatalog.mp.microsoft.com/v7.0/products?"
           + urllib.parse.urlencode({"bigIds": big_id, "market": "BR", "languages": "pt-BR"}))
    produtos = _get_json(url).get("Products") or []
    if not produtos:
        return None
    props = (produtos[0].get("LocalizedProperties") or [{}])[0]
    for finalidade in ("Poster", "BoxArt", "Tile"):
        for img in props.get("Images") or []:
            if img.get("ImagePurpose") == finalidade and img.get("Uri"):
                return _https(img["Uri"]), props.get("ProductTitle", "")
    return None


# ---------------------------------------------------------------------
# Fonte 2: Steam (reserva)
# ---------------------------------------------------------------------
def _steam(titulo):
    q = urllib.parse.urlencode({"term": titulo, "l": "portuguese", "cc": "br"})
    dados = _get_json("https://store.steampowered.com/api/storesearch/?" + q)
    for item in dados.get("items", []):
        if _combina(titulo, item.get("name", "")):
            return (f"https://cdn.cloudflare.steamstatic.com/steam/apps/{item['id']}/library_600x900.jpg",
                    item["name"])
    return None


def buscar_capa_detalhada(titulo):
    """Tenta Xbox e depois Steam. Devolve (url, fonte, titulo_encontrado) ou None."""
    for nome, fonte in (("Xbox", _xbox), ("Steam", _steam)):
        try:
            r = fonte(titulo)
            if r:
                return r[0], nome, r[1]
        except Exception:
            continue
    return None


def buscar_capa(titulo):
    r = buscar_capa_detalhada(titulo)
    return r[0] if r else None


# ---------------------------------------------------------------------
# Gravação
# ---------------------------------------------------------------------
def _sql_str(txt):
    return "'" + txt.replace("'", "''") + "'"


def atualizar_capas(somente_faltantes=True, progresso=None):
    """Busca as capas e grava no banco. Devolve (encontradas, total, [dict por jogo])."""
    if not somente_faltantes:
        db.executar("UPDATE jogo SET url_capa = NULL")
    filtro = "WHERE url_capa IS NULL" if somente_faltantes else ""
    jogos = db.consultar(f"SELECT id_jogo, titulo FROM jogo {filtro} ORDER BY id_jogo")
    achadas = []
    for i, (id_jogo, titulo) in enumerate(zip(jogos["id_jogo"], jogos["titulo"])):
        r = buscar_capa_detalhada(titulo)
        if r:
            db.executar("UPDATE jogo SET url_capa = %s WHERE id_jogo = %s", (r[0], int(id_jogo)))
            achadas.append({"Jogo": titulo, "Fonte": r[1], "Título encontrado": r[2]})
        if progresso:
            progresso((i + 1) / len(jogos), titulo)
    return len(achadas), len(jogos), achadas


def escrever_sql():
    """Grava sql/05_capas.sql a partir do que está no banco (para reproduzir a carga sem rede)."""
    df = db.consultar("SELECT id_jogo, titulo, url_capa FROM jogo WHERE url_capa IS NOT NULL ORDER BY id_jogo")
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write("-- =====================================================================\n")
        f.write("-- Capas dos jogos (jogo.url_capa)\n")
        f.write(f"-- Gerado por src/capas.py em {datetime.now():%d/%m/%Y %H:%M}.\n")
        f.write("-- Executar APÓS 01_schema.sql, 02_pgvector.sql e 03_carga.sql.\n")
        f.write("-- =====================================================================\nBEGIN;\n\n")
        for id_jogo, titulo, url in zip(df["id_jogo"], df["titulo"], df["url_capa"]):
            f.write(f"-- {titulo}\nUPDATE jogo SET url_capa = {_sql_str(url)} WHERE id_jogo = {int(id_jogo)};\n\n")
        f.write("COMMIT;\n")
    return ARQUIVO_SAIDA, len(df)


# ---------------------------------------------------------------------
# Cartão reserva (sem imagem)
# ---------------------------------------------------------------------
def cartao_reserva(titulo, largura="100%", proporcao="2 / 3"):
    """HTML de um cartão colorido com as iniciais, usado quando não há capa."""
    cor = ROXOS[int(hashlib.md5(titulo.encode()).hexdigest(), 16) % len(ROXOS)]
    palavras = [p for p in re.split(r"\W+", titulo) if p]
    iniciais = "".join(p[0] for p in palavras[:2]).upper() or "?"
    return (f'<div style="width:{largura};aspect-ratio:{proporcao};border-radius:10px;'
            f'background:linear-gradient(145deg,{cor},#0b0f0b);display:flex;align-items:center;'
            f'justify-content:center;color:#fff;font-weight:800;font-size:2.2rem;'
            f'letter-spacing:.05em;box-shadow:0 2px 8px rgba(0,0,0,.25)" '
            f'title="{html.escape(titulo)}">{html.escape(iniciais)}</div>')


def main(argv=None):
    p = argparse.ArgumentParser(description="Busca as capas dos jogos.")
    p.add_argument("--aplicar", action="store_true", help="atualiza o banco além de gerar o arquivo")
    p.add_argument("--todas", action="store_true", help="refaz também as capas que já existem")
    args = p.parse_args(argv)
    if args.aplicar:
        achadas, total, lista = atualizar_capas(
            somente_faltantes=not args.todas, progresso=lambda f, t: None)
        for a in lista:
            print(f"  {a['Jogo']}  ->  {a['Fonte']}: {a['Título encontrado']}")
        print(f"{achadas} de {total} capas encontradas.")
        caminho, n = escrever_sql()
        print(f"Arquivo gerado: {caminho} ({n} capas)")
    else:
        jogos = db.consultar("SELECT id_jogo, titulo FROM jogo ORDER BY id_jogo")
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            f.write("BEGIN;\n")
            n = 0
            for id_jogo, titulo in zip(jogos["id_jogo"], jogos["titulo"]):
                url = buscar_capa(titulo)
                print(f"  {titulo}: {'ok' if url else 'não achei'}")
                if url:
                    n += 1
                    f.write(f"UPDATE jogo SET url_capa = {_sql_str(url)} WHERE id_jogo = {int(id_jogo)};\n")
            f.write("COMMIT;\n")
        print(f"{n} capas gravadas em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    sys.exit(main())
