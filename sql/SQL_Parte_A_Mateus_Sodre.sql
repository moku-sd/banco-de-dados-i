-- EX1: Criar Schema e tabelas

CREATE SCHEMA IF NOT EXISTS sql_parte_a;

SET search_path TO sql_parte_a;

CREATE TABLE cliente (
    cod_cliente INTEGER PRIMARY KEY,
    nome VARCHAR(50),
    cidade VARCHAR(50),
    uf VARCHAR(2),
    endereco VARCHAR(50)
);

CREATE TABLE produto (
    cod_produto INTEGER PRIMARY KEY,
    qtde_estoque INTEGER,
    descricao VARCHAR(50),
    valor NUMERIC
);

CREATE TABLE nota (
    num_nota INTEGER PRIMARY KEY,
    data TIMESTAMP,
    num_parcela INTEGER,
    cod_cliente INTEGER,
    FOREIGN KEY (cod_cliente)
        REFERENCES cliente (cod_cliente)
);

CREATE TABLE nota_produto (
    num_nota INTEGER,
    cod_produto INTEGER,
    valor NUMERIC,
    qtde INTEGER,
    PRIMARY KEY (num_nota, cod_produto),
    FOREIGN KEY (num_nota)
        REFERENCES nota (num_nota),
    FOREIGN KEY (cod_produto)
        REFERENCES produto (cod_produto)
);

CREATE TABLE venda (
    num_nota INTEGER,
    data_vencto TIMESTAMP,
    data_pagto TIMESTAMP,
    multa_juro NUMERIC,
    valor NUMERIC,
    desconto NUMERIC,
    PRIMARY KEY (num_nota, data_vencto),
    FOREIGN KEY (num_nota)
        REFERENCES nota (num_nota)
);

-- EX2: Inserir dados

INSERT INTO cliente (cod_cliente, nome, cidade, uf, endereco)
VALUES
    (1, 'Mateus', 'Araranguá', 'SC', 'Rua das Flores, 100'),
    (2, 'Manuel', 'Florianópolis', 'SC', 'Rua das Palmeiras, 200'),
    (3, 'Zeferino', 'Rio de Janeiro', 'RJ', 'Rua do Sol, 300');

INSERT INTO produto (cod_produto, qtde_estoque, descricao, valor)
VALUES
	(1, 10, 'Xbox Series S', 2400.00),
	(2, 20, 'Controle Xbox', 400.00),
	(3, 30, 'Headset', 200.00),
	(4, 50, 'Jogo físico', 100.00);

INSERT INTO nota (num_nota, data, num_parcela, cod_cliente)
VALUES
	(1, '2026-09-01 10:00:00', 0, 1),
	(2, '2026-09-01 14:00:00', 2, 2),
	(3, '2026-09-10 15:30:00', 1, 3);

INSERT INTO nota_produto (num_nota, cod_produto, valor, qtde)
VALUES
	(1, 2, 400.00, 1),
	(1, 4, 100.00, 2),
	(2, 1, 2400.00, 1),
	(2, 3, 200.00, 1),
	(1, 3, 200.00, 2);

INSERT INTO venda (num_nota, data_vencto, data_pagto, multa_juro, valor, desconto)
VALUES
	(1, '2026-09-01 10:00:00', '2026-09-01 10:00:00', 0.00, 600.00, 30.00),
	(2, '2026-10-01 14:00:00', NULL, 0.00, 1300.00, 0.00),
	(2, '2026-10-31 14:00:00', NULL, 0.00, 1300.00, 0.00),
	(3, '2026-10-10 15:30:00', '2026-10-15 15:30:00', 8.00, 400.00, 0.00);

-- EX3: Consultas

-- Total de vendas por cliente por mes/ano
SELECT
	c.cod_cliente,
	c.nome,
	EXTRACT(YEAR FROM v.data_vencto) AS ano,
	EXTRACT(MONTH FROM v.data_vencto) AS mes,
	SUM(v.valor) AS total_vendas
FROM cliente c
JOIN nota n ON n.cod_cliente = c.cod_cliente
JOIN venda v ON v.num_nota = n.num_nota
GROUP BY
	c.cod_cliente,
	c.nome,
	EXTRACT(YEAR FROM v.data_vencto),
	EXTRACT(MONTH FROM v.data_vencto)
ORDER BY ano, mes, c.cod_cliente;

-- Total de vendas por estado
SELECT
	c.uf,
	SUM(v.valor) AS total_vendas
FROM cliente c
JOIN nota n ON n.cod_cliente = c.cod_cliente
JOIN venda v ON v.num_nota = n.num_nota
GROUP BY c.uf
ORDER BY c.uf;

-- Produto mais vendido por periodo
SELECT
	p.cod_produto,
	p.descricao,
	SUM(np.qtde) AS quantidade_vendida
FROM produto p
JOIN nota_produto np ON np.cod_produto = p.cod_produto
JOIN nota n ON n.num_nota = np.num_nota
WHERE n.data >= '2026-09-01'
	AND n.data < '2026-10-01'
GROUP BY p.cod_produto, p.descricao
HAVING SUM(np.qtde) = (
	SELECT SUM(np2.qtde)
	FROM nota_produto np2
	JOIN nota n2 ON n2.num_nota = np2.num_nota
	WHERE n2.data >= '2026-09-01'
		AND n2.data < '2026-10-01'
	GROUP BY np2.cod_produto
	ORDER BY SUM(np2.qtde) DESC
	LIMIT 1
	)
ORDER BY p.cod_produto;

-- Total por cliente em um periodo
SELECT
	c.cod_cliente,
	c.nome,
	SUM(
		v.valor
		+ COALESCE(v.multa_juro, 0)
		- COALESCE(v.desconto, 0)
	) AS total_recebido
FROM cliente c
JOIN nota n ON n.cod_cliente = c.cod_cliente
JOIN venda v ON v.num_nota = n.num_nota
WHERE v.data_pagto >= '2026-09-01'
	AND v.data_pagto < '2026-11-01'
GROUP BY c.cod_cliente, c.nome
ORDER BY c.cod_cliente;

-- Total a receber por cliente em um periodo
SELECT
	c.cod_cliente,
	c.nome,
	SUM(v.valor) AS total_a_receber
FROM cliente c
JOIN nota n ON n.cod_cliente = c.cod_cliente
JOIN venda v ON v.num_nota = n.num_nota
WHERE v.data_pagto IS NULL
	AND v.data_vencto >= '2026-10-01'
	AND v.data_vencto < '2026-11-01'
GROUP BY c.cod_cliente, c.nome
ORDER BY c.cod_cliente;
