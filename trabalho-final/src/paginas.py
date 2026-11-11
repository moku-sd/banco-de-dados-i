"""Páginas da interface (Streamlit). Cada função é uma entrada do menu lateral."""
import math
from datetime import date, datetime

import pandas as pd
import streamlit as st

import capas
import consultas
import crud
import db
import ia
import ui
from esquema import STATUS, TABELAS


def _py(v):
    """Converte valores do pandas/numpy para tipos nativos do Python (None se vazio)."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if hasattr(v, "item"):
        return v.item()
    return v


# =====================================================================
# Banco de dados  (item 7e)
# =====================================================================
def pagina_banco():
    ui.cabecalho("Banco de dados", "Criar as tabelas, carregar os dados e eliminar tudo a partir de um banco vazio.")
    ok, msg = db.testar_conexao()
    if not ok:
        st.error("Sem conexão com o PostgreSQL. Confira o container (docker compose up -d) e o arquivo .env.")
        st.code(msg)
        return
    st.success(f"Conectado: {msg} · banco **{db._parametros()['database']}**")

    existentes = db.tabelas_existentes()
    pronto = len(existentes) == len(db.TABELAS)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("1 · Criar tabelas", width="stretch", disabled=pronto, type="primary"):
        try:
            with st.spinner("Executando 01_schema.sql e 02_pgvector.sql..."):
                db.criar_tabelas()
            st.toast("Tabelas criadas.", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(crud.traduzir_erro(e))
    if c2.button("2 · Carregar dados", width="stretch", disabled=not pronto):
        try:
            with st.spinner("Carregando dados..."):
                usados = db.carregar_dados()
            st.toast("Carga concluída: " + ", ".join(usados), icon="✅")
            st.rerun()
        except Exception as e:
            st.error(crud.traduzir_erro(e))
    if c3.button("Recriar tudo", width="stretch", help="Elimina, cria e carrega de novo (demonstração rápida)"):
        try:
            with st.spinner("Eliminando, criando e carregando..."):
                db.eliminar_tudo()
                db.criar_tabelas()
                db.carregar_dados()
            st.toast("Banco recriado do zero.", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(crud.traduzir_erro(e))
    with c4.popover("3 · Eliminar tudo", width="stretch", disabled=not existentes):
        st.warning("Apaga todas as tabelas, a visão e as funções. Os dados serão perdidos.")
        if st.button("Sim, eliminar", type="primary"):
            try:
                db.eliminar_tudo()
                st.toast("Tudo eliminado.", icon="🗑️")
                st.rerun()
            except Exception as e:
                st.error(crud.traduzir_erro(e))

    st.subheader("Tabelas")
    cont = db.contagens()
    linhas = [{"Tabela": t, "Descrição": TABELAS[t]["titulo"],
               "Linhas": cont.get(t, None) if t in cont else None,
               "Situação": "existe" if t in cont else "não existe"} for t in db.TABELAS]
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

    if not pronto:
        return
    db.migrar()

    st.subheader("Recursos de IA e capas")
    faltam_emb = len(ia.jogos_sem_embedding())
    faltam_capa = int(db.consultar("SELECT count(*) AS n FROM jogo WHERE url_capa IS NULL")["n"][0])
    a, b = st.columns(2)
    with a:
        st.metric("Jogos sem embedding", faltam_emb)
        if st.button("Gerar embeddings (Gemini)", disabled=faltam_emb == 0, width="stretch"):
            try:
                with st.spinner("Chamando o Gemini..."):
                    n = ia.atualizar_embeddings()
                st.toast(f"{n} embeddings gravados.", icon="✅")
                st.rerun()
            except ia.ErroIA as e:
                st.error(str(e))
    with b:
        st.metric("Jogos sem capa", faltam_capa)
        ca, cb = st.columns(2)
        refazer = False
        buscar = ca.button("Buscar capas faltantes", disabled=faltam_capa == 0, width="stretch")
        if cb.button("Refazer todas", width="stretch", help="Apaga as capas atuais e busca de novo"):
            buscar, refazer = True, True
        if buscar:
            barra = st.progress(0.0, text="Buscando...")
            achadas, total, lista = capas.atualizar_capas(
                somente_faltantes=not refazer, progresso=lambda f, t: barra.progress(f, text=t))
            barra.empty()
            st.success(f"{achadas} de {total} capas encontradas.")
            if lista:
                st.dataframe(pd.DataFrame(lista), width="stretch", hide_index=True)
            st.caption("Capa errada ou ausente? Corrija a «URL da capa» em Cadastros → Jogos → Alterar.")

    with st.expander("Auditoria de integridade (regras que o banco não consegue impor sozinho)"):
        aud = db.consultar("SELECT * FROM vw_auditoria_integridade")
        if aud.empty:
            st.success("Nenhuma violação encontrada.")
        else:
            st.dataframe(aud, width="stretch", hide_index=True)


# =====================================================================
# Biblioteca  (item 7b / 7c)
# =====================================================================
SQL_ITENS = """
SELECT ib.id_item, ib.id_jogo_plataforma, j.id_jogo, j.titulo, j.url_capa, p.nome AS plataforma,
       ib.status, ib.horas_jogadas,
       (SELECT count(*) FROM conquista c JOIN pacote_conquistas pc ON pc.id_pacote = c.id_pacote
         WHERE pc.id_jogo_plataforma = ib.id_jogo_plataforma)                         AS total,
       (SELECT count(*) FROM desbloqueio d WHERE d.id_item = ib.id_item)              AS desbloqueadas,
       (SELECT COALESCE(sum(c.gamerscore), 0) FROM conquista c
          JOIN pacote_conquistas pc ON pc.id_pacote = c.id_pacote
         WHERE pc.id_jogo_plataforma = ib.id_jogo_plataforma)                         AS gs_total,
       (SELECT COALESCE(sum(c.gamerscore), 0) FROM desbloqueio d
          JOIN conquista c ON c.id_conquista = d.id_conquista WHERE d.id_item = ib.id_item) AS gs
  FROM item_biblioteca ib
  JOIN jogo_plataforma jp ON jp.id_jogo_plataforma = ib.id_jogo_plataforma
  JOIN jogo j             ON j.id_jogo = jp.id_jogo
  JOIN plataforma p       ON p.id_plataforma = jp.id_plataforma
 WHERE ib.id_usuario = %s
 ORDER BY ib.horas_jogadas DESC, j.titulo
