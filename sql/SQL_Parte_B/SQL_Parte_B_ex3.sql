CREATE SCHEMA sql_parte_b_ex3;

SET search_path TO sql_parte_b_ex3;

-- Ciar Tabelas

CREATE TABLE fornecedor (
    cod_fornecedor INTEGER PRIMARY KEY,
    nome VARCHAR(50)
);

CREATE TABLE produto (
    cod_produto INTEGER PRIMARY KEY,
    descricao VARCHAR(50)
);

CREATE TABLE fornecedor_produto (
    cod_fornecedor INTEGER,
    cod_produto INTEGER,
    valor DOUBLE PRECISION,
    PRIMARY KEY (cod_fornecedor, cod_produto),
    FOREIGN KEY (cod_fornecedor)
        REFERENCES fornecedor (cod_fornecedor),
    FOREIGN KEY (cod_produto)
        REFERENCES produto (cod_produto)
);

-- Popular BD

INSERT INTO fornecedor (cod_fornecedor, nome)
VALUES
    (1, 'Fornecedor A'),
    (2, 'Fornecedor B');

INSERT INTO produto (cod_produto, descricao)
VALUES
    (1, 'Controle'),
    (2, 'Headset');

INSERT INTO fornecedor_produto (cod_fornecedor, cod_produto, valor)
VALUES
    (1, 1, 200.00),
    (1, 2, 100.00),
    (2, 1, 80.00),
    (2, 2, 100.00);

-- Consultas

SELECT f.nome
FROM fornecedor f
JOIN fornecedor_produto fp
    ON fp.cod_fornecedor = f.cod_fornecedor
GROUP BY f.cod_fornecedor, f.nome
HAVING AVG(fp.valor) > 100;