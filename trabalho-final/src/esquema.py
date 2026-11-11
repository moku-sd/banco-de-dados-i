"""
Descrição das 14 tabelas (colunas, tipos, chaves) usada para gerar
automaticamente os formulários de cadastro (inserir / alterar / excluir).

Tipos de campo:  texto, area, int, num, data, datahora, escolha, fk
  - fk:      lista suspensa com os registros da tabela referenciada
  - escolha: lista suspensa com opções fixas (CHECK do banco)
"""

STATUS = ["QUERO_JOGAR", "JOGANDO", "PAUSADO", "ABANDONADO", "FINALIZADO"]
TIPOS_PACOTE = ["BASE", "DLC", "UPDATE"]


def col(nome, rotulo, tipo="texto", obrigatorio=True, ref=None, opcoes=None, padrao=None):
    return dict(nome=nome, rotulo=rotulo, tipo=tipo, obrigatorio=obrigatorio,
                ref=ref, opcoes=opcoes, padrao=padrao)


# Expressão SQL (alias "t") que produz o texto legível de um registro de cada tabela.
ROTULOS = {
    "usuario": "t.gamertag",
    "desenvolvedora": "t.nome",
    "publicadora": "t.nome",
    "genero": "t.nome",
    "plataforma": "t.nome",
    "jogo": "t.titulo",
    "jogo_plataforma": "(SELECT j.titulo || ' (' || p.nome || ')' FROM jogo j, plataforma p "
                       "WHERE j.id_jogo = t.id_jogo AND p.id_plataforma = t.id_plataforma)",
    "pacote_conquistas": "(SELECT t.nome || ' [' || t.tipo || '] - ' || j.titulo || ' (' || p.nome || ')' "
                         "FROM jogo_plataforma jp JOIN jogo j ON j.id_jogo = jp.id_jogo "
                         "JOIN plataforma p ON p.id_plataforma = jp.id_plataforma "
                         "WHERE jp.id_jogo_plataforma = t.id_jogo_plataforma)",
    "conquista": "(SELECT t.nome || ' - ' || j.titulo FROM pacote_conquistas pc "
                 "JOIN jogo_plataforma jp ON jp.id_jogo_plataforma = pc.id_jogo_plataforma "
                 "JOIN jogo j ON j.id_jogo = jp.id_jogo WHERE pc.id_pacote = t.id_pacote)",
    "item_biblioteca": "(SELECT u.gamertag || ' · ' || j.titulo || ' (' || p.nome || ')' "
                       "FROM usuario u, jogo_plataforma jp JOIN jogo j ON j.id_jogo = jp.id_jogo "
                       "JOIN plataforma p ON p.id_plataforma = jp.id_plataforma "
                       "WHERE u.id_usuario = t.id_usuario AND jp.id_jogo_plataforma = t.id_jogo_plataforma)",
    "recomendacao": "(SELECT '#' || t.id_recomendacao || ' - ' || u.gamertag || ' - ' || "
                    "to_char(t.data_geracao, 'DD/MM/YYYY HH24:MI') FROM usuario u WHERE u.id_usuario = t.id_usuario)",
}

