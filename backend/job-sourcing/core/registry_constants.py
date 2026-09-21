# Constantes d'orchestration du registre de sites
# Priorites, crons, labels et frequences

# Priorites d'orchestration Airflow
# Fenetres batch cible:
# - mini refresh midi: ~13h
# - fenetre longue: 18h -> 06h
PRIORITY_HIGH = 1       # rafraichissement frequent dans les fenetres
PRIORITY_MEDIUM = 2     # rafraichissement intermediaire
PRIORITY_LOW = 3        # desactivee par defaut
PRIORITY_NIGHTLY = 4    # crawl complet nocturne

CRON_MAP = {
    PRIORITY_HIGH: "0 0,2,4,13,18,20,22 * * *",
    PRIORITY_MEDIUM: "10 0,2,4,18,22 * * *",
    PRIORITY_LOW: "40 13 * * *",
    PRIORITY_NIGHTLY: "0 1 * * *",
}

PRIORITY_LABELS = {
    PRIORITY_HIGH: "Haute (13h + fenetre 18h-06h)",
    PRIORITY_MEDIUM: "Moyenne (18h, 22h, 00h, 02h, 04h)",
    PRIORITY_LOW: "Basse (desactivee par defaut)",
    PRIORITY_NIGHTLY: "Nocturne (crawl complet a 01h)",
}

FREQUENCY_LABELS = {
    PRIORITY_HIGH: "7 runs / jour",
    PRIORITY_MEDIUM: "5 runs / jour",
    PRIORITY_LOW: "1 fois par jour",
    PRIORITY_NIGHTLY: "1 fois par nuit",
}

SCHEDULE_HOURS = {
    PRIORITY_HIGH: ["00:00", "02:00", "04:00", "13:00", "18:00", "20:00", "22:00"],
    PRIORITY_MEDIUM: ["00:10", "02:10", "04:10", "18:10", "22:10"],
    PRIORITY_LOW: ["13:40"],
    PRIORITY_NIGHTLY: ["01:00"],
}
