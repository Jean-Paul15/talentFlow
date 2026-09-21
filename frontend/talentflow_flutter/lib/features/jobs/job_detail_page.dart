import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/favorites/favorite_toggle_button.dart';
import '../../core/jobs/source_label.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';

class JobDetailPage extends StatelessWidget {
  const JobDetailPage({super.key, required this.token, required this.job});

  final String token;
  final Map<String, dynamic> job;

  Future<void> _openUrl() async {
    final raw = (job['sourceUrl'] ?? '').toString().trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  int _scorePercent(dynamic score) {
    if (score is! num) return 0;
    if (score <= 1) return (score * 100).round().clamp(0, 100);
    return score.round().clamp(0, 100);
  }

  @override
  Widget build(BuildContext context) {
    final title = (job['title'] ?? '').toString();
    final company = (job['company'] ?? '').toString();
    final location = (job['location'] ?? '').toString();
    final contractType = (job['contractType'] ?? '').toString();
    final sourceName = sourceLabel((job['sourceName'] ?? '').toString());
    final postedDate = (job['postedDate'] ?? '').toString();
    final salary = (job['salary'] ?? '').toString();
    final description = (job['description'] ?? job['summary'] ?? '').toString();
    final scorePercent = _scorePercent(job['score']);

    final metaLine = <String>[
      company,
      location,
      contractType,
    ].where((e) => e.isNotEmpty).join(' · ');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Détail offre'),
        actions: <Widget>[
          FavoriteToggleButton(token: token, job: job),
          const SizedBox(width: 8),
        ],
      ),
      body: Container(
        decoration: AppTheme.appBackground,
        child: Column(
          children: <Widget>[
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
                children: <Widget>[
                  TfReveal(
                    delay: const Duration(milliseconds: 40),
                    child: TfCard(
                      variant: TfCardVariant.compact,
                      padding: const EdgeInsets.all(16),
                      child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            if (sourceName.isNotEmpty) _Tag(label: sourceName),
                            if (sourceName.isNotEmpty && postedDate.isNotEmpty)
                              const SizedBox(width: 6),
                            if (postedDate.isNotEmpty)
                              _Tag(
                                label: postedDate,
                                icon: PhosphorIconsRegular.calendar,
                              ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          title,
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                fontSize: 24,
                                height: 1.12,
                                letterSpacing: -0.5,
                              ),
                        ),
                        if (metaLine.isNotEmpty) ...<Widget>[
                          const SizedBox(height: 6),
                          Text(
                            metaLine,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  color: AppTheme.inkSoft,
                                  fontSize: 13,
                                ),
                          ),
                        ],
                        const SizedBox(height: 16),
                        Row(
                          children: <Widget>[
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color:
                                    (scorePercent >= 70
                                            ? AppTheme.success
                                            : scorePercent >= 40
                                            ? AppTheme.warning
                                            : AppTheme.danger)
                                        .withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: <Widget>[
                                  Icon(
                                    PhosphorIconsBold.chartDonut,
                                    size: 16,
                                    color: scorePercent >= 70
                                        ? AppTheme.success
                                        : scorePercent >= 40
                                        ? AppTheme.warning
                                        : AppTheme.danger,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Match $scorePercent%',
                                    style: TextStyle(
                                      color: scorePercent >= 70
                                          ? AppTheme.success
                                          : scorePercent >= 40
                                          ? AppTheme.warning
                                          : AppTheme.danger,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 14,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (salary.isNotEmpty) ...<Widget>[
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 8,
                                ),
                                decoration: BoxDecoration(
                                  color: AppTheme.mist,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: <Widget>[
                                    const Icon(
                                      PhosphorIconsRegular.money,
                                      size: 15,
                                      color: AppTheme.inkSoft,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      salary,
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelMedium
                                          ?.copyWith(color: AppTheme.inkSoft),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TfReveal(
                    delay: const Duration(milliseconds: 90),
                    child: TfCard(
                      variant: TfCardVariant.compact,
                      padding: const EdgeInsets.all(14),
                      child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Icon(
                              PhosphorIconsBold.lightbulb,
                              size: 14,
                              color: AppTheme.inkSoft,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Pourquoi cette offre ?',
                              style: Theme.of(context).textTheme.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        ..._buildReasons(
                          context,
                          scorePercent: scorePercent,
                          location: location,
                          contractType: contractType,
                          salary: salary,
                        ),
                      ],
                    ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TfReveal(
                    delay: const Duration(milliseconds: 140),
                    child: TfCard(
                      variant: TfCardVariant.compact,
                      padding: const EdgeInsets.all(14),
                      child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Icon(
                              PhosphorIconsBold.article,
                              size: 14,
                              color: AppTheme.inkSoft,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Description',
                              style: Theme.of(context).textTheme.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          description.isEmpty
                              ? 'Aucune description détaillée disponible.'
                              : description,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(fontSize: 13.5, height: 1.55),
                        ),
                      ],
                    ),
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: AppTheme.cardBorder)),
              ),
              child: SafeArea(
                top: false,
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _openUrl,
                    icon: const Icon(
                      PhosphorIconsBold.arrowSquareOut,
                      size: 14,
                    ),
                    label: const Text('Postuler maintenant'),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildReasons(
    BuildContext context, {
    required int scorePercent,
    required String location,
    required String contractType,
    required String salary,
  }) {
    final reasons = <String>[
      if (scorePercent >= 70)
        'Le score de matching est solide pour ton profil.',
      if (location.isNotEmpty)
        'Localisation compatible avec ton ciblage actuel.',
      if (contractType.isNotEmpty) 'Type de contrat: $contractType.',
      if (salary.isNotEmpty) 'Fourchette salariale affichée: $salary.',
    ];

    if (reasons.isEmpty) {
      return <Widget>[
        Text(
          'Aucune synthèse métier disponible pour cette offre.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppTheme.inkSoft),
        ),
      ];
    }

    return reasons.map((reason) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              margin: const EdgeInsets.only(top: 5),
              width: 5,
              height: 5,
              decoration: const BoxDecoration(
                color: AppTheme.teal,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                reason,
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontSize: 13, height: 1.4),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }
}

class _Tag extends StatelessWidget {
  const _Tag({required this.label, this.icon});

  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.mist,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 12, color: AppTheme.inkSoft),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: AppTheme.inkSoft,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
