import 'package:flutter/material.dart';

import 'home_page_snapshot_action_plan_panel.dart';
import 'home_page_snapshot_overview_panel.dart';
import 'home_page_snapshot_targeting_panel.dart';
import 'home_page_snapshot_watchlist_panel.dart';

class HomeSnapshotLayout extends StatelessWidget {
  const HomeSnapshotLayout({
    super.key,
    required this.recoDateLabel,
    required this.hasRecommendation,
    required this.latestMode,
    required this.latestLlmStatus,
    required this.latestSummary,
    required this.latestReason,
    required this.atsSummary,
    required this.watchlistQueries,
    required this.actionPlan,
    required this.headlineMissing,
    required this.preferredRolesMissing,
    required this.locationMissing,
    required this.countryMissing,
    required this.onNavigateToSearch,
    required this.onNavigateToProfile,
  });

  final String recoDateLabel;
  final bool hasRecommendation;
  final String latestMode;
  final String latestLlmStatus;
  final String latestSummary;
  final String latestReason;
  final String atsSummary;
  final List<String> watchlistQueries;
  final List<String> actionPlan;
  final bool headlineMissing;
  final bool preferredRolesMissing;
  final bool locationMissing;
  final bool countryMissing;
  final VoidCallback onNavigateToSearch;
  final VoidCallback onNavigateToProfile;

  @override
  Widget build(BuildContext context) {
    final left = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        HomeSnapshotOverviewPanel(
          recoDateLabel: recoDateLabel,
          hasRecommendation: hasRecommendation,
          latestMode: latestMode,
          latestLlmStatus: latestLlmStatus,
          latestSummary: latestSummary,
          latestReason: latestReason,
          atsSummary: atsSummary,
        ),
        const SizedBox(height: 14),
        HomeSnapshotWatchlistPanel(
          watchlistQueries: watchlistQueries,
          onNavigateToSearch: onNavigateToSearch,
        ),
      ],
    );

    final right = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        HomeSnapshotActionPlanPanel(actionPlan: actionPlan),
        const SizedBox(height: 14),
        HomeSnapshotTargetingPanel(
          headlineMissing: headlineMissing,
          preferredRolesMissing: preferredRolesMissing,
          locationMissing: locationMissing,
          countryMissing: countryMissing,
          onNavigateToProfile: onNavigateToProfile,
        ),
      ],
    );

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final wide = constraints.maxWidth >= 980;
        if (wide) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: left),
              const SizedBox(width: 16),
              Expanded(child: right),
            ],
          );
        }
        return Column(
          children: <Widget>[left, const SizedBox(height: 14), right],
        );
      },
    );
  }
}
