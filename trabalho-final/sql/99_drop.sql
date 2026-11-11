-- =====================================================================
-- Elimina todos os objetos criados por 01_schema.sql e 02_pgvector.sql.
-- A extensão "vector" é mantida instalada (inofensiva, reaproveitada
-- pela próxima criação).
-- =====================================================================
DROP VIEW IF EXISTS vw_auditoria_integridade;

DROP TABLE IF EXISTS
    recomendacao_jogo, recomendacao, desbloqueio, item_biblioteca,
    conquista, pacote_conquistas, jogo_plataforma, jogo_genero, jogo,
    plataforma, genero, publicadora, desenvolvedora, usuario
CASCADE;

DROP FUNCTION IF EXISTS fn_t1_desbloqueio_mesmo_jogo_plataforma();
DROP FUNCTION IF EXISTS fn_t1_protege_item();
DROP FUNCTION IF EXISTS fn_t1_protege_conquista();
DROP FUNCTION IF EXISTS fn_t1_protege_pacote();
DROP FUNCTION IF EXISTS fn_t2_data_hora_nao_futura();
DROP FUNCTION IF EXISTS fn_t3_gamerscore_conquista();
DROP FUNCTION IF EXISTS fn_t3_tipo_pacote();
DROP FUNCTION IF EXISTS fn_limite_gamerscore(VARCHAR);