TABELAS = {
    "usuario": dict(
        titulo="Usuários", pk=["id_usuario"], auto=True,
        colunas=[
            col("nome", "Nome"),
            col("email", "E-mail"),
            col("gamertag", "Gamertag"),
            col("data_cadastro", "Data de cadastro", "datahora", obrigatorio=False,
                padrao="agora"),
        ]),
    "desenvolvedora": dict(
        titulo="Desenvolvedoras", pk=["id_desenvolvedora"], auto=True,
        colunas=[col("nome", "Nome"), col("pais", "País", obrigatorio=False),
                 col("ano_fundacao", "Ano de fundação", "int", obrigatorio=False)]),
    "publicadora": dict(
        titulo="Publicadoras", pk=["id_publicadora"], auto=True,
        colunas=[col("nome", "Nome"), col("pais", "País", obrigatorio=False),
                 col("ano_fundacao", "Ano de fundação", "int", obrigatorio=False)]),
    "genero": dict(
        titulo="Gêneros", pk=["id_genero"], auto=True,
        colunas=[col("nome", "Nome")]),
    "plataforma": dict(
        titulo="Plataformas", pk=["id_plataforma"], auto=True,
        colunas=[col("nome", "Nome"),
                 col("ano_lancamento", "Ano de lançamento", "int", obrigatorio=False)]),
    "jogo": dict(
        titulo="Jogos", pk=["id_jogo"], auto=True,
        colunas=[
            col("titulo", "Título"),
            col("descricao", "Descrição", "area", obrigatorio=False),
            col("data_lancamento", "Data de lançamento", "data"),
            col("id_desenvolvedora", "Desenvolvedora", "fk", ref="desenvolvedora"),
            col("id_publicadora", "Publicadora", "fk", ref="publicadora"),
            col("url_capa", "URL da capa", obrigatorio=False),
        ]),
    "jogo_genero": dict(
        titulo="Gêneros do jogo", pk=["id_jogo", "id_genero"], auto=False,
        colunas=[col("id_jogo", "Jogo", "fk", ref="jogo"),
                 col("id_genero", "Gênero", "fk", ref="genero")]),
    "jogo_plataforma": dict(
        titulo="Jogo × Plataforma", pk=["id_jogo_plataforma"], auto=True,
        colunas=[col("id_jogo", "Jogo", "fk", ref="jogo"),
                 col("id_plataforma", "Plataforma", "fk", ref="plataforma"),
                 col("data_lancamento_plataforma", "Lançamento na plataforma", "data",
                     obrigatorio=False)]),
    "pacote_conquistas": dict(
        titulo="Pacotes de conquistas", pk=["id_pacote"], auto=True,
        colunas=[col("id_jogo_plataforma", "Jogo / plataforma", "fk", ref="jogo_plataforma"),
                 col("nome", "Nome"),
                 col("tipo", "Tipo", "escolha", opcoes=TIPOS_PACOTE),
                 col("data_lancamento", "Data de lançamento", "data")]),
    "conquista": dict(
        titulo="Conquistas", pk=["id_conquista"], auto=True,
        colunas=[col("id_pacote", "Pacote", "fk", ref="pacote_conquistas"),
                 col("nome", "Nome"),
                 col("descricao", "Descrição", "area"),
                 col("gamerscore", "Gamerscore", "int")]),
    "item_biblioteca": dict(
        titulo="Biblioteca (itens)", pk=["id_item"], auto=True,
        colunas=[col("id_usuario", "Usuário", "fk", ref="usuario"),
                 col("id_jogo_plataforma", "Jogo / plataforma", "fk", ref="jogo_plataforma"),
                 col("status", "Status", "escolha", opcoes=STATUS, padrao="QUERO_JOGAR"),
                 col("horas_jogadas", "Horas jogadas", "num", padrao=0.0),
                 col("data_adicao", "Data de adição", "data", obrigatorio=False,
                     padrao="hoje")]),
    "desbloqueio": dict(
        titulo="Desbloqueios", pk=["id_item", "id_conquista"], auto=False,
        colunas=[col("id_item", "Item da biblioteca", "fk", ref="item_biblioteca"),
                 col("id_conquista", "Conquista", "fk", ref="conquista"),
                 col("data_hora", "Data e hora", "datahora", padrao="agora")]),
    "recomendacao": dict(
        titulo="Recomendações", pk=["id_recomendacao"], auto=True,
        colunas=[col("id_usuario", "Usuário", "fk", ref="usuario"),
                 col("data_geracao", "Data de geração", "datahora", obrigatorio=False,
                     padrao="agora"),
                 col("modelo_ia", "Modelo de IA")]),
    "recomendacao_jogo": dict(
        titulo="Jogos recomendados", pk=["id_recomendacao", "id_jogo"], auto=False,
        colunas=[col("id_recomendacao", "Recomendação", "fk", ref="recomendacao"),
                 col("id_jogo", "Jogo", "fk", ref="jogo"),
                 col("posicao", "Posição", "int"),
                 col("justificativa", "Justificativa", "area")]),
}
