# Constantes pour l'extraction de competences
# Patterns regex et listes de mots-cles FR/EN

# Technologies courantes (anglais/international)
TECH_PATTERNS = [
    # Langages de programmation
    r"\b(Python|Java|JavaScript|TypeScript|PHP|Ruby|Go|Rust|C\+\+|C#|Kotlin|Swift|Scala|Dart|R)\b",
    # Frameworks Frontend
    r"\b(React|Angular|Vue\.?js|Next\.?js|Nuxt|Svelte|jQuery|Bootstrap|Tailwind)\b",
    # Frameworks Backend
    r"\b(Node\.?js|Django|Flask|FastAPI|Spring Boot|Laravel|Express|NestJS|Rails)\b",
    # Cloud et DevOps
    r"\b(Docker|Kubernetes|AWS|Azure|GCP|Terraform|Ansible|Jenkins|GitLab CI|GitHub Actions)\b",
    # Bases de donnees
    r"\b(PostgreSQL|MySQL|MariaDB|MongoDB|Redis|Elasticsearch|Cassandra|DynamoDB|SQLite)\b",
    # Big Data
    r"\b(Spark|Hadoop|Kafka|Airflow|Flink|Hive|Presto|Databricks|Snowflake)\b",
    # IA/ML
    r"\b(TensorFlow|PyTorch|Scikit-learn|Keras|Pandas|NumPy|Hugging Face|OpenCV|MLflow)\b",
    # Outils
    r"\b(Git|Jira|Confluence|Figma|Postman|VS Code|IntelliJ|Linux|Windows Server)\b",
    # Methodologies
    r"\b(Agile|Scrum|Kanban|DevOps|CI/CD|TDD|BDD|Microservices|REST|GraphQL|API)\b",
]

# Soft skills francais
SOFT_SKILLS_FR = [
    "communication", "leadership", "travail en equipe", "travail d'equipe",
    "autonomie", "rigueur", "organisation", "adaptabilite", "flexibilite",
    "creativite", "gestion du stress", "negociation", "esprit d'analyse",
    "resolution de problemes", "proactivite", "dynamisme", "motivation",
    "collaboration", "esprit d'equipe", "relationnel", "polyvalence",
    "sens du service", "ecoute", "pedagogie", "curiosite", "initiative"
]

# Soft skills anglais
SOFT_SKILLS_EN = [
    "communication", "leadership", "teamwork", "autonomy", "rigor",
    "organization", "adaptability", "flexibility", "creativity",
    "stress management", "negotiation", "analytical skills", "problem solving",
    "proactivity", "dynamism", "motivation", "collaboration", "initiative"
]

# Patterns experience (FR + EN)
EXPERIENCE_PATTERNS = [
    r"(\d+)\s*(?:ans?|annees?)\s*(?:d['\s]?experience)?",
    r"experience\s*(?:de\s*)?(\d+)\s*ans?",
    r"minimum\s*(\d+)\s*ans?",
    r"(\d+)\s*years?\s*(?:of\s*)?experience",
    r"at\s*least\s*(\d+)\s*years?",
]

# Mapping niveau education (du plus haut au plus bas)
EDUCATION_MAPPING = {
    r"doctorat|phd|these": "Doctorat",
    r"bac\s*\+\s*5|master|ingenieur|m2|mba": "Bac+5",
    r"bac\s*\+\s*3|licence|bachelor|l3": "Bac+3",
    r"bac\s*\+\s*2|bts|dut|deug": "Bac+2",
    r"baccalaureat|niveau\s*bac\b": "Bac",
}
