"""Elementos visuais compartilhados: estilo (CSS), capas, selos de status e checagem do banco."""
import html

import streamlit as st

import capas
import db

CSS = """
<style>
[data-testid="stSidebar"] { background: #0B1F0B; }
[data-testid="stSidebar"] * { color: #E8F5E8 !important; }
[data-testid="stSidebar"] [aria-selected="true"], [data-testid="stSidebar"] a[aria-current="page"] {
    background: rgba(155,240,11,.18) !important; border-radius: 8px; }
h1 { letter-spacing: -.02em; }
.xb-sub { color:#4B5563; margin-top:-0.6rem; margin-bottom:1rem; }
.xb-selo { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.72rem;
           font-weight:700; letter-spacing:.03em; color:#fff; }
.xb-titulo { font-weight:700; font-size:1.02rem; line-height:1.25; margin:0 0 .15rem 0; }
.xb-meta { color:#4B5563; font-size:.85rem; margin:0 0 .4rem 0; }
.xb-just { color:#1F2937; font-size:.95rem; }
.xb-pos { font-size:2.2rem; font-weight:800; color:#107C10; line-height:1; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #DDE5DD; border-radius:12px; padding:.6rem .9rem; }
div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; }
</style>
"""

CORES_STATUS = {
    "FINALIZADO": ("#107C10", "Finalizado"),
    "JOGANDO": ("#1F6FEB", "Jogando"),
    "PAUSADO": ("#B7791F", "Pausado"),
    "ABANDONADO": ("#9B2C2C", "Abandonado"),
    "QUERO_JOGAR": ("#6B7280", "Quero jogar"),
}


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(titulo, subtitulo=""):
    st.title(titulo)
    if subtitulo:
        st.markdown(f'<p class="xb-sub">{html.escape(subtitulo)}</p>', unsafe_allow_html=True)


def selo_status(status):
    cor, texto = CORES_STATUS.get(status, ("#6B7280", status))
    return f'<span class="xb-selo" style="background:{cor}">{texto}</span>'


def mostrar_capa(titulo, url):
    """Capa vertical 2:3; se não houver imagem, cartão colorido com as iniciais."""
    if url:
        st.image(url, width="stretch")
    else:
        st.markdown(capas.cartao_reserva(titulo), unsafe_allow_html=True)


def exigir_banco():
    """Interrompe a página com um aviso se o banco ainda não está pronto."""
    ok, msg = db.testar_conexao()
    if not ok:
        st.error("Não consegui conectar ao PostgreSQL. Confira se o container está de pé e o arquivo .env.")
        st.code(msg)
        st.stop()
    if len(db.tabelas_existentes()) < len(db.TABELAS):
        st.warning("As tabelas ainda não existem. Abra **Banco de dados** e use *Criar tabelas* e *Carregar dados*.")
        st.stop()
    db.migrar()
