"""
Plataforma de Acompanhamento de Conquistas (Xbox) - DEC7129 Banco de Dados I.
Execute (na pasta trabalho-final/):   streamlit run src/app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))      # permite 'import db' etc.

import paginas  # noqa: E402
import ui       # noqa: E402

st.set_page_config(page_title="Conquistas Xbox", page_icon="🎮", layout="wide")
ui.aplicar_estilo()

menu = st.navigation([
    st.Page(paginas.pagina_biblioteca, title="Biblioteca", icon="🎮", url_path="biblioteca", default=True),
    st.Page(paginas.pagina_consultas, title="Consultas", icon="📊", url_path="consultas"),
    st.Page(paginas.pagina_ia, title="Recomendação IA", icon="✨", url_path="ia"),
    st.Page(paginas.pagina_cadastros, title="Cadastros", icon="🗂️", url_path="cadastros"),
    st.Page(paginas.pagina_banco, title="Banco de dados", icon="🛢️", url_path="banco"),
])
st.sidebar.markdown("### Conquistas Xbox")
st.sidebar.caption("DEC7129 · Banco de Dados I · UFSC")
menu.run()
