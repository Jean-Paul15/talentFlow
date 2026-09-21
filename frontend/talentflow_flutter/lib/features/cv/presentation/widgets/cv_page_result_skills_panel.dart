import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvResultSkillsPanel extends StatelessWidget {
  const CvResultSkillsPanel({super.key, required this.skills});

  final List<String> skills;

  @override
  Widget build(BuildContext context) {
    if (skills.isEmpty) return const SizedBox.shrink();
    return TfReveal(
      delay: const Duration(milliseconds: 130),
      child: TfPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const TfSectionHeader(
              title: 'Compétences détectées',
              subtitle:
                  'Signaux extraits directement du CV avant la synthèse finale.',
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: skills
                  .take(18)
                  .map((String skill) => Chip(label: Text(skill)))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
}
