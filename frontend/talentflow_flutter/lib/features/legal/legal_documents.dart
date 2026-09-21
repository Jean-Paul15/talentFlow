import 'package:flutter/material.dart';

enum LegalDocumentType {
  termsOfUse,
  privacyPolicy,
}

class LegalDocumentSection {
  const LegalDocumentSection({
    required this.title,
    required this.body,
  });

  final String title;
  final List<String> body;
}

class LegalDocumentContent {
  const LegalDocumentContent({
    required this.type,
    required this.title,
    required this.summary,
    required this.lastUpdatedLabel,
    required this.sections,
  });

  final LegalDocumentType type;
  final String title;
  final String summary;
  final String lastUpdatedLabel;
  final List<LegalDocumentSection> sections;
}

LegalDocumentContent legalDocumentOf(LegalDocumentType type) {
  switch (type) {
    case LegalDocumentType.termsOfUse:
      return const LegalDocumentContent(
        type: LegalDocumentType.termsOfUse,
        title: 'Conditions d’utilisation',
        summary:
            'Les règles qui encadrent l’usage de TalentFlow, les responsabilités de chacun et les limites du service.',
        lastUpdatedLabel: 'Mise à jour: 3 avril 2026',
        sections: <LegalDocumentSection>[
          LegalDocumentSection(
            title: '1. Objet du service',
            body: <String>[
              'TalentFlow aide à analyser un CV, trouver des offres pertinentes, suivre des recommandations et piloter un plan d’action candidature.',
              'Le service fournit une aide à la décision. Il ne garantit ni entretien, ni embauche, ni résultat commercial auprès d’un recruteur.',
            ],
          ),
          LegalDocumentSection(
            title: '2. Compte utilisateur',
            body: <String>[
              'Tu es responsable des informations fournies à l’inscription et de la confidentialité de ton compte.',
              'Tu t’engages à ne pas utiliser l’application pour diffuser du contenu illicite, trompeur, offensant ou portant atteinte aux droits d’autrui.',
            ],
          ),
          LegalDocumentSection(
            title: '3. Usage autorisé',
            body: <String>[
              'Tu peux utiliser TalentFlow pour préparer tes candidatures, améliorer ton profil et consulter les opportunités proposées.',
              'Toute tentative d’extraction massive, d’automatisation abusive, de contournement technique ou de dégradation du service peut entraîner une suspension.',
            ],
          ),
          LegalDocumentSection(
            title: '4. Contenus importés',
            body: <String>[
              'Tu restes responsable des documents et textes que tu importes, y compris leur exactitude et leur légitimité.',
              'N’importe que ce soit ton propre CV ou un document autorisé, tu dois disposer des droits nécessaires pour l’utiliser dans l’application.',
            ],
          ),
          LegalDocumentSection(
            title: '5. Recommandations et IA',
            body: <String>[
              'Les analyses, scores et recommandations sont générés automatiquement à partir de tes données et des offres disponibles.',
              'Ces résultats peuvent contenir des approximations et doivent être relus avant toute décision importante.',
            ],
          ),
          LegalDocumentSection(
            title: '6. Disponibilité du service',
            body: <String>[
              'Nous faisons le nécessaire pour assurer un accès stable au service, mais des interruptions, opérations de maintenance ou limites techniques peuvent survenir.',
              'Le service peut évoluer, être enrichi ou ajusté sans préavis quand cela améliore la qualité, la sécurité ou la conformité.',
            ],
          ),
          LegalDocumentSection(
            title: '7. Propriété intellectuelle',
            body: <String>[
              'L’interface, les contenus produits par TalentFlow, la structure du service et ses éléments de marque restent protégés.',
              'Tu peux utiliser les résultats pour ta recherche d’emploi, mais tu ne peux pas reproduire ou redistribuer l’application comme si elle t’appartenait.',
            ],
          ),
          LegalDocumentSection(
            title: '8. Responsabilité',
            body: <String>[
              'TalentFlow est fourni en l’état, avec une obligation de moyens raisonnable et non une garantie absolue de performance.',
              'Chaque utilisateur reste décisionnaire final sur les candidatures envoyées, les modifications de CV et les actions entreprises.',
            ],
          ),
        ],
      );
    case LegalDocumentType.privacyPolicy:
      return const LegalDocumentContent(
        type: LegalDocumentType.privacyPolicy,
        title: 'Politique de confidentialité',
        summary:
            'Comment TalentFlow collecte, utilise, protège et conserve les données liées au compte, au CV et à l’activité de candidature.',
        lastUpdatedLabel: 'Mise à jour: 3 avril 2026',
        sections: <LegalDocumentSection>[
          LegalDocumentSection(
            title: '1. Données collectées',
            body: <String>[
              'Nous traitons les informations de compte nécessaires au fonctionnement du service: nom, email, préférences de profil, historique d’analyse et favoris.',
              'Quand tu importes un CV, le contenu du document, ses métadonnées utiles et les résultats d’analyse associés peuvent être traités pour produire les recommandations.',
            ],
          ),
          LegalDocumentSection(
            title: '2. Finalités du traitement',
            body: <String>[
              'Les données servent à authentifier l’utilisateur, personnaliser le matching, conserver l’historique, améliorer les résultats et générer des rapports cohérents.',
              'Certaines données techniques peuvent aussi être utilisées pour la sécurité, le diagnostic d’erreurs, la prévention d’abus et l’amélioration de la qualité de service.',
            ],
          ),
          LegalDocumentSection(
            title: '3. Base de fonctionnement',
            body: <String>[
              'Les traitements principaux sont nécessaires pour exécuter le service demandé par l’utilisateur.',
              'Quand un traitement complémentaire est introduit, il doit rester proportionné à l’usage métier attendu dans TalentFlow.',
            ],
          ),
          LegalDocumentSection(
            title: '4. Conservation',
            body: <String>[
              'Les données sont conservées pendant la durée utile au fonctionnement du compte, au suivi des analyses et à la continuité du service.',
              'Certaines sauvegardes techniques et journaux peuvent être conservés plus longtemps pour des besoins de sécurité, de reprise ou d’audit.',
            ],
          ),
          LegalDocumentSection(
            title: '5. Partage et sous-traitance',
            body: <String>[
              'Certaines données peuvent transiter par des services techniques nécessaires au traitement, à l’hébergement, au stockage ou à l’analyse automatique.',
              'Ce partage reste limité à ce qui est nécessaire pour faire fonctionner TalentFlow et sécuriser ses opérations.',
            ],
          ),
          LegalDocumentSection(
            title: '6. Sécurité',
            body: <String>[
              'Nous mettons en place des mesures techniques et organisationnelles raisonnables pour protéger les comptes, documents importés, bases de données et journaux associés.',
              'Aucune mesure ne garantit un risque nul, mais tout incident significatif doit être traité avec un niveau d’attention adapté.',
            ],
          ),
          LegalDocumentSection(
            title: '7. Tes droits',
            body: <String>[
              'Tu peux demander l’accès, la rectification ou la suppression des données liées à ton compte, dans la limite des contraintes légales et techniques applicables.',
              'Tu peux également demander une limitation de certains traitements quand cela est compatible avec la continuité du service.',
            ],
          ),
          LegalDocumentSection(
            title: '8. Évolution de la politique',
            body: <String>[
              'Cette politique peut évoluer si le service, l’infrastructure ou les exigences de conformité changent.',
              'La version affichée dans l’application fait foi pour l’état le plus récent des engagements présentés.',
            ],
          ),
        ],
      );
  }
}

String legalDocumentButtonLabel(LegalDocumentType type) {
  switch (type) {
    case LegalDocumentType.termsOfUse:
      return 'Conditions d’utilisation';
    case LegalDocumentType.privacyPolicy:
      return 'Politique de confidentialité';
  }
}

IconData legalDocumentIcon(LegalDocumentType type) {
  switch (type) {
    case LegalDocumentType.termsOfUse:
      return Icons.gavel_rounded;
    case LegalDocumentType.privacyPolicy:
      return Icons.verified_user_outlined;
  }
}
