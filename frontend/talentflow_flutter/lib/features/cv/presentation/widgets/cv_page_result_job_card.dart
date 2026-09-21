import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/favorites/favorite_toggle_button.dart';
import 'package:talentflow_flutter/core/jobs/source_label.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';
import 'package:talentflow_flutter/features/jobs/job_detail_page.dart';

class CvResultJobCard extends StatelessWidget {
  const CvResultJobCard({
    super.key,
    required this.index,
    required this.token,
    required this.job,
    required this.why,
    required this.cvImprovement,
    required this.onOpenUrl,
  });

  final int index;
  final String token;
  final Map<String, dynamic> job;
  final String why;
  final String cvImprovement;
  final Future<void> Function(String?) onOpenUrl;

  @override
  Widget build(BuildContext context) {
    final url = (job['sourceUrl'] ?? '').toString();
    final summary = (job['summary'] ?? '').toString();

    return TfReveal(
      delay: Duration(milliseconds: 40 * index),
      child: Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TfPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  if (sourceLabel((job['sourceName'] ?? '').toString())
                      .isNotEmpty)
                    TfPill(
                      label: sourceLabel((job['sourceName'] ?? '').toString()),
                      color: const Color(0xFFFDEBD2),
                      foreground: const Color(0xFF8A5B12),
                    ),
                  if ((job['postedDate'] ?? '').toString().isNotEmpty)
                    TfPill(
                      label: (job['postedDate'] ?? '').toString(),
                      icon: Icons.schedule,
                    ),
                  if ((job['score'] ?? '').toString().isNotEmpty)
                    TfPill(
                      label: 'Score ${job['score']}',
                      color: const Color(0xFFDDF7E8),
                      foreground: AppTheme.success,
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                (job['title'] ?? '').toString(),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  height: 1.02,
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  if ((job['company'] ?? '').toString().isNotEmpty)
                    Chip(label: Text((job['company'] ?? '').toString())),
                  if ((job['location'] ?? '').toString().isNotEmpty)
                    Chip(label: Text((job['location'] ?? '').toString())),
                  if ((job['contractType'] ?? '').toString().isNotEmpty)
                    Chip(label: Text((job['contractType'] ?? '').toString())),
                ],
              ),
              if (summary.isNotEmpty) ...<Widget>[
                const SizedBox(height: 10),
                Text(
                  summary,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppTheme.inkSoft,
                  ),
                ),
              ],
              if (why.isNotEmpty || cvImprovement.isNotEmpty) ...<Widget>[
                const SizedBox(height: 12),
                TfCallout(
                  title: why.isNotEmpty
                      ? why
                      : 'Pourquoi cette offre remonte',
                  message: cvImprovement.isNotEmpty
                      ? cvImprovement
                      : 'Le moteur la considère comme une opportunité crédible.',
                  icon: Icons.workspace_premium_outlined,
                  color: AppTheme.coral,
                ),
              ],
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => JobDetailPage(token: token, job: job),
                        ),
                      );
                    },
                    icon: const Icon(Icons.visibility_outlined),
                    label: const Text('Voir le détail'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: url.isEmpty ? null : () => onOpenUrl(url),
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('Ouvrir l’offre'),
                  ),
                  FavoriteToggleButton(token: token, job: job),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
