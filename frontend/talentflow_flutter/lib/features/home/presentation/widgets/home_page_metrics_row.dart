import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeMetricsRow extends StatelessWidget {
  const HomeMetricsRow({
    super.key,
    required this.overallScore,
    required this.readinessLabel,
    required this.recommendationMode,
    required this.totalResults,
    required this.profileCompleteness,
    required this.favoriteCount,
  });

  final int overallScore;
  final String readinessLabel;
  final String recommendationMode;
  final int totalResults;
  final int profileCompleteness;
  final int favoriteCount;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 14,
      runSpacing: 14,
      children: <Widget>[
        SizedBox(
          width: 250,
          child: TfScoreCard(
            label: 'Alignement actuel',
            score: overallScore,
            caption: readinessLabel,
            color: AppTheme.teal,
          ),
        ),
        SizedBox(
          width: 250,
          child: TfMetricCard(
            label: 'offres crédibles',
            value: recommendationMode == 'no_match'
                ? '0'
                : totalResults.toString(),
            icon: Icons.travel_explore_outlined,
            accent: AppTheme.coral,
          ),
        ),
        SizedBox(
          width: 250,
          child: TfMetricCard(
            label: 'profil complété',
            value: '$profileCompleteness%',
            icon: Icons.account_circle_outlined,
            accent: AppTheme.gold,
          ),
        ),
        SizedBox(
          width: 250,
          child: TfMetricCard(
            label: 'offres en veille',
            value: '$favoriteCount',
            icon: Icons.favorite_border,
            accent: AppTheme.success,
          ),
        ),
      ],
    );
  }
}
