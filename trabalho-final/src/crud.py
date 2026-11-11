"""
Operações genéricas de inserir, listar, alterar e excluir para qualquer das
14 tabelas, guiadas pela descrição em esquema.py, e tradução das mensagens
de erro do PostgreSQL (restrições e gatilhos) para texto compreensível.
"""
import re

import pandas as pd
from psycopg2 import errors

import db
from esquema import ROTULOS, TABELAS


# ---------------------------------------------------------------------
# Consultas de apoio
# ---------------------------------------------------------------------
def colunas_visiveis(tabela):
    """pk + colunas descritas (não inclui o vetor de embedding)."""
    cfg = TABELAS[tabela]
    nomes = list(cfg["pk"])
    nomes += [c["nome"] for c in cfg["colunas"] if c["nome"] not in nomes]
    return nomes


def listar(tabela):
    """DataFrame com todas as linhas; cada FK ganha uma coluna '<fk>__rotulo' legível."""
    cfg = TABELAS[tabela]
    partes = [f"t.{c}" for c in colunas_visiveis(tabela)]
    juncoes = []
    for i, c in enumerate(cfg["colunas"]):
        if c["tipo"] == "fk":
            ref = c["ref"]
            ref_pk = TABELAS[ref]["pk"][0]
            juncoes.append(f"LEFT JOIN (SELECT t.{ref_pk} AS k, {ROTULOS[ref]} AS rot FROM {ref} t) f{i} "
                           f"ON f{i}.k = t.{c['nome']}")
            partes.append(f"f{i}.rot AS {c['nome']}__rotulo")
    if tabela in ROTULOS:
        partes.append(f"{ROTULOS[tabela]} AS __rotulo")
    ordem = ", ".join(f"t.{c}" for c in cfg["pk"])
    return db.consultar(f"SELECT {', '.join(partes)} FROM {tabela} t {' '.join(juncoes)} ORDER BY {ordem}")


def opcoes_fk(ref):
    """[(id, rótulo)] dos registros de uma tabela, para as listas suspensas."""
    pk = TABELAS[ref]["pk"][0]
    df = db.consultar(f"SELECT t.{pk} AS id, {ROTULOS[ref]} AS rotulo FROM {ref} t ORDER BY 2")
    return list(zip(df["id"].astype(int), df["rotulo"]))


def pk_where(tabela, pk):
    cols = TABELAS[tabela]["pk"]
    return " AND ".join(f"{c} = %s" for c in cols), [pk[c] for c in cols]


# ---------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------
def inserir(tabela, valores):
    """Insere uma linha. Valores None são omitidos (vale o DEFAULT do banco). Devolve a PK."""
    cfg = TABELAS[tabela]
    dados = {k: v for k, v in valores.items() if v is not None}
    pk = cfg["pk"]
    if dados:
        cols = ", ".join(dados)
        marcadores = ", ".join(["%s"] * len(dados))
        sql = f"INSERT INTO {tabela} ({cols}) VALUES ({marcadores}) RETURNING {', '.join(pk)}"
        params = list(dados.values())
    else:
        sql = f"INSERT INTO {tabela} DEFAULT VALUES RETURNING {', '.join(pk)}"
        params = None
    with db.transacao() as cur:
        cur.execute(sql, params)
        linha = cur.fetchone()
    return dict(zip(pk, linha))


def atualizar(tabela, pk, valores):
    """Altera as colunas informadas da linha identificada por pk (dict)."""
    if not valores:
        raise ValueError("Esta tabela não tem colunas alteráveis (a linha é só a combinação de chaves).")
    sets = ", ".join(f"{c} = %s" for c in valores)
    where, params_pk = pk_where(tabela, pk)
    return db.executar(f"UPDATE {tabela} SET {sets} WHERE {where}", list(valores.values()) + params_pk)


def excluir(tabela, pk):
    where, params = pk_where(tabela, pk)
    return db.executar(f"DELETE FROM {tabela} WHERE {where}", params)


# ---------------------------------------------------------------------
# Tradução de erros
# ---------------------------------------------------------------------
MSG_UNICOS = {
    "uq_usuario_email": "Já existe um usuário com esse e-mail (RN01).",
    "uq_usuario_gamertag": "Já existe um usuário com essa gamertag (RN01).",
    "uq_genero_nome": "Esse gênero já está cadastrado.",
    "uq_plataforma_nome": "Essa plataforma já está cadastrada.",
    "uq_jogo_plataforma": "Esse jogo já está cadastrado nessa plataforma.",
    "uq_item_usuario_jogo_plataforma": "Esse usuário já tem esse jogo/plataforma na biblioteca (RN11).",
    "ux_pacote_base_por_jogo_plataforma": "Esse jogo/plataforma já possui um pacote BASE (RN06).",
    "uq_recomendacao_posicao": "Essa posição já está ocupada nesta recomendação (RN23).",
}
MSG_CHECKS = {
    "ck_pacote_tipo": "O tipo do pacote deve ser BASE, DLC ou UPDATE (RN06).",
    "ck_conquista_gamerscore": "O gamerscore da conquista deve ser maior que zero (RN07).",
    "ck_item_status": "Status inválido para o item da biblioteca (RN12).",
    "ck_item_horas": "As horas jogadas não podem ser negativas (RN13).",
    "ck_recomendacao_posicao": "A posição na recomendação deve ser maior que zero (RN23).",
}


def traduzir_erro(erro):
    """Converte uma exceção do psycopg2 em uma frase para o usuário."""
    diag = getattr(erro, "diag", None)
    restricao = getattr(diag, "constraint_name", None) or ""
    detalhe = getattr(diag, "message_detail", None) or ""
    primaria = getattr(diag, "message_primary", None) or str(erro).strip()

    if isinstance(erro, errors.UniqueViolation):
        return MSG_UNICOS.get(restricao, "Esse registro já existe (valor ou chave repetidos).")
    if isinstance(erro, errors.ForeignKeyViolation):
        m = re.search(r'is still referenced from table "(\w+)"', detalhe)
        if m:
            return (f"Não é possível excluir: o registro ainda é usado na tabela «{m.group(1)}». "
                    "Remova ou altere os dependentes primeiro (RN19).")
        return "Referência inválida: o registro relacionado escolhido não existe."
    if isinstance(erro, errors.CheckViolation):
        if restricao in MSG_CHECKS:
            return MSG_CHECKS[restricao]
        return primaria        # gatilhos T2/T3 também usam este código e já citam a regra
    if isinstance(erro, errors.NotNullViolation):
        return f"O campo «{getattr(diag, 'column_name', '') or '?'}» é obrigatório."
    if isinstance(erro, errors.StringDataRightTruncation):
        return "Texto longo demais para o campo."
    if isinstance(erro, errors.RaiseException):          # gatilhos T1, T2, T3: a mensagem já cita a regra
        return primaria
    if isinstance(erro, (errors.InvalidTextRepresentation, errors.NumericValueOutOfRange,
                         errors.InvalidDatetimeFormat)):
        return f"Valor em formato inválido: {primaria}"
    return primaria
