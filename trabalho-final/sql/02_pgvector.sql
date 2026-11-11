-- =====================================================================
-- Suporte a embeddings (pgvector) - item 7f (IA generativa)
-- Executar APÓS 01_schema.sql.
-- A dimensão do vetor (768) corresponde ao modelo gemini-embedding-001 com
-- output_dimensionality=768. Se trocar de modelo, recrie a coluna.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE jogo ADD COLUMN embedding vector(768);

-- Detalhe de implementação (não faz parte do modelo lógico): endereço da imagem
-- de capa, usado apenas para exibição na interface. Pode ficar nulo.
ALTER TABLE jogo ADD COLUMN url_capa TEXT;

-- Com algumas dezenas de jogos a busca sequencial basta. Para volumes
-- maiores, um índice aproximado (HNSW, distância de cosseno) seria:
-- CREATE INDEX ix_jogo_embedding ON jogo USING hnsw (embedding vector_cosine_ops);
