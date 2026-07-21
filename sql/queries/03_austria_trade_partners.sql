-- RQ1 detail: Austria's largest export destinations and import origins.
WITH exports AS (
    SELECT importer_iso3 AS partner, value_kusd AS exports_kusd
    FROM edges WHERE exporter_iso3 = 'AUT'
),
imports AS (
    SELECT exporter_iso3 AS partner, value_kusd AS imports_kusd
    FROM edges WHERE importer_iso3 = 'AUT'
)
SELECT
    COALESCE(e.partner, i.partner)         AS partner,
    ROUND(COALESCE(e.exports_kusd, 0) / 1e6, 2) AS exports_busd,
    ROUND(COALESCE(i.imports_kusd, 0) / 1e6, 2) AS imports_busd
FROM exports e
FULL OUTER JOIN imports i ON e.partner = i.partner
ORDER BY (COALESCE(e.exports_kusd, 0) + COALESCE(i.imports_kusd, 0)) DESC
LIMIT 15;
