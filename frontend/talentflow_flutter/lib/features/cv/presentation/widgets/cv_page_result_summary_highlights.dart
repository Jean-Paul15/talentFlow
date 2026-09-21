import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvResultSummaryHighlights extends StatelessWidget {
  const CvResultSummaryHighlights({
    super.key,
    required this.mode,
    required this.llmLabel,
    required this.totalResults,
    required this.overallScore,
    required this.structureScore,
    required this.alignmentScore,
    required this.evidenceScore,
    required this.readiness,
    required this.experienceYears,
    required this.educationLevel,
  });

  final String mode;
  final String llmLabel;
  final int totalResults;
  final int overallScore;
  final int structureScore;
  final int alignmentScore;
  final int evidenceScore;
  final String readiness;
  final String experienceYears;
  final String educationLevel;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: <Widget>[
            TfPill(
              label: mode == 'no_match'
                  ? 'Aucun match crédible'
                  : 'Match crédible',
              color: mode == 'no_match'
                  ? const Color(0xFFFFF3CD)
                  : const Color(0xFFDDF7E8),
              foreground: mode == 'no_match'
                  ? const Color(0xFF7C5E10)
                  : AppTheme.success,
              icon: mode == 'no_match'
                  ? Icons.warning_amber_outlined
                  : Icons.verified_outlined,
            ),
            TfPill(label: llmLabel, icon: Icons.smart_toy_outlined),
            TfPill(
              label: '$totalResults offres retenues',
              icon: Icons.work_outline,
            ),
            if (experienceYears.isNotEmpty)
              TfPill(label: '$experienceYears ans', icon: Icons.timeline),
            if (educationLevel.isNotEmpty)
              TfPill(label: educationLevel, icon: Icons.school_outlined),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: <Widget>[
            _scoreCard(
              label: 'Score global',
              score: overallScore,
              caption: readiness,
              color: AppTheme.teal,
            ),
            _scoreCard(
              label: 'Structure CV',
              score: structureScore,
              caption: 'Lisibilité pour un tri initial',
              color: AppTheme.gold,
            ),
            _scoreCard(
              label: 'Alignement offres',
              score: alignmentScore,
              caption: 'Proximité avec les postes retenus',
              color: AppTheme.coral,
            ),
            _scoreCard(
              label: 'Preuves concrètes',
              score: evidenceScore,
              caption: 'Impact, chiffres, réalisations',
              color: AppTheme.success,
            ),
          ],
        ),
      ],
    );
  }

  Widget _scoreCard({
    required String label,
    required int score,
    required String caption,
    required Color color,
  }) {
    return SizedBox(
      width: 220,
      child: TfScoreCard(
        label: label,
        score: score,
        caption: caption,
        color: color,
      ),
    );
  }
}
