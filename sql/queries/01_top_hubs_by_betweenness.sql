-- RQ1: rank economies by structural centrality; flag where Austria lands.
SELECT
    ROW_NUMBER() OVER (ORDER BY betweenness DESC) AS rank,
    iso3,
    name,
    grp,
    ROUND(betweenness, 4)          AS betweenness,
    ROUND(out_strength / 1e6, 1)   AS exports_busd,
    pagerank
FROM nodes
ORDER BY betweenness DESC;
