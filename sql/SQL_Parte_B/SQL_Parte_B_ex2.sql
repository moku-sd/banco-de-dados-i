CREATE SCHEMA sql_parte_b_ex2;

SET search_path TO sql_parte_b_ex2;

-- Criando tabelas

CREATE TABLE livro (
    isbn VARCHAR(20) PRIMARY KEY,
    editora VARCHAR(100),
    titulo VARCHAR(200)
);

CREATE TABLE autor (
    cod_autor INTEGER PRIMARY KEY,
    nome VARCHAR(100)
);

CREATE TABLE palavra_chave (
    cod_plv_chave INTEGER PRIMARY KEY,
    descricao VARCHAR(100)
);

CREATE TABLE associado (
    cod_associado INTEGER PRIMARY KEY,
    nome VARCHAR(100),
    endereco VARCHAR(200)
);

CREATE TABLE exemplar (
    cod_exemplar INTEGER PRIMARY KEY,
    isbn VARCHAR(20),
    FOREIGN KEY (isbn) REFERENCES livro (isbn)
);

CREATE TABLE emprestimo (
    cod_exemplar INTEGER,
    cod_associado INTEGER,
    data_emprestimo TIMESTAMP,
    data_devolucao TIMESTAMP,
    PRIMARY KEY (
        cod_exemplar,
        cod_associado,
        data_emprestimo
    ),
    FOREIGN KEY (cod_exemplar)
        REFERENCES exemplar (cod_exemplar),
    FOREIGN KEY (cod_associado)
        REFERENCES associado (cod_associado)
);

-- Consultas

SELECT
    l.titulo,
    e.data_emprestimo,
    e.data_devolucao
FROM livro l
JOIN exemplar ex ON ex.isbn = l.isbn
JOIN emprestimo e ON e.cod_exemplar = ex.cod_exemplar
WHERE e.cod_associado = 1
  AND e.data_emprestimo >= DATE '2026-11-08' - INTERVAL '2 months'
  AND e.data_emprestimo < DATE '2026-11-08' + INTERVAL '1 day'
ORDER BY e.data_emprestimo DESC;

SELECT *
FROM livro
WHERE titulo LIKE '%Banco de Dados%';