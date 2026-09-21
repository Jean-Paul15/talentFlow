import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeSnapshotWatchlistPanel extends StatelessWidget {
  const HomeSnapshotWatchlistPanel({
    super.key,
    required this.watchlistQueries,
    required this.onNavigateToSearch,
  });

  final List<String> watchlistQueries;
  final VoidCallback onNavigateToSearch;

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const TfSectionHeader(
            title: 'Relances à surveiller',
            subtitle:
                'Quelques pistes rapides à relancer depuis tes préférences, favoris et dernières recherches.',
          ),
          const SizedBox(height: 14),
          if (watchlistQueries.isEmpty)
            const TfEmptyState(
              title: 'Aucune relance intelligente pour l’instant',
              message:
                  'Complète le profil et lance au moins une analyse pour alimenter les suggestions.',
              icon: Icons.radar,
            )
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: watchlistQueries
                  .map(
                    (String value) => ActionChip(
                      avatar: const Icon(Icons.bolt, size: 18),
                      label: Text(value),
                      onPressed: onNavigateToSearch,
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }
}
