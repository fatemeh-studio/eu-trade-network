"""Approximate capital (or centroid) coordinates for the analysis country set.

Coordinates are ``(latitude, longitude)`` in WGS84 decimal degrees.
"""

from __future__ import annotations

# Capital-city approx. for EU-27 + partners in ``config.COUNTRIES``.
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "AUT": (48.2082, 16.3738),  # Vienna
    "BEL": (50.8503, 4.3517),  # Brussels
    "BGR": (42.6977, 23.3219),  # Sofia
    "HRV": (45.8150, 15.9819),  # Zagreb
    "CYP": (35.1856, 33.3823),  # Nicosia
    "CZE": (50.0755, 14.4378),  # Prague
    "DNK": (55.6761, 12.5683),  # Copenhagen
    "EST": (59.4370, 24.7536),  # Tallinn
    "FIN": (60.1699, 24.9384),  # Helsinki
    "FRA": (48.8566, 2.3522),  # Paris
    "DEU": (52.5200, 13.4050),  # Berlin
    "GRC": (37.9838, 23.7275),  # Athens
    "HUN": (47.4979, 19.0402),  # Budapest
    "IRL": (53.3498, -6.2603),  # Dublin
    "ITA": (41.9028, 12.4964),  # Rome
    "LVA": (56.9496, 24.1052),  # Riga
    "LTU": (54.6872, 25.2797),  # Vilnius
    "LUX": (49.6116, 6.1319),  # Luxembourg
    "MLT": (35.8989, 14.5146),  # Valletta
    "NLD": (52.3676, 4.9041),  # Amsterdam
    "POL": (52.2297, 21.0122),  # Warsaw
    "PRT": (38.7223, -9.1393),  # Lisbon
    "ROU": (44.4268, 26.1025),  # Bucharest
    "SVK": (48.1486, 17.1077),  # Bratislava
    "SVN": (46.0569, 14.5058),  # Ljubljana
    "ESP": (40.4168, -3.7038),  # Madrid
    "SWE": (59.3293, 18.0686),  # Stockholm
    "GBR": (51.5074, -0.1278),  # London
    "CHE": (46.9480, 7.4474),  # Bern
    "NOR": (59.9139, 10.7522),  # Oslo
    "USA": (38.9072, -77.0369),  # Washington, D.C.
    "CHN": (39.9042, 116.4074),  # Beijing
    "TUR": (39.9334, 32.8597),  # Ankara
    "RUS": (55.7558, 37.6173),  # Moscow
    "JPN": (35.6762, 139.6503),  # Tokyo
}