"""

SQL_CONQUISTAS_ITEM = """
SELECT c.id_conquista, c.nome, c.descricao, c.gamerscore, pc.nome AS pacote, pc.tipo, d.data_hora
  FROM conquista c
  JOIN pacote_conquistas pc ON pc.id_pacote = c.id_pacote
  LEFT JOIN desbloqueio d   ON d.id_conquista = c.id_conquista AND d.id_item = %s
 WHERE pc.id_jogo_plataforma = %s
 ORDER BY (pc.tipo <> 'BASE'), pc.id_pacote, c.id_conquista
"""


def pagina_biblioteca():
    ui.cabecalho("Biblioteca", "Jogos de cada usuário, com o progresso de conquistas e o gamerscore.")
    ui.exigir_banco()
    usuarios = db.consultar("SELECT id_usuario, gamertag, nome FROM usuario ORDER BY gamertag")
    if usuarios.empty:
        st.info("Não há usuários cadastrados. Cadastre um em **Cadastros → Usuários**.")
        return
    rot = {int(r.id_usuario): f"{r.gamertag} — {r.nome}" for r in usuarios.itertuples()}
    uid = st.selectbox("Usuário", list(rot), format_func=rot.get, key="bib_usuario")

    itens = db.consultar(SQL_ITENS, (uid,))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jogos na biblioteca", len(itens))
    m2.metric("Horas jogadas", f"{float(itens['horas_jogadas'].sum()):g}" if len(itens) else "0")
    m3.metric("Conquistas", int(itens["desbloqueadas"].sum()) if len(itens) else 0)
    m4.metric("Gamerscore", f"{int(itens['gs'].sum()):,}".replace(",", ".") if len(itens) else "0")

    filtro = st.pills("Status", STATUS, selection_mode="multi", key="bib_filtro",
                      format_func=lambda s: ui.CORES_STATUS[s][1])
    vis = itens if not filtro else itens[itens["status"].isin(filtro)]

    aberto = st.session_state.get("bib_item")
    colunas = st.columns(3)
    for i, r in enumerate(vis.itertuples()):
        with colunas[i % 3].container(border=True):
            ca, cb = st.columns([1, 2])
            with ca:
                ui.mostrar_capa(r.titulo, r.url_capa)
            with cb:
                st.markdown(f'<p class="xb-titulo">{r.titulo}</p>'
                            f'<p class="xb-meta">{r.plataforma} · {float(r.horas_jogadas):g} h</p>'
                            f'{ui.selo_status(r.status)}', unsafe_allow_html=True)
            frac = (r.desbloqueadas / r.total) if r.total else 0.0
            st.progress(frac, text=f"{r.desbloqueadas}/{r.total} conquistas · {r.gs}/{r.gs_total} G")
            if st.button("Ver detalhes" if aberto != r.id_item else "Fechar", key=f"det_{r.id_item}",
                         width="stretch"):
                st.session_state["bib_item"] = None if aberto == r.id_item else int(r.id_item)
                st.rerun()
    if vis.empty:
        st.info("Nenhum jogo com esse filtro.")

    _detalhe_item(itens, uid)
    _adicionar_jogo(uid)


def _detalhe_item(itens, uid):
    aberto = st.session_state.get("bib_item")
    if aberto is None or aberto not in set(itens["id_item"].astype(int)):
        return
    r = itens[itens["id_item"] == aberto].iloc[0]
    st.divider()
    st.subheader(f"{r['titulo']} · {r['plataforma']}")
    conq = db.consultar(SQL_CONQUISTAS_ITEM, (int(aberto), int(r["id_jogo_plataforma"])))

    esq, dir_ = st.columns([3, 2])
    with esq:
        if conq.empty:
            st.info("Este jogo/plataforma ainda não tem conquistas cadastradas.")
        for pacote, grupo in conq.groupby("pacote", sort=False):
            feitas = int(grupo["data_hora"].notna().sum())
            st.markdown(f"**{pacote}** ({grupo['tipo'].iloc[0]}) — {feitas}/{len(grupo)}")
            st.progress(feitas / len(grupo))
            for c in grupo.itertuples():
                if pd.notna(c.data_hora):
                    st.markdown(f"✅ **{c.nome}** · {c.gamerscore} G · "
                                f"{pd.Timestamp(c.data_hora):%d/%m/%Y %H:%M}  \n<span class='xb-meta'>{c.descricao}</span>",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"🔒 {c.nome} · {c.gamerscore} G  \n<span class='xb-meta'>{c.descricao}</span>",
                                unsafe_allow_html=True)
    with dir_:
        with st.container(border=True):
            st.markdown("**Registrar desbloqueio**")
            bloqueadas = conq[conq["data_hora"].isna()]
            if bloqueadas.empty:
                st.caption("Todas as conquistas já foram desbloqueadas.")
            else:
                rot = {int(c.id_conquista): f"{c.nome} ({c.gamerscore} G)" for c in bloqueadas.itertuples()}
                with st.form(f"form_desb_{aberto}", clear_on_submit=True):
                    cid = st.selectbox("Conquista", list(rot), format_func=rot.get)
                    d = st.date_input("Data", value=date.today(), min_value=date(2005, 1, 1))
                    h = st.time_input("Hora", value=datetime.now().time().replace(second=0, microsecond=0))
                    if st.form_submit_button("Desbloquear", type="primary"):
                        try:
                            crud.inserir("desbloqueio", {"id_item": int(aberto), "id_conquista": cid,
                                                         "data_hora": datetime.combine(d, h)})
                            st.toast("Conquista desbloqueada!", icon="🏆")
                            st.rerun()
                        except Exception as e:
                            st.error(crud.traduzir_erro(e))
        with st.container(border=True):
            st.markdown("**Atualizar andamento**")
            with st.form(f"form_item_{aberto}"):
                novo_status = st.selectbox("Status", STATUS, index=STATUS.index(r["status"]),
                                           format_func=lambda s: ui.CORES_STATUS[s][1])
                horas = st.number_input("Horas jogadas", min_value=-1000.0, value=float(r["horas_jogadas"]),
                                        step=0.5, format="%.1f")
                if st.form_submit_button("Salvar"):
                    try:
                        crud.atualizar("item_biblioteca", {"id_item": int(aberto)},
                                       {"status": novo_status, "horas_jogadas": horas})
                        st.toast("Item atualizado.", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(crud.traduzir_erro(e))
            with st.popover("Remover da biblioteca"):
                st.warning("Remove o item e todos os desbloqueios dele.")
                if st.button("Confirmar remoção", key=f"rm_{aberto}"):
                    try:
                        crud.excluir("item_biblioteca", {"id_item": int(aberto)})
                        st.session_state["bib_item"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(crud.traduzir_erro(e))


def _adicionar_jogo(uid):
    with st.expander("Adicionar jogo à biblioteca"):
        livres = db.consultar("""
            SELECT jp.id_jogo_plataforma, j.titulo || ' (' || p.nome || ')' AS rotulo
              FROM jogo_plataforma jp JOIN jogo j ON j.id_jogo = jp.id_jogo
              JOIN plataforma p ON p.id_plataforma = jp.id_plataforma
             WHERE NOT EXISTS (SELECT 1 FROM item_biblioteca ib WHERE ib.id_usuario = %s
                                  AND ib.id_jogo_plataforma = jp.id_jogo_plataforma)
             ORDER BY 2""", (uid,))
        if livres.empty:
            st.caption("Este usuário já tem todos os jogos cadastrados.")
            return
        rot = dict(zip(livres["id_jogo_plataforma"].astype(int), livres["rotulo"]))
        with st.form("form_add_jogo", clear_on_submit=True):
            jp = st.selectbox("Jogo / plataforma", list(rot), format_func=rot.get)
            status = st.selectbox("Status", STATUS, format_func=lambda s: ui.CORES_STATUS[s][1])
            if st.form_submit_button("Adicionar", type="primary"):
                try:
                    crud.inserir("item_biblioteca", {"id_usuario": uid, "id_jogo_plataforma": jp, "status": status})
                    st.toast("Jogo adicionado.", icon="🎮")
                    st.rerun()
                except Exception as e:
                    st.error(crud.traduzir_erro(e))


# =====================================================================
# Consultas  (item 7c)
# =====================================================================
def pagina_consultas():
    ui.cabecalho("Consultas", "Três consultas agregadas, cada uma sobre três ou mais tabelas.")
    ui.exigir_banco()
    abas = st.tabs([f"{i}. {c['titulo']}" for i, c in enumerate(consultas.CONSULTAS.values(), 1)])
    for aba, (chave, cfg) in zip(abas, consultas.CONSULTAS.items()):
        with aba:
            st.markdown(cfg["descricao"])
            st.caption(f"Tabelas: {cfg['tabelas']}")
            with st.expander("Ver o comando SQL"):
                st.code(cfg["sql"], language="sql")
            try:
                df = consultas.executar(chave)
            except Exception as e:
                st.error(crud.traduzir_erro(e))
                continue
            esq, dir_ = st.columns([2, 3])
            with esq:
                st.dataframe(df, width="stretch", hide_index=True)
                st.download_button("Baixar CSV", df.to_csv(index=False).encode("utf-8"),
                                   f"consulta_{chave}.csv", "text/csv", key=f"csv_{chave}")
            with dir_:
                fig = consultas.grafico(chave, df)
                st.pyplot(fig, width="stretch")
                st.download_button("Baixar gráfico (PNG)", consultas.png(fig), f"grafico_{chave}.png",
                                   "image/png", key=f"png_{chave}")


# =====================================================================
# Recomendação com IA  (item 7f)
# =====================================================================
def _cartoes_recomendacao(df):
    for r in df.itertuples():
        with st.container(border=True):
            a, b, c = st.columns([1, 2, 7])
            a.markdown(f'<div class="xb-pos">#{r.posicao}</div>', unsafe_allow_html=True)
            with b:
                ui.mostrar_capa(r.titulo, r.url_capa)
            with c:
                st.markdown(f'<p class="xb-titulo">{r.titulo}</p>'
                            f'<p class="xb-meta">{r.generos or ""}</p>'
                            f'<p class="xb-just">{r.justificativa}</p>', unsafe_allow_html=True)


def pagina_ia():
    ui.cabecalho("Recomendação com IA",
                 "O pgvector encontra os jogos mais parecidos com o gosto do usuário; o Gemini escolhe e justifica.")
    ui.exigir_banco()
    usuarios = db.consultar("SELECT id_usuario, gamertag FROM usuario ORDER BY gamertag")
    if usuarios.empty:
        st.info("Não há usuários cadastrados.")
        return
    rot = dict(zip(usuarios["id_usuario"].astype(int), usuarios["gamertag"]))
    c1, c2, c3 = st.columns([3, 2, 2])
    uid = c1.selectbox("Usuário", list(rot), format_func=rot.get, key="ia_usuario")
    qtd = c2.slider("Quantidade", 1, 5, 3)
    c3.markdown("&nbsp;", unsafe_allow_html=True)
    gerar = c3.button("Gerar recomendação", type="primary", width="stretch")

    if gerar:
        try:
            with st.spinner("Buscando jogos parecidos e consultando o Gemini..."):
                res = ia.recomendar(uid, qtd)
            res["id_usuario"] = uid
            st.session_state["ia_ultima"] = res
            st.toast("Recomendação gerada e salva no banco.", icon="✨")
        except ia.ErroIA as e:
            st.error(str(e))
        except Exception as e:
            st.error(crud.traduzir_erro(e))

    ultima = st.session_state.get("ia_ultima")
    if ultima and ultima.get("id_usuario") == uid:
        st.subheader("Resultado")
        st.caption(f"Recomendação #{ultima['id_recomendacao']} · modelo {ultima['modelo']}")
        _cartoes_recomendacao(ia.ler_recomendacao(ultima["id_recomendacao"]))
        with st.expander("Como o resultado foi gerado"):
            st.markdown("**1. Recuperação (pgvector)** — jogos mais próximos do perfil, por distância de cosseno:")
            st.dataframe(ultima["candidatos"][["titulo", "generos", "similaridade"]], width="stretch",
                         hide_index=True)
            st.markdown("**2. Prompt enviado ao Gemini:**")
            st.code(ultima["prompt"], language="text")

    st.subheader("Histórico deste usuário")
    hist = ia.historico_recomendacoes(uid)
    if hist.empty:
        st.caption("Nenhuma recomendação gravada ainda.")
    else:
        rotulos = {int(r.id_recomendacao): f"#{r.id_recomendacao} · {pd.Timestamp(r.data_geracao):%d/%m/%Y %H:%M} · {r.modelo_ia}"
                   for r in hist.itertuples()}
        sel = st.selectbox("Recomendação", list(rotulos), format_func=rotulos.get, key="ia_hist")
        _cartoes_recomendacao(ia.ler_recomendacao(sel))


# =====================================================================
# Cadastros  (item 7b) - insere, lista, altera e exclui em qualquer tabela
# =====================================================================
AVISO_EXCLUSAO = {
    "usuario": "Excluir o usuário remove também a biblioteca, os desbloqueios e as recomendações dele (RN21).",
    "jogo": "Excluir o jogo remove também suas plataformas, pacotes, conquistas, desbloqueios e recomendações (RN20).",
    "jogo_plataforma": "Remove os pacotes, as conquistas e os itens de biblioteca desse jogo/plataforma (RN20).",
    "pacote_conquistas": "Remove as conquistas do pacote e os desbloqueios delas (RN20).",
    "conquista": "Remove também os desbloqueios dessa conquista (RN20).",
    "item_biblioteca": "Remove também os desbloqueios do item (RN20/RN21).",
    "desenvolvedora": "Só é possível se nenhum jogo usar esta desenvolvedora (RN19).",
    "publicadora": "Só é possível se nenhum jogo usar esta publicadora (RN19).",
    "genero": "Só é possível se nenhum jogo usar este gênero (RN19).",
    "plataforma": "Só é possível se nenhum jogo estiver cadastrado nesta plataforma (RN19).",
}


def _campo(c, tabela, chave, atual=None, opcoes_cache=None):
    """Desenha o widget adequado para uma coluna e devolve o valor informado (ou None)."""
    rot = c["rotulo"] + ("" if c["obrigatorio"] else " (opcional)")
    k = f"{chave}_{tabela}_{c['nome']}"
    t = c["tipo"]
    if t == "texto":
        v = st.text_input(rot, value=atual or "", key=k)
        return v.strip() or None
    if t == "area":
        v = st.text_area(rot, value=atual or "", key=k)
        return v.strip() or None
    if t == "int":
        return _int(st.number_input(rot, value=None if atual is None else int(atual), step=1, key=k))
    if t == "num":
        padrao = atual if atual is not None else c["padrao"]
        v = st.number_input(rot, value=None if padrao is None else float(padrao), step=0.5, format="%.1f", key=k)
        return None if v is None else float(v)
    if t == "data":
        padrao = atual if atual is not None else (date.today() if c["padrao"] == "hoje" else None)
        if isinstance(padrao, datetime):
            padrao = padrao.date()
        return st.date_input(rot, value=padrao, min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                             key=k, format="DD/MM/YYYY")
    if t == "datahora":
        base = atual or (datetime.now().replace(second=0, microsecond=0) if c["padrao"] == "agora" else None)
        a, b = st.columns(2)
        d = a.date_input(rot, value=base.date() if base else None, min_value=date(1950, 1, 1),
                         max_value=date(2100, 12, 31), key=k + "_d", format="DD/MM/YYYY")
        h = b.time_input("Hora", value=base.time() if base else None, key=k + "_h")
        return datetime.combine(d, h) if d and h else None
    if t == "escolha":
        ops = c["opcoes"]
        ini = ops.index(atual) if atual in ops else (ops.index(c["padrao"]) if c["padrao"] in ops else 0)
        return st.selectbox(rot, ops, index=ini, key=k)
    if t == "fk":
        ops = opcoes_cache[c["nome"]]
        ids = [o[0] for o in ops]
        rotulos = dict(ops)
        if not ids:
            st.warning(f"Não há registros em «{TABELAS[c['ref']]['titulo']}». Cadastre primeiro (RN: dependência).")
            return None
        ini = ids.index(int(atual)) if atual is not None and int(atual) in ids else None
        return st.selectbox(rot, ids, index=ini, format_func=rotulos.get, key=k, placeholder="Escolha...")
    raise ValueError(t)


def _int(v):
    return None if v is None else int(v)


def _opcoes_fk(tabela):
    return {c["nome"]: crud.opcoes_fk(c["ref"]) for c in TABELAS[tabela]["colunas"] if c["tipo"] == "fk"}


def _faltando(tabela, valores):
    return [c["rotulo"] for c in TABELAS[tabela]["colunas"]
            if c["obrigatorio"] and valores.get(c["nome"]) in (None, "")]


def _depois_de_gravar_jogo(id_jogo, titulo):
    """Jogo novo/alterado: atualiza embedding (Gemini) e tenta achar a capa."""
    with st.spinner("Atualizando embedding e capa do jogo..."):
        try:
            ia.atualizar_embeddings([id_jogo])
        except ia.ErroIA as e:
            st.warning(f"Jogo salvo, mas o embedding não foi gerado: {e} (use Banco de dados → Gerar embeddings).")
        atual = db.consultar("SELECT url_capa FROM jogo WHERE id_jogo = %s", (id_jogo,))["url_capa"][0]
        if not atual:
            url = capas.buscar_capa(titulo)
            if url:
                crud.atualizar("jogo", {"id_jogo": id_jogo}, {"url_capa": url})


def pagina_cadastros():
    ui.cabecalho("Cadastros", "Inserir, consultar, alterar e excluir registros de qualquer tabela, respeitando as dependências.")
    ui.exigir_banco()
    msg = st.session_state.pop("cad_msg", None)
    if msg:
        st.success(msg)
    n_ins = st.session_state.setdefault("cad_n_ins", 0)
    tabela = st.selectbox("Tabela", db.TABELAS, format_func=lambda t: f"{TABELAS[t]['titulo']}  ({t})", key="cad_tabela")
    cfg = TABELAS[tabela]
    df = crud.listar(tabela)
    fks = [c for c in cfg["colunas"] if c["tipo"] == "fk"]

    def rotulo_linha(r):
        chave = ", ".join(str(r[p]) for p in cfg["pk"])
        if "__rotulo" in df.columns and r["__rotulo"]:
            return f"{r['__rotulo']}  [id {chave}]"
        return " · ".join(str(r[f"{c['nome']}__rotulo"]) for c in fks) + f"  [{chave}]"

    aba_l, aba_i, aba_a, aba_e = st.tabs(["Consultar", "Inserir", "Alterar", "Excluir"])

    with aba_l:
        mostra = df.copy()
        for c in fks:
            mostra[c["nome"]] = mostra[c["nome"] + "__rotulo"]
        mostra = mostra[[n for n in crud.colunas_visiveis(tabela)]]
        mostra.columns = [next((c["rotulo"] for c in cfg["colunas"] if c["nome"] == n), n) for n in mostra.columns]
        st.caption(f"{len(df)} registro(s)")
        st.dataframe(mostra, width="stretch", hide_index=True)

    with aba_i:
        opc = _opcoes_fk(tabela)
        with st.form(f"form_ins_{tabela}"):
            valores = {c["nome"]: _campo(c, tabela, f"ins{n_ins}", None, opc) for c in cfg["colunas"]}
            enviar = st.form_submit_button("Inserir", type="primary")
        if enviar:
            falta = _faltando(tabela, valores)
            if falta:
                st.error("Preencha: " + ", ".join(falta))
            else:
                try:
                    pk = crud.inserir(tabela, valores)
                    if tabela == "jogo":
                        _depois_de_gravar_jogo(pk["id_jogo"], valores["titulo"])
                    st.session_state["cad_msg"] = f"Registro inserido ({', '.join(f'{k}={v}' for k, v in pk.items())})."
                    st.session_state["cad_n_ins"] = n_ins + 1          # limpa o formulário
                    st.rerun()
                except Exception as e:
                    st.error(crud.traduzir_erro(e))

    with aba_a:
        editaveis = [c for c in cfg["colunas"] if c["nome"] not in cfg["pk"]]
        if df.empty:
            st.info("Não há registros para alterar.")
        elif not editaveis:
            st.info("Esta tabela é só uma combinação de chaves: para alterar, exclua o registro e insira outro.")
        else:
            rot = {i: rotulo_linha(r) for i, r in df.iterrows()}
            idx = st.selectbox("Registro", list(rot), format_func=rot.get, key=f"alt_sel_{tabela}")
            linha = df.loc[idx]
            pk = {p: _py(linha[p]) for p in cfg["pk"]}
            sufixo = "_".join(str(v) for v in pk.values())
            opc = _opcoes_fk(tabela)
            for p in cfg["pk"]:
                if p not in [c["nome"] for c in editaveis]:
                    st.text_input(f"{p} (chave, não editável)", value=str(pk[p]), disabled=True,
                                  key=f"altpk_{tabela}_{p}_{sufixo}")
            with st.form(f"form_alt_{tabela}_{sufixo}"):
                valores = {c["nome"]: _campo(c, tabela, f"alt{sufixo}", _py(linha[c["nome"]]), opc)
                           for c in editaveis}
                enviar = st.form_submit_button("Salvar alterações", type="primary")
            if enviar:
                falta = [c["rotulo"] for c in editaveis if c["obrigatorio"] and valores[c["nome"]] in (None, "")]
                if falta:
                    st.error("Preencha: " + ", ".join(falta))
                else:
                    try:
                        crud.atualizar(tabela, pk, valores)
                        if tabela == "jogo":
                            _depois_de_gravar_jogo(pk["id_jogo"], valores["titulo"])
                        st.session_state["cad_msg"] = "Registro alterado."
                        st.rerun()
                    except Exception as e:
                        st.error(crud.traduzir_erro(e))

    with aba_e:
        if df.empty:
            st.info("Não há registros para excluir.")
        else:
            rot = {i: rotulo_linha(r) for i, r in df.iterrows()}
            idx = st.selectbox("Registro", list(rot), format_func=rot.get, key=f"del_sel_{tabela}")
            pk = {p: _py(df.loc[idx][p]) for p in cfg["pk"]}
            if tabela in AVISO_EXCLUSAO:
                st.info(AVISO_EXCLUSAO[tabela])
            ok = st.checkbox("Confirmo a exclusão", key=f"del_ok_{tabela}")
            if st.button("Excluir", disabled=not ok, type="primary", key=f"del_btn_{tabela}"):
                try:
                    crud.excluir(tabela, pk)
                    st.session_state["cad_msg"] = "Registro excluído."
                    st.rerun()
                except Exception as e:
                    st.error(crud.traduzir_erro(e))
