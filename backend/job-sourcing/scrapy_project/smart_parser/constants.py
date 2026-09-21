# Constantes du moteur d'extraction intelligent
# Mots-cles indicateurs et selecteurs generiques

# Mots-cles indicateurs d'offre d'emploi (fr + en)
JOB_KEYWORDS = {
    "title": [
        "poste propos", "intitul", "titre du poste", "job title",
        "position", "offre", "recrutement",
    ],
    "company": [
        "entreprise", "societe", "recruteur", "employeur",
        "company", "organization", "cabinet", "structure",
    ],
    "location": [
        "lieu", "localisation", "ville", "region", "pays",
        "location", "adresse", "base a", "poste a",
    ],
    "contract": [
        "contrat", "type de contrat", "cdi", "cdd", "stage",
        "freelance", "interim", "temps partiel", "temps plein",
        "contract", "employment type",
    ],
    "experience": [
        "experience", "niveau d'experience", "annees",
        "debutant", "senior", "junior", "confirme",
    ],
    "education": [
        "etudes", "diplome", "formation", "niveau d'etudes",
        "bac", "licence", "master", "education",
    ],
    "salary": [
        "salaire", "remuneration", "salary", "compensation",
        "fcfa", "xof", "eur", "usd",
    ],
    "skills": [
        "competences", "skills", "qualifications", "requis",
        "profil recherche", "aptitudes", "savoir-faire",
    ],
    "sector": [
        "secteur", "domaine", "metier", "sector", "industry",
        "activite",
    ],
    "work_schedule": [
        "temps", "horaire", "duree", "regime", "schedule",
        "temps complet", "temps partiel", "full time", "part time",
        "teletravail", "remote", "presentiel", "hybride",
    ],
    "apply": [
        "postuler", "candidater", "apply", "soumettre",
        "envoyer cv", "deposer candidature",
    ],
}

# Selecteurs CSS generiques (du plus specifique au generique)
TITLE_SELECTORS = [
    "h1.entry-title::text", "h1.job-title::text", "h1.page-title::text",
    "h1::text", ".job-title::text", ".post-title::text",
    "h2.entry-title::text", ".position-title::text",
    ".job-header h1::text", ".job-listing-title::text",
    "[itemprop='title']::text", ".vacancy-title::text",
    ".offer-title::text", ".titre-offre::text",
]

COMPANY_SELECTORS = [
    ".company-name::text", ".employer-name::text", ".recruteur a::text",
    ".recruteur::text", ".company::text", ".company .value::text",
    ".job-company::text", "a[href*='recruteur']::text",
    ".entreprise::text", ".employeur::text",
    "[itemprop='hiringOrganization'] [itemprop='name']::text",
    "[data-employer]::attr(data-employer)",
    ".hiring-company::text", ".org-name::text",
    ".job-company-name::text", ".recruiter-name::text",
    "a[href*='employer']::text", "a[href*='company']::text",
    ".job-meta .company a::text", ".firm-name::text",
]

LOCATION_SELECTORS = [
    ".job-location::text", ".location::text", ".region::text",
    ".ville::text", "a[href*='localisation']::text",
    ".job-location .value::text",
    ".lieu::text", ".adresse::text",
    "[itemprop='addressLocality']::text",
    "[itemprop='addressRegion']::text",
    "[itemprop='jobLocation'] [itemprop='name']::text",
    ".city::text", ".area::text",
    "a[href*='location']::text", ".job-city::text",
    ".workplace-location::text", ".posting-location::text",
]

DESCRIPTION_SELECTORS = [
    ".job-description", ".description-offre", ".entry-content",
    ".job_description", ".item-page", "article .content",
    ".post-content", ".job-details", "#job-description",
    ".detail-annonce", ".job-single-content",
    ".offre-details", ".annonce-content", ".job-body",
    "[itemprop='description']", ".description-poste",
    ".vacancy-description", ".role-description",
    ".job-detail-content", ".job-info",
    ".posting-description", ".opportunity-details",
    "#job-details", ".job-text", ".job-summary",
]

CONTRACT_SELECTORS = [
    ".job-type::text", ".type-contrat::text", ".contract-type::text",
    "a[href*='contrat']::text", ".employment-type::text",
    "[itemprop='employmentType']::text",
    "[itemprop='employmentType']::attr(content)",
    ".nature-contrat::text", ".work-type::text",
    ".job-category::text", ".job-employment-type::text",
    "a[href*='job-type']::text", ".type-emploi::text",
]

DATE_SELECTORS = [
    "time::attr(datetime)", "time::text", ".date-publication::text",
    ".post-date::text", ".date-posted::text", ".published-date::text",
    "meta[property='article:published_time']::attr(content)",
    "[itemprop='datePosted']::attr(content)",
    "[itemprop='datePosted']::text", ".posting-date::text",
    ".date-added::text", ".job-date::text",
]

