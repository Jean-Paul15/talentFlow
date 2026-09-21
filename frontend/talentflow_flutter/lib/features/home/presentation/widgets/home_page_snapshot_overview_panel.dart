import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeSnapshotOverviewPanel extends StatelessWidget {
  const HomeSnapshotOverviewPanel({
    super.key,
    required this.recoDateLabel,
    required this.hasRecommendation,
    required this.latestMode,
    required this.latestLlmStatus,
    required this.latestSummary,
    required this.latestReason,
    required this.atsSummary,
  });

  final String recoDateLabel;
  final bool hasRecommendation;
  final String latestMode;
  final String latestLlmStatus;
  final String latestSummary;
  final String latestReason;
  final String atsSummary;

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          TfSectionHeader(
            title: 'Dernière lecture du profil',
            subtitle: recoDateLabel.isEmpty
                ? 'Aucune recommandation récente enregistrée.'
                : 'Dernière recommandation sauvegardée le $recoDateLabel.',
          ),
          const SizedBox(height: 14),
          if (!hasRecommendation)
            const TfEmptyState(
              title: 'Aucune analyse encore lancée',
              message:
                  'Colle un CV ou importe un fichier pour obtenir un diagnostic, des offres crédibles et un vrai plan d’action.',
              icon: Icons.psychology_alt_outlined,
            )
          else ...<Widget>[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                TfPill(
                  label: latestMode == 'no_match'
                      ? 'Aucun match crédible'
                      : 'Match crédible',
                  color: latestMode == 'no_match'
                      ? const Color(0xFFFFF3CD)
                      : const Color(0xFFDDF7E8),
                  foreground: latestMode == 'no_match'
                      ? const Color(0xFF7C5E10)
                      : AppTheme.success,
                  icon: latestMode == 'no_match'
                      ? Icons.warning_amber_outlined
                      : Icons.verified_outlined,
                ),
                if (latestLlmStatus.isNotEmpty)
                  TfPill(
                    label: latestLlmStatus.replaceAll('_', ' '),
                    icon: Icons.smart_toy_outlined,
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              latestSummary.isNotEmpty
                  ? latestSummary
                  : 'Le dernier diagnostic est prêt à être relancé dans l’historique.',
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: AppTheme.ink),
            ),
            if (latestReason.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              TfCallout(
                title: 'Signal important',
                message: latestReason,
                icon: Icons.track_changes_outlined,
                color: AppTheme.warning,
              ),
            ],
            if (atsSummary.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              TfCallout(
                title: 'Lecture ATS-lite',
                message: atsSummary,
                icon: Icons.rule_folder_outlined,
              ),
            ],
          ],
        ],
      ),
    );
  }
}
