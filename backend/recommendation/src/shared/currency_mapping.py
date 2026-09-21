"""
Mapping pays → devise ISO 4217 et devises supportées.
"""

COUNTRY_CURRENCY_MAP = {
    "togo": "XOF",
    "benin": "XOF",
    "burkina faso": "XOF",
    "côte d'ivoire": "XOF",
    "mali": "XOF",
    "niger": "XOF",
    "senegal": "XOF",
    "guinea-bissau": "XOF",
    "france": "EUR",
    "germany": "EUR",
    "spain": "EUR",
    "italy": "EUR",
    "usa": "USD",
    "united states": "USD",
    "canada": "CAD",
    "uk": "GBP",
    "united kingdom": "GBP",
    "morocco": "MAD",
    "algeria": "DZD",
    "tunisia": "TND",
}

SUPPORTED_CURRENCIES = [
    "XOF",
    "EUR",
    "USD",
    "GBP",
    "CAD",
    "MAD",
    "DZD",
    "TND",
]