# Indicateurs heuristiques pour valider une page d'offre
JOB_INDICATORS = [
    r'emploi', r'offre', r'poste', r'recrutement', r'recrute',
    r'mission', r'profil recherch', r'candidat', r'competence',
    r'experience', r'contrat', r'cdi', r'cdd', r'stage',
    r'salaire', r'cv', r'postuler', r'job', r'career',
    r'vacancy', r'hiring', r'apply', r'qualifica',
    r'internship', r'apprentice', r'deadline', r'submit',
    r'requirements?', r'responsibilities', r'duties',
    r'opportunit', r'position', r'opening', r'recruit',
    r'remunera', r'compensation', r'benefits',
    r'freelance', r'consultant', r'volunteer',
]

# Carte pays -> mots-cles pour detection geographique
COUNTRY_MAP = {
    "Togo": ["togo", "lome", "lom\u00e9", "kara", "sokode", "atakpame", "tsevie"],
    "Senegal": ["senegal", "dakar", "thies", "saint-louis", "s\u00e9n\u00e9gal"],
    "Cote d'Ivoire": [
        "cote d'ivoire", "abidjan", "ivory coast", "c\u00f4te d'ivoire",
        "bouake", "yamoussoukro", "korhogo", "san pedro",
    ],
    "Cameroun": ["cameroun", "douala", "yaounde", "cameroon", "yaound\u00e9"],
    "Burkina Faso": ["burkina", "ouagadougou", "bobo-dioulasso"],
    "Benin": ["benin", "cotonou", "porto-novo", "b\u00e9nin", "parakou"],
    "Mali": ["mali", "bamako", "sikasso"],
    "Niger": ["niger", "niamey", "zinder", "maradi"],
    "Guinee": ["guinee", "conakry", "guinea", "guin\u00e9e"],
    "Congo": ["congo", "brazzaville", "kinshasa", "pointe-noire"],
    "Gabon": ["gabon", "libreville", "port-gentil"],
    "Tchad": ["tchad", "ndjamena", "chad", "n'djamena"],
    "Madagascar": ["madagascar", "antananarivo", "tananarive"],
    "RDC": ["rdc", "congo-kinshasa", "lubumbashi"],
    "Rwanda": ["rwanda", "kigali"],
    "Mauritanie": ["mauritanie", "nouakchott"],
    "Centrafrique": ["centrafrique", "bangui"],
    "Tunisie": ["tunisie", "tunis", "tunisia", "sfax", "sousse"],
    "Maroc": ["maroc", "casablanca", "rabat", "morocco", "marrakech", "fes", "tanger"],
    "Algerie": ["algerie", "alger", "algeria", "oran", "constantine"],
    "Kenya": ["kenya", "nairobi", "mombasa", "kisumu"],
    "Nigeria": ["nigeria", "lagos", "abuja", "port harcourt", "ibadan"],
    "Ghana": ["ghana", "accra", "kumasi", "tamale"],
    "Tanzanie": ["tanzanie", "tanzania", "dar es salaam", "dodoma"],
    "Ouganda": ["ouganda", "uganda", "kampala"],
    "Ethiopie": ["ethiopie", "ethiopia", "addis ababa", "addis-abeba"],
    "Afrique du Sud": ["south africa", "afrique du sud", "johannesburg", "cape town", "durban", "pretoria"],
    "Mozambique": ["mozambique", "maputo"],
    "Zambie": ["zambie", "zambia", "lusaka"],
    "Zimbabwe": ["zimbabwe", "harare"],
    "Egypte": ["egypte", "egypt", "cairo", "le caire", "alexandrie"],
    "Libye": ["libye", "libya", "tripoli"],
    "Soudan": ["soudan", "sudan", "khartoum"],
    "Sierra Leone": ["sierra leone", "freetown"],
    "Liberia": ["liberia", "monrovia"],
    "Togo-Diaspora": ["diaspora", "international"],
}

# Patterns URL indicateurs d'offre d'emploi
JOB_URL_PATTERNS = [
    r'/offre[s-]', r'/emploi[s-]', r'/job[s/]', r'/career',
    r'/recrutement', r'/vacancy', r'/poste', r'/annonce',
    r'/offer', r'/position', r'/hiring', r'/apply',
    r'/opportunit', r'post_type=job',
    r'/job-\d+', r'/offre-\d+', r'/listing/',
    r'/ci/emploi/', r'/tg/emploi/', r'/sn/emploi/',
    r'/cm/emploi/', r'/bf/emploi/', r'/bj/emploi/',
    r'/stage[s/]', r'/mission[s/]',
    r'/internship', r'/opening', r'/recruitment',
    r'/job-details', r'/job-view', r'/offre-details',
    r'/vacancies', r'/employ', r'/work/',
]

# Patterns URL de navigation a exclure
NAV_URL_PATTERNS = [
    r'/login', r'/register', r'/inscription', r'/contact',
    r'/about', r'/a-propos', r'/faq', r'/mentions',
    r'/politique', r'/privacy', r'/terms', r'/conditions',
    r'\.pdf$', r'\.jpg$', r'\.png$', r'facebook\.com',
    r'twitter\.com', r'linkedin\.com/share', r'mailto:',
    r'/wp-admin', r'/cart', r'/panier', r'/compte',
]
