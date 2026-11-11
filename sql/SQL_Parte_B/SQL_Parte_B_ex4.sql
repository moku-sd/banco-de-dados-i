CREATE SCHEMA sql_parte_b_ex4;

SET search_path TO sql_parte_b_ex4;

-- Criar Tabelas

CREATE TABLE bar (
    cod_bar INTEGER PRIMARY KEY,
    endereco VARCHAR(200),
    nome VARCHAR(100)
);

CREATE TABLE mesa (
    cod_mesa INTEGER PRIMARY KEY,
    cod_bar INTEGER NOT NULL,
    FOREIGN KEY (cod_bar) REFERENCES bar (cod_bar)
);

CREATE TABLE nota (
    cod_nota INTEGER PRIMARY KEY,
    data TIMESTAMP,
    cod_mesa INTEGER NOT NULL,
    FOREIGN KEY (cod_mesa) REFERENCES mesa (cod_mesa)
);

CREATE TABLE produto (
    cod_produto INTEGER PRIMARY KEY,
    descricao VARCHAR(100),
    valor NUMERIC(10,2)
);

CREATE TABLE garcom (
    cod_garcom INTEGER PRIMARY KEY,
    nome VARCHAR(100)
);

CREATE TABLE pedido (
    cod_nota INTEGER,
    cod_produto INTEGER,
    cod_garcom INTEGER NOT NULL,
    valor NUMERIC(10,2),
    quantidade INTEGER,
    PRIMARY KEY (cod_nota, cod_produto),
    FOREIGN KEY (cod_nota) REFERENCES nota (cod_nota),
    FOREIGN KEY (cod_produto) REFERENCES produto (cod_produto),
    FOREIGN KEY (cod_garcom) REFERENCES garcom (cod_garcom)
);

-- Popular BD

INSERT INTO bar (cod_bar, endereco, nome)
VALUES
    (1, 'Rua A, 100', 'Bar do Controle'),
    (2, 'Rua B, 200', 'Bar do Respawn');

INSERT INTO mesa (cod_mesa, cod_bar)
VALUES (1, 1), (2, 1), (3, 2);

INSERT INTO garcom (cod_garcom, nome)
VALUES (1, 'Manuel'), (2, 'Zeferino'), (3, 'Mateus');

INSERT INTO produto (cod_produto, descricao, valor)
VALUES
    (1, 'Suco', 10.00),
    (2, 'Porção de batatas', 20.00);

INSERT INTO nota (cod_nota, data, cod_mesa)
VALUES
    (1, '2026-10-05 19:00:00', 1),
    (2, '2026-10-10 20:00:00', 2),
    (3, '2026-10-15 21:00:00', 3);

INSERT INTO pedido (
    cod_nota, cod_produto, cod_garcom, valor, quantidade
)
VALUES
    (1, 1, 1, 10.00, 3),
    (1, 2, 1, 20.00, 1),
    (2, 2, 2, 20.00, 3),
    (3, 1, 2, 10.00, 4);

-- Consultas

-- Garçons, total de pedidos, despesas e 15% em Outubro
WITH pedidos_do_mes AS (
    SELECT p.*
    FROM pedido p
    JOIN nota n ON n.cod_nota = p.cod_nota
    WHERE n.data >= '2026-10-01'
      AND n.data < '2026-11-01'
)
SELECT
    g.cod_garcom,
    g.nome,
    COUNT(p.cod_nota) AS total_pedidos,
    COALESCE(SUM(p.valor * p.quantidade), 0) AS total_despesas,
    ROUND(
        COALESCE(SUM(p.valor * p.quantidade), 0) * 0.15,
        2
    ) AS valor_a_receber
FROM garcom g
LEFT JOIN pedidos_do_mes p ON p.cod_garcom = g.cod_garcom
GROUP BY g.cod_garcom, g.nome
ORDER BY g.cod_garcom;

-- Faturamento, ordem DEC, descontando 15%
SELECT
    b.cod_bar,
    b.nome,
    ROUND(
        COALESCE(SUM(p.valor * p.quantidade), 0) * 0.85,
        2
    ) AS faturamento
FROM bar b
LEFT JOIN mesa m ON m.cod_bar = b.cod_bar
LEFT JOIN nota n ON n.cod_mesa = m.cod_mesa
LEFT JOIN pedido p ON p.cod_nota = n.cod_nota
GROUP BY b.cod_bar, b.nome
ORDER BY faturamento DESC;