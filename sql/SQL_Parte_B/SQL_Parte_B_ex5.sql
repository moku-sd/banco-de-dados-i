CREATE SCHEMA sql_parte_b_ex5;

SET search_path TO sql_parte_b_ex5;

-- Cria tabelas
CREATE TABLE perfil (
codigo integer PRIMARY KEY,
descricao varchar(50),
custo_hora decimal
);
CREATE TABLE atividade_colaborador (
cod_colaborador integer,
cod_atividade integer,
perc_colaboracao integer,
PRIMARY KEY(cod_colaborador,cod_atividade)
);
CREATE TABLE colaborador (
codigo integer PRIMARY KEY,
nome varchar(50),
cod_perfil integer,
FOREIGN KEY(cod_perfil) REFERENCES perfil (codigo)
);
CREATE TABLE projeto (
codigo integer PRIMARY KEY,
descricao varchar(50)
);
CREATE TABLE categoria (
codigo integer PRIMARY KEY,
descricao varchar(50)
);
CREATE TABLE atividade (
codigo integer PRIMARY KEY,
descricao varchar(50),
qtde_hora_prevista integer,
qtde_hora_total integer,
cod_projeto integer,
cod_categoria integer,
FOREIGN KEY(cod_projeto) REFERENCES projeto (codigo),
FOREIGN KEY(cod_categoria) REFERENCES categoria (codigo)
);
ALTER TABLE atividade_colaborador
ADD FOREIGN KEY(cod_colaborador) REFERENCES colaborador (codigo);
ALTER TABLE atividade_colaborador
ADD FOREIGN KEY(cod_atividade) REFERENCES atividade (codigo);

-- Consultas

-- 1. Colaboradores e perfis
SELECT
    c.codigo,
    c.nome,
    p.descricao AS perfil
FROM colaborador c
LEFT JOIN perfil p ON p.codigo = c.cod_perfil
ORDER BY c.codigo;

-- 2. Colaboradores Desenvolvedor
SELECT
    c.codigo,
    c.nome,
    p.descricao AS perfil
FROM colaborador c
JOIN perfil p ON p.codigo = c.cod_perfil
WHERE p.descricao = 'Desenvolvedor'
ORDER BY c.codigo;

-- 3. Colaboradores do projeto 1
SELECT DISTINCT
    c.codigo,
    c.nome
FROM colaborador c
JOIN atividade_colaborador ac ON ac.cod_colaborador = c.codigo
JOIN atividade a ON a.codigo = ac.cod_atividade
WHERE a.cod_projeto = 1
ORDER BY c.codigo;

-- 4. Projetos e quantidade de colaboradores
SELECT
    p.codigo,
    p.descricao,
    COUNT(DISTINCT ac.cod_colaborador) AS total_colaboradores
FROM projeto p
LEFT JOIN atividade a ON a.cod_projeto = p.codigo
LEFT JOIN atividade_colaborador ac ON ac.cod_atividade = a.codigo
GROUP BY p.codigo, p.descricao
ORDER BY p.codigo;

-- 5. Projetos cuja soma das horas gastas supera a prevista
SELECT
    p.codigo,
    p.descricao,
    SUM(a.qtde_hora_prevista) AS horas_previstas,
    SUM(a.qtde_hora_total) AS horas_gastas
FROM projeto p
JOIN atividade a ON a.cod_projeto = p.codigo
GROUP BY p.codigo, p.descricao
HAVING SUM(a.qtde_hora_total) > SUM(a.qtde_hora_prevista)
ORDER BY p.codigo;

-- 6. Projetos com custo final > 15% previsto
WITH custos_projeto AS (
    SELECT
        p.codigo,
        p.descricao,
        SUM(
            a.qtde_hora_prevista
            * (ac.perc_colaboracao / 100.0)
            * pf.custo_hora
        ) AS custo_previsto,
        SUM(
            a.qtde_hora_total
            * (ac.perc_colaboracao / 100.0)
            * pf.custo_hora
        ) AS custo_final
    FROM projeto p
    JOIN atividade a ON a.cod_projeto = p.codigo
    JOIN atividade_colaborador ac ON ac.cod_atividade = a.codigo
    JOIN colaborador c ON c.codigo = ac.cod_colaborador
    JOIN perfil pf ON pf.codigo = c.cod_perfil
    GROUP BY p.codigo, p.descricao
)
SELECT *
FROM custos_projeto
WHERE custo_final > custo_previsto * 1.15
ORDER BY codigo;

-- 7. Média de horas previstas e gastas, por categoria
SELECT
    cat.codigo,
    cat.descricao,
    AVG(a.qtde_hora_prevista) AS media_horas_previstas,
    AVG(a.qtde_hora_total) AS media_horas_gastas
FROM categoria cat
LEFT JOIN atividade a ON a.cod_categoria = cat.codigo
GROUP BY cat.codigo, cat.descricao
ORDER BY cat.codigo;

-- 8. Categorias com maior soma de horas gastas
WITH horas_categoria AS (
    SELECT
        cat.codigo,
        cat.descricao,
        SUM(a.qtde_hora_total) AS total_horas
    FROM categoria cat
    JOIN atividade a ON a.cod_categoria = cat.codigo
    GROUP BY cat.codigo, cat.descricao
)
SELECT *
FROM horas_categoria
WHERE total_horas = (
    SELECT MAX(total_horas)
    FROM horas_categoria
)
ORDER BY codigo;

-- 9. 5 categorias que mais consumiram horas
SELECT
    cat.codigo,
    cat.descricao,
    SUM(a.qtde_hora_total) AS total_horas
FROM categoria cat
JOIN atividade a ON a.cod_categoria = cat.codigo
GROUP BY cat.codigo, cat.descricao
ORDER BY total_horas DESC NULLS LAST, cat.codigo
LIMIT 5;