# Sites d'Offres d'Emploi : Togo & International
## Analyse Complète pour Scraping & Architecture IA de Recrutement

---

## 🇹🇬 SITES TOGO (PRIORITÉ 1)

### 1. **Emploi.tg** - **URL** : https://www.emploi.tg/
- **Volume estimé** : ~500-1000 offres actives
- **Mise à jour** : Quotidienne
- **Structure** :
  - Offres bien structurées avec dates
  - Champs : Titre, Entreprise, Région (Lomé, Atakpamé, Dapaong, Kara, Sokodé)
  - Type de contrat visible (CDI, CDD, Stage)
  - Niveau d'études requis
- **Scraping** :
  - Structure HTML propre
  - Pas de JavaScript lourd
  - Pagination simple
  - Rate limiting possible (respecter 2-3 sec entre requêtes)
- **Priorité** : HAUTE

### 2. **EmploiTogo.com** - **URL** : https://emploitogo.com/
- **Volume estimé** : ~300-800 offres
- **Spécialité** : Offres gouvernementales + secteur privé
- **Structure** :
  - Focus sur appels d'offres et concours publics
  - Bonnes informations sur salaires et conditions
  - Email de contact : info@emploitogo.com
- **Scraping** :
  - Structure claire
  - Contenu texte facile à parser
  - Parfois des PDF à télécharger (utiliser PyPDF2)
- **Priorité** : HAUTE

### 3. **EmploiTogo.info** - **URL** : https://www.emploitogo.info/
- **Volume estimé** : ~200-500 offres
- **Spécialité** : Bourses, stages, séminaires de formation
- **Scraping** :
  - Site assez simple
  - Mélange d'actualités et d'offres (besoin de filtrage)
- **Priorité** : MOYENNE

### 4. **MiabeJob** - **URL** : https://miabejob.com/
- **Volume estimé** : ~400-700 offres
- **Spécialité** : Service RH + recrutement
- **Structure** :
  - Offres avec durées précises (ex: "juin 11, 2025 - décembre 28, 2025")
  - Types de contrat clairs (CDD/Mission, Stage)
  - Services d'audit RH (intéressant pour données contextuelles)
- **Scraping** :
  - Bon formatage des dates
  - Catégorisation claire
- **Priorité** : HAUTE

### 5. **ANPE Togo** (Agence Nationale Pour l'Emploi) - **URL** : https://anpetogo.org/
- **Volume estimé** : ~600-1200 offres
- **Type** : **OFFICIEL GOUVERNEMENTAL**
- **Avantages** :
  - Données fiables et vérifiées
  - Secteurs émergents et projets structurants
  - Grandes entreprises (Mairie de Lomé, BCEAO, etc.)
- **Scraping** :
  - Plateforme officielle (structure propre)
  - Authentification requise pour postuler (pas pour lire)
- **Priorité** : TRÈS HAUTE

### 6. **RMO Togo** (RMO JobCenter) - **URL** : https://www.rmo-jobcenter.com/fr/togo/offres-emploi.html
- **Volume estimé** : ~300-600 offres
- **Note** : Partie d'un réseau africain plus large
- **Scraping** :
  - Gestion de cookies (consentement requis)
  - Flux RSS disponible (excellent pour monitoring)
- **Priorité** : MOYENNE

---

## SITES AFRIQUE FRANCOPHONE (PRIORITÉ 2)

### 7. **AfricaWork** - **URL** : https://www.africawork.com/
- **Couverture** : 37 pays africains
- **Pays francophones** : Bénin, Burkina Faso, Côte d'Ivoire, Sénégal, Mali, Niger, Guinée, Cameroun, RDC, Gabon, Tchad, Togo, etc.
- **Volume estimé** : ~5000-10000 offres (tous pays)
- **Structure** :
  - Réseau décentralisé (un site par pays)
  - Executive Search + Middle Management
  - Filtres avancés (secteur, expérience, région)
- **Scraping** :
  - Architecture professionnelle
  - API potentielle (à investiguer)
  - Besoin de scraper chaque sous-domaine pays
- **Priorité** : TRÈS HAUTE

