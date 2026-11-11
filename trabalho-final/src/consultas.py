"""
As três consultas agregadas do trabalho (item 6 do enunciado), cada uma sobre
três ou mais tabelas, com o gráfico correspondente.
"""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import db

VERDE = "#107C10"
VERDE_CLARO = "#9BF00B"
CINZA = "#4B5563"

CONSULTAS = {
    "q1": dict(
        titulo="Ranking de gamerscore por usuário",
        tabelas="usuario, item_biblioteca, desbloqueio, conquista",
        descricao=("Soma o gamerscore das conquistas desbloqueadas por cada usuário e ordena do maior "
                   "para o menor. Responde: quem são os jogadores mais conquistadores da plataforma?"),
        sql="""SELECT u.gamertag,
       COUNT(*)          AS conquistas_desbloqueadas,
       SUM(c.gamerscore) AS gamerscore_total
  FROM usuario u
  JOIN item_biblioteca ib ON ib.id_usuario = u.id_usuario
  JOIN desbloqueio d      ON d.id_item = ib.id_item
  JOIN conquista c        ON c.id_conquista = d.id_conquista
 GROUP BY u.id_usuario, u.gamertag
 ORDER BY gamerscore_total DESC, u.gamertag""",
    ),
    "q2": dict(
        titulo="Conquistas desbloqueadas por trimestre",
        tabelas="desbloqueio, item_biblioteca, conquista",
        descricao=("Agrupa os desbloqueios por trimestre do ano, contando as conquistas, somando o "
                   "gamerscore e o número de usuários ativos. Responde: como a atividade da plataforma "
                   "evolui ao longo do tempo?"),
        sql="""SELECT EXTRACT(YEAR FROM d.data_hora)::int || '-T' || EXTRACT(QUARTER FROM d.data_hora)::int AS trimestre,
       COUNT(*)                        AS conquistas,
       SUM(c.gamerscore)               AS gamerscore,
       COUNT(DISTINCT ib.id_usuario)   AS usuarios_ativos
  FROM desbloqueio d
  JOIN item_biblioteca ib ON ib.id_item = d.id_item
  JOIN conquista c        ON c.id_conquista = d.id_conquista
 GROUP BY 1
 ORDER BY 1""",
    ),
    "q3": dict(
        titulo="Jogos concluídos (100% do pacote base) por ano",
        tabelas="item_biblioteca, pacote_conquistas, conquista, desbloqueio",
        descricao=("Considera concluído o item da biblioteca cujo usuário desbloqueou todas as conquistas "
                   "do pacote BASE; o ano é o da última conquista desbloqueada. Responde: quantos jogos "
                   "foram finalizados a cada ano?"),
        sql="""WITH base AS (
    SELECT ib.id_item,
           COUNT(c.id_conquista) AS total,
           COUNT(d.id_conquista) AS desbloqueadas,
           MAX(d.data_hora)      AS ultima
      FROM item_biblioteca ib
      JOIN pacote_conquistas pc ON pc.id_jogo_plataforma = ib.id_jogo_plataforma
                               AND pc.tipo = 'BASE'
      JOIN conquista c          ON c.id_pacote = pc.id_pacote
      LEFT JOIN desbloqueio d   ON d.id_item = ib.id_item
                               AND d.id_conquista = c.id_conquista
     GROUP BY ib.id_item
)
SELECT EXTRACT(YEAR FROM ultima)::int AS ano,
       COUNT(*)                       AS jogos_concluidos
  FROM base
 WHERE total > 0 AND desbloqueadas = total
 GROUP BY 1
 ORDER BY 1""",
    ),
}


def executar(chave):
    return db.consultar(CONSULTAS[chave]["sql"])


def _estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color("#D1D5DB")
    ax.spines["bottom"].set_color("#D1D5DB")
    ax.tick_params(colors=CINZA)
    ax.yaxis.grid(True, color="#E5E7EB")
    ax.set_axisbelow(True)


def grafico(chave, df):
    """Devolve a figura do matplotlib correspondente à consulta."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    if df.empty:
        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center", color=CINZA)
        ax.axis("off")
        return fig
    if chave == "q1":
        d = df.sort_values("gamerscore_total")
        barras = ax.barh(d["gamertag"], d["gamerscore_total"], color=VERDE)
        ax.bar_label(barras, padding=3, color=CINZA)
        ax.set_xlabel("Gamerscore total")
        ax.xaxis.grid(True, color="#E5E7EB")
        ax.yaxis.grid(False)
        _estilo(ax)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color="#E5E7EB")
    elif chave == "q2":
        barras = ax.bar(df["trimestre"], df["conquistas"], color=VERDE)
        ax.bar_label(barras, padding=2, color=CINZA, fontsize=8)
        ax.set_ylabel("Conquistas desbloqueadas")
        ax.set_xlabel("Trimestre")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        _estilo(ax)
    else:
        barras = ax.bar(df["ano"].astype(str), df["jogos_concluidos"], color=VERDE, width=0.55)
        ax.bar_label(barras, padding=3, color=CINZA)
        ax.set_ylabel("Jogos concluídos")
        ax.set_xlabel("Ano")
        _estilo(ax)
    ax.set_title(CONSULTAS[chave]["titulo"], loc="left", color="#111827", fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig


def png(fig):
    """Bytes PNG (alta resolução) para baixar e colar no relatório."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="white")
    return buf.getvalue()
