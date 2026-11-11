SET search_path TO sql_parte_a;

CREATE VIEW vendas_por_produto AS
SELECT
	np.cod_produto,
	SUM(np.qtde) AS qtde_total
FROM nota_produto np
JOIN nota nt ON nt.num_nota = np.num_nota
WHERE nt.data >= '2026-09-01'
  AND nt.data < '2026-10-01'
GROUP BY np.cod_produto;

SELECT p.*
FROM produto p
JOIN vendas_por_produto vp
    ON vp.cod_produto = p.cod_produto
WHERE vp.qtde_total = (
    SELECT MAX(qtde_total)
    FROM vendas_por_produto
);