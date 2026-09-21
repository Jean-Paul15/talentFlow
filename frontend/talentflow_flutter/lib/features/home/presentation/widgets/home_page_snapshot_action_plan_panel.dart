import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeSnapshotActionPlanPanel extends StatelessWidget {
  const HomeSnapshotActionPlanPanel({super.key, required this.actionPlan});

  final List<String> actionPlan;

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const TfSectionHeader(
            title: 'Plan d’action 7 jours',
            subtitle:
                'Une trajectoire simple pour passer d’un CV correct à une candidature plus convaincante.',
          ),
          const SizedBox(height: 14),
          TfBulletGroup(
            title: 'Plan prioritaire',
            items: actionPlan,
            icon: Icons.event_note_outlined,
            emptyMessage:
                'Lance une analyse CV pour générer un plan d’action ciblé.',
          ),
        ],
      ),
    );
  }
}
