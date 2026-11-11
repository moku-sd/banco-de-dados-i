-- =====================================================================
-- Suporte a embeddings (pgvector) - item 7f (IA generativa)
-- Executar APÓS 01_schema.sql.
-- ATENÇÃO: a dimensão do vetor (1536) deve ser a do modelo de embeddings
-- escolhido. Se trocar de modelo, recrie a coluna com a nova dimensão.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE jogo ADD COLUMN embedding vector(1536);

-- Com algumas dezenas de jogos a busca sequencial basta. Para volumes
-- maiores, um índice aproximado (HNSW, distância de cosseno) seria:
-- CREATE INDEX ix_jogo_embedding ON jogo USING hnsw (embedding vector_cosine_ops);
