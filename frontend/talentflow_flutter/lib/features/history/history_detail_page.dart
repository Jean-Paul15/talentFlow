import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/history/recommendation_history_store.dart';
import '../../core/reports/report_download_button.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';
import '../jobs/job_detail_page.dart';

class HistoryDetailPage extends StatelessWidget {
  const HistoryDetailPage({
    super.key,
    required this.token,
    required this.entry,
  });

  final String token;
  final RecommendationHistoryEntry entry;

  Future<void> _openUrl(String? url) async {
    final raw = (url ?? '').trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  String _llmLabel() {
    if (entry.llmUsed) {
      return entry.llmStatus == 'used_cached'
          ? 'Assistant intelligent (cache)'
          : 'Assistant intelligent';
    }
    return entry.llmStatus == 'provider_error'
        ? 'Diagnostic de secours'
        : 'Synthèse structurée';
  }

  Map<String, dynamic>? _assistantStructured() => entry.assistantStructured;

  List<Map<String, dynamic>> _displayJobs() {
    final structured = _assistantStructured();
    if (structured == null) return entry.jobs;
    final mode = (structured['mode'] ?? '').toString();
    if (mode == 'no_match') {
      return const <Map<String, dynamic>>[];
    }
    final recommended =
        (structured['recommendedJobs'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    if (recommended.isEmpty) return entry.jobs;

    final byId = <String, Map<String, dynamic>>{
      for (final Map<String, dynamic> job in entry.jobs)
        (job['id'] ?? '').toString(): job,
    };
    final byUrl = <String, Map<String, dynamic>>{
      for (final Map<String, dynamic> job in entry.jobs)
        (job['sourceUrl'] ?? '').toString(): job,
    };

    final resolved = <Map<String, dynamic>>[];
    for (final Map<String, dynamic> item in recommended) {
      final jobId = (item['jobId'] ?? '').toString();
      final url = (item['url'] ?? '').toString();
      final resolvedJob = byId[jobId] ?? byUrl[url];
      if (resolvedJob != null) {
        resolved.add(resolvedJob);
      }
    }
    return resolved.isEmpty ? entry.jobs : resolved;
  }

  @override
  Widget build(BuildContext context) {
    final createdAt = DateTime.tryParse(entry.createdAtIso)?.toLocal();
    final assistantStructured = _assistantStructured();
    final atsLite = entry.atsLite;
    final displayJobs = _displayJobs();

    return Scaffold(
      appBar: AppBar(title: const Text('Détail analyse')),
      body: Container(
        decoration: AppTheme.appBackground,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: <Widget>[
            TfReveal(
              delay: const Duration(milliseconds: 40),
              child: TfPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    TfSectionHeader(
                      title: entry.queryUsed.isEmpty
                          ? 'Recommandation CV'
                          : entry.queryUsed,
                      subtitle: createdAt == null
                          ? entry.createdAtIso
                          : '${createdAt.day}/${createdAt.month}/${createdAt.year} ${createdAt.hour}:${createdAt.minute.toString().padLeft(2, '0')}',
                      trailing: ReportDownloadButton(
                        token: token,
                        historyId: entry.id,
                        compact: true,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        if (entry.location.isNotEmpty)
                          TfPill(
                            label: entry.location,
                            icon: Icons.location_on_outlined,
                          ),
                        if (entry.contractType.isNotEmpty)
                          TfPill(
                            label: entry.contractType,
                            icon: Icons.badge_outlined,
                          ),
                        TfPill(
                          label: '${entry.totalResults} offres',
                          icon: Icons.work_outline,
                        ),
                        if (atsLite?['overallScore'] != null)
                          TfPill(
                            label: 'ATS ${atsLite!['overallScore']}/100',
                            icon: Icons.rule_folder_outlined,
                          ),
                        TfPill(
                          label: _llmLabel(),
                          color: entry.llmUsed
                              ? const Color(0xFFDDF7E8)
                              : AppTheme.mist,
                          foreground: entry.llmUsed
                              ? AppTheme.success
                              : AppTheme.ink,
                          icon: Icons.smart_toy_outlined,
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    TfCallout(
                      title: 'Lecture rapide du profil',
                      message: entry.cvPreview,
                      icon: Icons.description_outlined,
                      color: AppTheme.teal,
                    ),
                    if (entry.skills.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: entry.skills
                            .take(18)
                            .map((String skill) => Chip(label: Text(skill)))
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            TfReveal(
              delay: const Duration(milliseconds: 90),
              child: TfPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const TfSectionHeader(
                      title: 'Réponse structurée',
                      subtitle:
                          'Synthèse finale prête à être réutilisée pour tes prochaines candidatures.',
                    ),
                    const SizedBox(height: 14),
                    _HistoryAssistantStructuredView(
                      assistantStructured: assistantStructured,
                      assistantMessage: entry.assistantMessage,
                    ),
                    if (entry.llmError.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 12),
                      const TfCallout(
                        title: 'Information',
                        message:
                            'Une étape d’assistance a échoué, mais la synthèse de secours reste exploitable.',
                        icon: Icons.warning_amber_outlined,
                        color: AppTheme.warning,
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (atsLite != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: TfReveal(
                  delay: const Duration(milliseconds: 130),
                  child: TfPanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const TfSectionHeader(
                          title: 'Lecture ATS-lite',
                          subtitle:
                              'Score, mots-clés et conseils sauvegardés avec cette analyse.',
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            SizedBox(
                              width: 210,
                              child: TfScoreCard(
                                label: 'Global',
                                score: (atsLite['overallScore'] ?? 0) as int,
                                caption: (atsLite['readinessLabel'] ?? '')
                                    .toString(),
                                color: AppTheme.teal,
                              ),
                            ),
                            SizedBox(
                              width: 210,
                              child: TfScoreCard(
                                label: 'Structure',
                                score: (atsLite['structureScore'] ?? 0) as int,
                                caption: 'Lisibilité initiale',
                                color: AppTheme.gold,
                              ),
                            ),
                            SizedBox(
                              width: 210,
                              child: TfScoreCard(
                                label: 'Alignement',
                                score: (atsLite['alignmentScore'] ?? 0) as int,
                                caption: 'Offres retenues',
                                color: AppTheme.coral,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        _HistoryAssistantStructuredView(
                          assistantStructured: <String, dynamic>{
                            'profileSummary': (atsLite['summary'] ?? '')
                                .toString(),
                            'strengths':
                                atsLite['matchedKeywords'] ?? const <dynamic>[],
                            'gaps':
                                atsLite['missingKeywords'] ?? const <dynamic>[],
                            'actions':
                                atsLite['suggestions'] ?? const <dynamic>[],
                            'reasonIfNoMatch': null,
                          },
                          assistantMessage: '',
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ...displayJobs.map((Map<String, dynamic> job) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: TfPanel(
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text((job['title'] ?? '').toString()),
                    subtitle: Text(
                      [
                        (job['company'] ?? '').toString(),
                        (job['location'] ?? '').toString(),
                      ].where((String e) => e.isNotEmpty).join(' • '),
                    ),
                    trailing: Wrap(
                      spacing: 4,
                      children: <Widget>[
                        IconButton(
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                builder: (_) =>
                                    JobDetailPage(token: token, job: job),
                              ),
                            );
                          },
                          icon: const Icon(Icons.visibility_outlined),
                        ),
                        IconButton(
                          onPressed: () =>
                              _openUrl((job['sourceUrl'] ?? '').toString()),
                          icon: const Icon(Icons.open_in_new),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _HistoryAssistantStructuredView extends StatelessWidget {
  const _HistoryAssistantStructuredView({
    required this.assistantStructured,
    required this.assistantMessage,
  });

  final Map<String, dynamic>? assistantStructured;
  final String assistantMessage;

  List<String> _stringList(String key) {
    final raw =
        assistantStructured?[key] as List<dynamic>? ?? const <dynamic>[];
    return raw
        .map((dynamic item) => item.toString())
        .where((String item) => item.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    if (assistantStructured == null) {
      return Text(assistantMessage);
    }

    final mode = (assistantStructured?['mode'] ?? '').toString();
    final profileSummary = (assistantStructured?['profileSummary'] ?? '')
        .toString();
    final strengths = _stringList('strengths');
    final gaps = _stringList('gaps');
    final actions = _stringList('actions');
    final reasonIfNoMatch = (assistantStructured?['reasonIfNoMatch'] ?? '')
        .toString();
    final scoreExplanation = (assistantStructured?['scoreExplanation'] ?? '')
        .toString();
    final offerPlaybooks =
        (assistantStructured?['offerPlaybooks'] as List<dynamic>? ??
                const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    Widget title(String label) => Text(
      label,
      style: Theme.of(
        context,
      ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (profileSummary.isNotEmpty) ...<Widget>[
          title('Résumé du profil'),
          const SizedBox(height: 8),
          Text(profileSummary),
        ],
        if (strengths.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          title('Forces'),
          const SizedBox(height: 6),
          ...strengths.map((String item) => Text('• $item')),
        ],
        if (gaps.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          title('Points à renforcer'),
          const SizedBox(height: 6),
          ...gaps.map((String item) => Text('• $item')),
        ],
        if (mode == 'no_match') ...<Widget>[
          const SizedBox(height: 12),
          title('Diagnostic'),
          const SizedBox(height: 6),
          Text(
            reasonIfNoMatch.isEmpty
                ? 'Aucune offre réellement pertinente n’a été retenue pour ce profil.'
                : reasonIfNoMatch,
          ),
        ],
        if (scoreExplanation.trim().isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          title('Progression de score'),
          const SizedBox(height: 6),
          Text(scoreExplanation),
        ],
        if (offerPlaybooks.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          title('Playbooks par offre'),
          const SizedBox(height: 6),
          ...offerPlaybooks.take(3).map((Map<String, dynamic> playbook) {
            final rewrite =
                playbook['rewrite'] is Map<String, dynamic>
                    ? playbook['rewrite'] as Map<String, dynamic>
                    : const <String, dynamic>{};
            final bullets =
                (rewrite['experienceBullets'] as List<dynamic>? ??
                        const <dynamic>[])
                    .map((dynamic item) => item.toString())
                    .where((String item) => item.trim().isNotEmpty)
                    .toList();
            final evidence =
                (playbook['evidence'] as List<dynamic>? ?? const <dynamic>[])
                    .map((dynamic item) => item.toString())
                    .where((String item) => item.trim().isNotEmpty)
                    .toList();
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                <String>[
                  if ((playbook['title'] ?? '').toString().trim().isNotEmpty)
                    'Offre : ${(playbook['title'] ?? '').toString()}',
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
                    'Preuves CV : ${evidence.join(' • ')}',
                ].join('\n'),
              ),
            );
          }),
        ],
        if (actions.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          title('Actions immédiates'),
          const SizedBox(height: 6),
          ...actions.map((String item) => Text('• $item')),
        ],
        if (assistantMessage.isNotEmpty &&
            profileSummary.isEmpty &&
            strengths.isEmpty &&
            gaps.isEmpty &&
            actions.isEmpty) ...<Widget>[Text(assistantMessage)],
      ],
    );
  }
}
