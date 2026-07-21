-- RQ2: size and total internal trade of each detected community.
SELECT
    community,
    COUNT(*)                               AS n_countries,
    STRING_AGG(iso3, ', ' ORDER BY out_strength DESC) AS members,
    ROUND(SUM(out_strength) / 1e6, 1)      AS community_exports_busd
FROM nodes
GROUP BY community
ORDER BY community_exports_busd DESC;
