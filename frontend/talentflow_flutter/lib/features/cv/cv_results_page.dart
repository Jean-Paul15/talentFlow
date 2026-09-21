import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:talentflow_flutter/core/reports/report_download_button.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_data.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_result_action_plan_panel.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_result_insights_panel.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_result_jobs_panel.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_result_skills_panel.dart';
import 'package:talentflow_flutter/features/cv/presentation/widgets/cv_page_result_summary_panel.dart';

class CvResultsPage extends StatelessWidget {
  const CvResultsPage({
    super.key,
    required this.token,
    required this.payload,
    required this.historyId,
  });

  final String token;
  final Map<String, dynamic> payload;
  final String? historyId;

  Future<void> _openUrl(String? url) async {
    final raw = (url ?? '').trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final cvAnalysis =
        (payload['cvAnalysis'] as Map<String, dynamic>? ?? <String, dynamic>{});
    final atsLite = atsLiteOf(payload);
    final assistantStructured = assistantStructuredOf(payload);
    final skills = stringList(cvAnalysis, 'skills');
    final strengths = stringList(assistantStructured, 'strengths');
    final gaps = stringList(assistantStructured, 'gaps');
    final actions = stringList(assistantStructured, 'actions');
    final matchedKeywords = stringList(atsLite, 'matchedKeywords');
    final missingKeywords = stringList(atsLite, 'missingKeywords');
    final suggestions = stringList(atsLite, 'suggestions');
    final actionPlan = stringList(atsLite, 'actionPlan');
    final scoreExplanation = (assistantStructured?['scoreExplanation'] ?? '')
        .toString();
    final offerPlaybooks =
        (assistantStructured?['offerPlaybooks'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final jobs = cvJobsFromPayload(payload);
    final displayJobs = displayJobsForPayload(jobs, assistantStructured);
    final overall = (atsLite?['overallScore'] ?? 0) as int;

    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Résultats d’analyse'),
          actions: <Widget>[
            ReportDownloadButton(
              token: token,
              historyId: historyId,
              compact: true,
            ),
            const SizedBox(width: 6),
          ],
          bottom: TabBar(
            isScrollable: true,
            indicatorColor: AppTheme.gold,
            indicatorWeight: 2.5,
            labelColor: AppTheme.ink,
            unselectedLabelColor: AppTheme.inkMuted,
            labelStyle: Theme.of(context).textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
            dividerColor: AppTheme.cardBorder,
            tabs: const <Tab>[
              Tab(text: 'Résumé'),
              Tab(text: 'Détails'),
              Tab(text: 'Offres'),
              Tab(text: 'Actions'),
            ],
          ),
        ),
        body: Container(
          decoration: AppTheme.appBackground,
          child: TabBarView(
            children: <Widget>[
              ListView(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
                children: <Widget>[
                  TfReveal(
                    delay: const Duration(milliseconds: 40),
                    child: _ScoreHeroCard(
                      overall: overall,
                      profileSummary:
                          (assistantStructured?['profileSummary'] ?? '')
                              .toString(),
                    ),
                  ),
                  const SizedBox(height: 14),
                  CvResultSummaryPanel(
                    token: token,
                    historyId: historyId,
                    mode: (assistantStructured?['mode'] ?? '').toString(),
                    llmLabel: llmLabelForPayload(payload),
                    totalResults: (payload['totalResults'] ?? 0) as int,
                    overallScore: overall,
                    structureScore: (atsLite?['structureScore'] ?? 0) as int,
                    alignmentScore: (atsLite?['alignmentScore'] ?? 0) as int,
                    evidenceScore: (atsLite?['evidenceScore'] ?? 0) as int,
                    readiness:
                        (atsLite?['readinessLabel'] ?? 'Diagnostic prêt').toString(),
                    profileSummary:
                        (assistantStructured?['profileSummary'] ?? '').toString(),
                    reasonIfNoMatch:
                        (assistantStructured?['reasonIfNoMatch'] ?? '').toString(),
                    assistantMessage: (payload['assistantMessage'] ?? '').toString(),
                    experienceYears: (cvAnalysis['experienceYears'] ?? '').toString(),
                    educationLevel: (cvAnalysis['educationLevel'] ?? '').toString(),
                    llmError: (payload['llmError'] ?? '').toString(),
                  ),
                ],
              ),
              ListView(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
                children: <Widget>[
                  CvResultInsightsPanel(
                    strengths: strengths,
                    gaps: gaps,
                    matchedKeywords: matchedKeywords,
                    missingKeywords: missingKeywords,
                    suggestions: suggestions,
                    actions: actions,
                    skills: skills,
                    scoreExplanation: scoreExplanation,
                    offerPlaybooks: offerPlaybooks,
                  ),
                  if (skills.isNotEmpty) ...<Widget>[
                    const SizedBox(height: 14),
                    CvResultSkillsPanel(skills: skills),
                  ],
                ],
              ),
              ListView(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
                children: <Widget>[
                  if (displayJobs.isEmpty)
                    const TfReveal(
                      delay: Duration(milliseconds: 60),
                      child: TfEmptyIllustration(
                        title: 'Aucune offre crédible',
                        message:
                            'Le diagnostic recommande de renforcer le CV avant de candidater.',
                        icon: PhosphorIconsRegular.briefcase,
                      ),
                    )
                  else
                    TfReveal(
                      delay: const Duration(milliseconds: 60),
                      child: CvResultJobsPanel(
                        token: token,
                        jobs: displayJobs,
                        assistantStructured: assistantStructured,
                        onOpenUrl: _openUrl,
                      ),
                    ),
                ],
              ),
              ListView(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
                children: <Widget>[
                  CvResultActionPlanPanel(
                    actionPlan: actionPlan,
                    actions: actions,
                  ),
                  const SizedBox(height: 14),
                  TfCard(
                    variant: TfCardVariant.compact,
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Icon(
                              PhosphorIconsBold.calendarCheck,
                              size: 14,
                              color: AppTheme.inkSoft,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Plan 7 jours',
                              style: Theme.of(context).textTheme.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        ...(actionPlan.isEmpty ? actions : actionPlan)
                            .asMap()
                            .entries
                            .map((entry) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Container(
                                  margin: const EdgeInsets.only(top: 2),
                                  width: 18,
                                  height: 18,
                                  decoration: BoxDecoration(
                                    color: AppTheme.gold.withValues(alpha: 0.10),
                                    borderRadius: BorderRadius.circular(5),
                                  ),
                                  child: Center(
                                    child: Text(
                                      '${entry.key + 1}',
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelSmall
                                          ?.copyWith(
                                            color: AppTheme.goldDark,
                                            fontWeight: FontWeight.w800,
                                            fontSize: 10,
                                          ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    entry.value,
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(
                                          color: AppTheme.ink,
                                          fontSize: 13,
                                        ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                        if (actionPlan.isEmpty && actions.isEmpty)
                          Text(
                            'Aucune action immédiate pour cette analyse.',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: AppTheme.inkSoft),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScoreHeroCard extends StatelessWidget {
  const _ScoreHeroCard({required this.overall, required this.profileSummary});

  final int overall;
  final String profileSummary;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      variant: TfCardVariant.compact,
      padding: const EdgeInsets.all(16),
      child: Row(
        children: <Widget>[
          TfProgressRing(
            value: overall,
            label: 'Score ATS',
            size: 88,
            strokeWidth: 5,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: (overall >= 70 ? AppTheme.success : AppTheme.warning)
                        .withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    overall >= 70 ? 'Prêt à candidater' : 'Profil à renforcer',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: overall >= 70
                          ? AppTheme.success
                          : AppTheme.warning,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  profileSummary.isNotEmpty
                      ? profileSummary
                      : 'Diagnostic prêt. Parcours les onglets pour passer à l’action.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppTheme.inkSoft,
                    fontSize: 12.5,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