### 8. **Wiijob** - **URL** : https://wiijob.com/
- **Couverture** : Afrique francophone (focus Togo, Côte d'Ivoire, Sénégal)
- **Volume estimé** : ~3000-6000 offres
- **Spécialité** : Coaching carrière + offres d'emploi
- **Types de contrat** : CDD, CDI, Stage, Freelance
- **Scraping** :
  - Structure moderne et claire
  - Filtres par localisation et secteur
- **Priorité** : HAUTE

### 9. **SenJob** (Afrique de l'Ouest francophone) - **URL** : https://senjob.com/
- **Couverture** : Sénégal, Côte d'Ivoire, Burkina Faso, Mali, Niger, Guinée, Togo, Bénin
- **Volume estimé** : ~2000-4000 offres
- **Focus** : Dakar, Abidjan
- **Scraping** :
  - Structure simple
  - Bon pour jobs multi-pays
- **Priorité** : MOYENNE-HAUTE

### 10. **GoAfricaOnline Emploi** - **URL** : https://www.goafricaonline.com/emploi
- **Couverture** : Pan-africain (focus Bénin, Côte d'Ivoire, Guinée)
- **Volume estimé** : ~1500-3000 offres
- **Scraping** :
  - Structure assez basique
  - Qualité variable des annonces
- **Priorité** : MOYENNE

### 11. **JobAfrique** - **URL** : http://www.jobafrique.com/
- **Couverture** : Afrique francophone (25+ pays)
- **Volume estimé** : ~500-1000 offres
- **Note** : Site moins actif, mais réseau étendu
- **Scraping** :
  - Design ancien, structure moins propre
- **Priorité** : BASSE

### 12. **Fed Africa** - **URL** : https://www.fedafrica.com/
- **Type** : Cabinet de recrutement (approche directe)
- **Focus** : Middle & Top Management
- **Bureaux** : Paris (France) + Abidjan (Côte d'Ivoire)
- **Spécialité** : Cadres et dirigeants
- **Scraping** :
  - Offres qualitatives (moins de volume, meilleure qualité)
  - Peut nécessiter authentification
- **Priorité** : MOYENNE (haute qualité, faible volume)

---

## SITES INTERNATIONAUX (PRIORITÉ 3)

### 13. **LinkedIn** - **URL** : https://www.linkedin.com/jobs/
- **Volume estimé** : 180+ millions d'offres mondiales
- **Couverture Togo** : ~100-500 offres
- **Avantages** :
  - Réseau professionnel intégré
  - Données riches (profils entreprises, salaires)
  - Recommandations IA natives
- **Scraping** :
  - **TRÈS DIFFICILE** (anti-bot strict)
  - Requiert API officielle (LinkedIn Talent Solutions)
  - Coût : $5000+/an par siège recruteur
  - Alternative : Web scraping léger avec proxies rotatifs + respect strict des limites
- **Priorité** : HAUTE (utiliser API si budget disponible)

### 14. **Indeed** - **URL** : https://www.indeed.com/
- **Volume estimé** : 250+ millions d'offres mondiales
- **Couverture Togo** : ~200-800 offres (agrégateur)
- **Spécificité** : **Agrégateur de job boards**
  - Récolte automatiquement les offres d'autres sites
  - Donc scraper Indeed = obtenir contenu de multiples sources
- **Scraping** :
  - Anti-bot modéré (Cloudflare)
  - Possible avec Scrapy + rotating proxies
  - Risque de ban IP si trop agressif
  - Utiliser `scrapy-rotating-proxies` + `scrapy-user-agents`
- **Priorité** : TRÈS HAUTE (source agrégatrice précieuse)

### 15. **Glassdoor** - **URL** : https://www.glassdoor.com/
- **Volume estimé** : 24+ millions de visiteurs/mois
- **Spécialité** : Reviews entreprises + offres + salaires
- **Avantages UNIQUES** :
  - Avis d'employés (sentiment analysis)
  - Données salariales transparentes
  - Culture d'entreprise
- **Scraping** :
  - Anti-bot moyen (protection par Cloudflare)
  - Structure HTML exploitable
  - **VALEUR AJOUTÉE** : Enrichir les offres avec avis employés
- **Priorité** : HAUTE (pour enrichissement sémantique)

### 16. **Monster** - **URL** : https://www.monster.com/
- **Volume estimé** : 35+ millions de visiteurs/mois
- **Historique** : 25+ ans d'expérience (ancien leader)
- **Volume** : 29 CV uploadés/minute
- **Scraping** :
  - Structure accessible
  - UI jugée "vieillotte" par certains utilisateurs
  - Bon pour profils administratifs et juniors
- **Priorité** : MOYENNE (marché mature, déclin face à Indeed)

### 17. **ZipRecruiter** - **URL** : https://www.ziprecruiter.com/
- **Volume estimé** : 16+ millions de visiteurs/mois
- **Spécialité** : **AI-powered matching**
- **Avantages** :
  - Matching algorithmique avancé
  - Distribution automatique sur 100+ job boards
  - App mobile #1 rated (iOS & Android)
- **Scraping** :
  - Technologie anti-bot moderne
  - Possible mais nécessite proxies premium
- **Priorité** : MOYENNE-HAUTE (surtout USA, moins Afrique)

### 18. **CareerBuilder** - **URL** : https://www.careerbuilder.com/
- **Volume estimé** : 85+ millions de chercheurs d'emploi
- **Couverture** : 60+ marchés, 29 langues
- **Scraping** :
  - Structure relativement accessible
  - Déclin en popularité face à Indeed/LinkedIn
- **Priorité** : BASSE (focus USA, peu pertinent Afrique)

### 19. **France Travail** (ex-Pôle Emploi) - **URL** : https://candidat.francetravail.fr/offres/recherche?lieux=AFC
- **Couverture Afrique** : Offres pour Bénin, Côte d'Ivoire, Comores, etc.
- **Volume estimé Afrique** : ~500-1500 offres
- **Type** : Offres françaises avec missions Afrique
- **Scraping** :
  - API publique potentielle
  - Site officiel bien structuré
- **Priorité** : MOYENNE (profils internationaux)

### 20. **Jooble** - **URL** : https://fr.jooble.org/
- **Type** : Méta-moteur (agrégateur)
- **Volume** : 529,000+ offres (France + international)
- **Couverture Togo** : ~100-300 offres
- **Scraping** :
  - Structure simple
  - Agrégateur = risque de doublons avec autres sources
- **Priorité** : BASSE (redondant si Indeed déjà scrapé)

---

## RÉSUMÉ STRATÉGIQUE POUR VOTRE ARCHITECTURE

### Sites à Scraper EN PRIORITÉ (MVP)

| Rang | Site | Raison | Volume estimé |
|------|------|--------|---------------|
| 1 | **ANPE Togo** | Source officielle gouvernementale | 600-1200 |
| 2 | **Emploi.tg** | Leader local Togo | 500-1000 |
| 3 | **MiabeJob** | Données structurées + dates précises | 400-700 |
| 4 | **AfricaWork** | Réseau 37 pays, qualité haute | 5000-10000 |
| 5 | **Indeed** | Agrégateur mondial | 200-800 (Togo) |
| 6 | **Wiijob** | Coaching + offres Afrique | 3000-6000 |

**Total MVP** : ~10,000-20,000 offres actives

### Stack Technique Recommandée

```python
# Scrapy Configuration
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 2  # Respecter les serveurs
ROBOTSTXT_OBEY = True

# Anti-Ban
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
]

# Proxy Rotation (pour Indeed, LinkedIn)
ROTATING_PROXY_LIST = [
    'proxy1.example.com:8000',
    'proxy2.example.com:8000',
]

# Fingerprinting (Redis Cache)
import hashlib
def get_job_fingerprint(url, title, company):
    data = f"{url}|{title}|{company}".encode()
    return hashlib.sha256(data).hexdigest()
```

### Fréquence de Scraping Recommandée

| Type de site | Fréquence | Raison |
|--------------|-----------|--------|
| Sites Togo locaux | **2x/jour** | Faible volume, mises à jour fréquentes |
| AfricaWork, Wiijob | **1x/jour** | Volume moyen, turnover modéré |
| Indeed, LinkedIn | **3x/jour** | Agrégateurs, flux continu |
| Glassdoor (enrichissement) | **1x/semaine** | Pour reviews entreprises (pas offres) |

### Stratégie Anti-Duplication

```python
# Étape 1 : Fingerprint URL
hash_url = hashlib.sha256(job_url.encode()).hexdigest()
if redis_client.exists(f"job:url:{hash_url}"):
    return  # Skip

# Étape 2 : Fingerprint Sémantique (après scraping)
hash_content = hashlib.sha256(
    f"{title}|{company}|{location}".lower().encode()
).hexdigest()
if redis_client.exists(f"job:content:{hash_content}"):
    return  # Duplicate

# Étape 3 : Déduplication IA (MongoDB + Elasticsearch)
# Comparer vecteurs embeddings pour offres similaires
```

### Roadmap de Déploiement

**Phase 1 (Semaine 1-2) : Togo Only**
- Scraper ANPE + Emploi.tg + MiabeJob
- Pipeline MinIO → MongoDB → Elasticsearch
- Test matching basique

**Phase 2 (Semaine 3-4) : Afrique Francophone**
- Ajouter AfricaWork + Wiijob + SenJob
- Améliorer déduplication
- Premier RAG avec Llama 3

**Phase 3 (Mois 2) : International**
- Indeed + Glassdoor (avec proxies)
- Enrichissement avec reviews Glassdoor
- API Gateway NestJS + Auth Passport

**Phase 4 (Mois 3+) : Optimisation**
- LinkedIn via API officielle (si budget)
- Monitoring Grafana/Prometheus
- Scaling horizontal des spiders

---

## RECOMMANDATIONS SPÉCIFIQUES

### Pour Indeed
```bash
# Utiliser Scrapy avec rotation d'IP
pip install scrapy-rotating-proxies scrapy-fake-useragent

# Configuration
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_fake_useragent.middleware.RandomUserAgentMiddleware': 400,
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}
```

### Pour Glassdoor (Enrichissement)
```python
# Ne pas scraper les offres, mais les reviews pour enrichir
def enrich_company_data(company_name):
    glassdoor_data = scrape_glassdoor_reviews(company_name)
    return {
        'rating': glassdoor_data['rating'],
        'pros': glassdoor_data['pros_summary'],  # NLP summary
        'cons': glassdoor_data['cons_summary'],
        'culture_sentiment': sentiment_analysis(glassdoor_data['reviews'])
    }
```

### Pour LinkedIn
**Option 1 (Recommandée)** : API Officielle
- Coût : $5000-10000/an
- Fiable, légal, données riches

**Option 2 (Alternative)** : Web Scraping Léger
- Utiliser Selenium + undetected-chromedriver
- Limiter à 50 requêtes/jour/IP
- Proxies résidentiels premium

---

## POINTS D'ATTENTION LÉGAUX

### Conformité RGPD / Données Personnelles
- Scraper les **offres d'emploi** (données publiques) = OK
- Scraper les **CV/profils candidats** = INTERDIT sans consentement
- Glassdoor reviews = Zone grise (privilégier API si disponible)

### Respect des Terms of Service
- **LinkedIn** : TOS strictes, privilégier API
- **Indeed** : Autorise scraping modéré (respect rate limits)
- **Sites africains** : Généralement pas de TOS strictes

### Best Practices
1. Toujours inclure un `User-Agent` identifiable
2. Respecter `robots.txt`
3. Rate limiting : 1-3 sec entre requêtes
4. Offrir un contact email dans le User-Agent pour whitelisting

---

## MÉTRIQUES À TRACKER (Airflow + Grafana)

```python
# Dashboard Monitoring
metrics = {
    'jobs_scraped_today': 2847,
    'duplicate_rate': 0.23,  # 23% de doublons
    'scraping_failures': {
        'emploi_tg': 2,  # 2 échecs
        'indeed': 15,    # Rate limited
    },
    'storage_size_minio': '2.3 GB',
    'elasticsearch_docs': 18432,
    'llm_api_calls_today': 156,
    'avg_matching_latency': '87ms'
}
```

---

## CONCLUSION

Avec cette liste de 20 sites, vous disposez de :
- **~30,000-50,000 offres uniques** (après déduplication)
- **Couverture géographique** : Togo → Afrique francophone → International
- **Qualité variable** : Des offres locales authentiques aux postes internationaux
- **Diversité sectorielle** : Public, privé, ONG, startups, multinationales

**Votre architecture est parfaitement dimensionnée pour gérer ce volume** avec Elasticsearch, MinIO et le pipeline Airflow proposé. 
**Prochaines étapes** :
1. Développer spiders Scrapy pour Top 6 sites
2. Tester anti-duplication avec Redis
3. Valider stockage MinIO → MongoDB → Elasticsearch
4. Intégrer Llama 3 pour premier matching

Bonne chance pour le projet ! 