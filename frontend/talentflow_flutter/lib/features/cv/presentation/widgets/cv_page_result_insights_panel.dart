import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvResultInsightsPanel extends StatelessWidget {
  const CvResultInsightsPanel({
    super.key,
    required this.strengths,
    required this.gaps,
    required this.matchedKeywords,
    required this.missingKeywords,
    required this.suggestions,
    required this.actions,
    required this.skills,
    required this.scoreExplanation,
    required this.offerPlaybooks,
  });

  final List<String> strengths;
  final List<String> gaps;
  final List<String> matchedKeywords;
  final List<String> missingKeywords;
  final List<String> suggestions;
  final List<String> actions;
  final List<String> skills;
  final String scoreExplanation;
  final List<Map<String, dynamic>> offerPlaybooks;

  @override
  Widget build(BuildContext context) {
    return TfReveal(
      delay: const Duration(milliseconds: 40),
      child: TfPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const TfSectionHeader(
              title: 'Lecture premium du CV',
              subtitle:
                  'On sépare ce qui te sert, ce qui manque, et l’action qui fait avancer ta candidature.',
            ),
            const SizedBox(height: 14),
            if (scoreExplanation.trim().isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: TfCallout(
                  title: 'Progression de score',
                  message: scoreExplanation,
                  icon: Icons.show_chart,
                  color: AppTheme.teal,
                ),
              ),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: <Widget>[
                SizedBox(
                  width: 360,
                  child: TfBulletGroup(
                    title: 'Forces à conserver',
                    items: strengths.isNotEmpty
                        ? strengths
                        : skills.take(5).toList(),
                    icon: Icons.check_circle_outline,
                    emptyMessage:
                        'Le moteur n’a pas encore extrait de forces explicites.',
                  ),
                ),
                SizedBox(
                  width: 360,
                  child: TfBulletGroup(
                    title: 'Gaps à corriger',
                    items: gaps,
                    icon: Icons.build_circle_outlined,
                    emptyMessage: 'Aucun gap majeur remonté.',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: <Widget>[
                SizedBox(
                  width: 360,
                  child: TfBulletGroup(
                    title: 'Mots-clés déjà alignés',
                    items: matchedKeywords,
                    icon: Icons.radar,
                    emptyMessage:
                        'Le CV reste trop générique; il faut préciser davantage les outils et le métier visé.',
                  ),
                ),
                SizedBox(
                  width: 360,
                  child: TfBulletGroup(
                    title: 'Mots-clés manquants',
                    items: missingKeywords,
                    icon: Icons.priority_high_outlined,
                    emptyMessage:
                        'Peu de mots-clés critiques manquent sur les offres retenues.',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TfBulletGroup(
              title: 'Conseils de reformulation',
              items: suggestions.isNotEmpty ? suggestions : actions,
              icon: Icons.edit_note_outlined,
              emptyMessage:
                  'Les conseils apparaîtront ici après la prochaine analyse.',
            ),
            if (offerPlaybooks.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              ...offerPlaybooks.take(3).map((Map<String, dynamic> playbook) {
                final rewrite =
                    playbook['rewrite'] is Map<String, dynamic>
                        ? playbook['rewrite'] as Map<String, dynamic>
                        : const <String, dynamic>{};
                final evidence =
                    (playbook['evidence'] as List<dynamic>? ?? const <dynamic>[])
                        .map((dynamic e) => e.toString())
                        .where((String e) => e.trim().isNotEmpty)
                        .toList();
                final bullets =
                    (rewrite['experienceBullets'] as List<dynamic>? ??
                            const <dynamic>[])
                        .map((dynamic e) => e.toString())
                        .where((String e) => e.trim().isNotEmpty)
                        .toList();

                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: TfCallout(
                    title: (playbook['title'] ?? '').toString().trim().isEmpty
                        ? 'Playbook offre'
                        : 'Playbook : ${(playbook['title'] ?? '').toString()}',
                    message: <String>[
                      if ((playbook['whyFit'] ?? '').toString().trim().isNotEmpty)
                        'Pourquoi cette offre : ${(playbook['whyFit'] ?? '').toString()}',
                      if ((playbook['cvDelta'] ?? '').toString().trim().isNotEmpty)
                        'Ce que tu dois changer : ${(playbook['cvDelta'] ?? '').toString()}',
                      if ((rewrite['targetTitle'] ?? '').toString().trim().isNotEmpty)
                        'Titre CV proposé : ${(rewrite['targetTitle'] ?? '').toString()}',
                      if ((rewrite['targetSummary'] ?? '').toString().trim().isNotEmpty)
                        'Résumé proposé : ${(rewrite['targetSummary'] ?? '').toString()}',
                      if (bullets.isNotEmpty)
                        'Expériences à reformuler : ${bullets.join(' • ')}',
                      if (evidence.isNotEmpty)
                        'Preuves utilisées : ${evidence.join(' • ')}',
                    ].join('\n'),
                    icon: Icons.track_changes_outlined,
                    color: AppTheme.coral,
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
