import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvResultActionPlanPanel extends StatelessWidget {
  const CvResultActionPlanPanel({
    super.key,
    required this.actionPlan,
    required this.actions,
  });

  final List<String> actionPlan;
  final List<String> actions;

  @override
  Widget build(BuildContext context) {
    return TfReveal(
      delay: const Duration(milliseconds: 90),
      child: TfPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const TfSectionHeader(
              title: 'Plan d’action 7 jours',
              subtitle:
                  'Le minimum utile pour transformer le diagnostic en exécution.',
            ),
            const SizedBox(height: 14),
            TfBulletGroup(
              title: 'Exécution recommandée',
              items: actionPlan.isNotEmpty ? actionPlan : actions,
              icon: Icons.event_note_outlined,
              emptyMessage:
                  'Le plan s’affichera ici après la prochaine analyse.',
            ),
          ],
        ),
      ),
    );
  }
}
