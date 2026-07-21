-- DuckDB schema for the European trade network.
-- Populated from Python via src/eu_trade_network/db.py.

CREATE TABLE IF NOT EXISTS nodes (
    iso3          TEXT PRIMARY KEY,
    name          TEXT,
    grp           TEXT,          -- 'EU' or 'Partner'
    out_strength  DOUBLE,        -- total exports (thousand USD)
    in_strength   DOUBLE,        -- total imports (thousand USD)
    degree        INTEGER,       -- total unique trade partners
    betweenness   DOUBLE,        -- weighted (distance = 1/value)
    betweenness_u DOUBLE,        -- unweighted (pure topology)
    eigenvector   DOUBLE,
    pagerank      DOUBLE,
    community     INTEGER
);

CREATE TABLE IF NOT EXISTS edges (
    exporter_iso3 TEXT,
    importer_iso3 TEXT,
    value_kusd    DOUBLE,        -- thousands of USD
    year          INTEGER,
    PRIMARY KEY (exporter_iso3, importer_iso3, year)
);

-- Convenience view: top exporters by total outgoing value.
CREATE OR REPLACE VIEW top_exporters AS
SELECT exporter_iso3,
       SUM(value_kusd) AS total_exports_kusd
FROM edges
GROUP BY exporter_iso3
ORDER BY total_exports_kusd DESC;
