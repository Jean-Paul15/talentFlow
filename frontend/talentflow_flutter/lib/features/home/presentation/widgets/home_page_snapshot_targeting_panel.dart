import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeSnapshotTargetingPanel extends StatelessWidget {
  const HomeSnapshotTargetingPanel({
    super.key,
    required this.headlineMissing,
    required this.preferredRolesMissing,
    required this.locationMissing,
    required this.countryMissing,
    required this.onNavigateToProfile,
  });

  final bool headlineMissing;
  final bool preferredRolesMissing;
  final bool locationMissing;
  final bool countryMissing;
  final VoidCallback onNavigateToProfile;

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const TfSectionHeader(
            title: 'Ciblage à compléter',
            subtitle:
                'Les champs les plus utiles pour améliorer le matching et réduire les faux résultats.',
          ),
          const SizedBox(height: 14),
          TfBulletGroup(
            title: 'Champs à renforcer',
            items: <String>[
              if (headlineMissing)
                'Ajoute une phrase de positionnement claire dans le profil.',
              if (preferredRolesMissing)
                'Définis 2 ou 3 rôles précis pour guider la recommandation.',
              if (locationMissing)
                'Renseigne ta localisation de recherche principale.',
              if (countryMissing)
                'Précise le pays prioritaire pour les opportunités.',
            ],
            icon: Icons.tune_outlined,
            emptyMessage:
                'Le profil est déjà bien renseigné. Tu peux surtout travailler le CV et les preuves.',
          ),
          const SizedBox(height: 14),
          OutlinedButton.icon(
            onPressed: onNavigateToProfile,
            icon: const Icon(Icons.person_outline),
            label: const Text('Compléter le profil'),
          ),
        ],
      ),
    );
  }
}
