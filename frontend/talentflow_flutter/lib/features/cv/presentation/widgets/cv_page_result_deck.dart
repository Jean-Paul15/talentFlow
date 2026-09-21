import 'package:flutter/material.dart';

import 'cv_page_data.dart';
import 'cv_page_result_action_plan_panel.dart';
import 'cv_page_result_insights_panel.dart';
import 'cv_page_result_jobs_panel.dart';
import 'cv_page_result_skills_panel.dart';
import 'cv_page_result_summary_panel.dart';

class CvResultDeck extends StatelessWidget {
  const CvResultDeck({
    super.key,
    required this.token,
    required this.payload,
    required this.atsLite,
    required this.assistantStructured,
    required this.cvAnalysis,
    required this.skills,
    required this.displayJobs,
    required this.llmLabel,
    required this.historyId,
    required this.onOpenUrl,
  });

  final String token;
  final Map<String, dynamic> payload;
  final Map<String, dynamic>? atsLite;
  final Map<String, dynamic>? assistantStructured;
  final Map<String, dynamic> cvAnalysis;
  final List<String> skills;
  final List<Map<String, dynamic>> displayJobs;
  final String llmLabel;
  final String? historyId;
  final Future<void> Function(String?) onOpenUrl;

  @override
  Widget build(BuildContext context) {
    final mode = (assistantStructured?['mode'] ?? '').toString();
    final profileSummary = (assistantStructured?['profileSummary'] ?? '')
        .toString();
    final reasonIfNoMatch = (assistantStructured?['reasonIfNoMatch'] ?? '')
        .toString();
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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        CvResultSummaryPanel(
          token: token,
          historyId: historyId,
          mode: mode,
          llmLabel: llmLabel,
          totalResults: (payload['totalResults'] ?? 0) as int,
          overallScore: (atsLite?['overallScore'] ?? 0) as int,
          structureScore: (atsLite?['structureScore'] ?? 0) as int,
          alignmentScore: (atsLite?['alignmentScore'] ?? 0) as int,
          evidenceScore: (atsLite?['evidenceScore'] ?? 0) as int,
          readiness: (atsLite?['readinessLabel'] ?? 'Diagnostic prêt')
              .toString(),
          profileSummary: profileSummary,
          reasonIfNoMatch: reasonIfNoMatch,
          assistantMessage: (payload['assistantMessage'] ?? '').toString(),
          experienceYears: (cvAnalysis['experienceYears'] ?? '').toString(),
          educationLevel: (cvAnalysis['educationLevel'] ?? '').toString(),
          llmError: (payload['llmError'] ?? '').toString(),
        ),
        const SizedBox(height: 14),
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
        const SizedBox(height: 14),
        CvResultActionPlanPanel(actionPlan: actionPlan, actions: actions),
        if (skills.isNotEmpty) ...<Widget>[
          const SizedBox(height: 14),
          CvResultSkillsPanel(skills: skills),
        ],
        if (displayJobs.isNotEmpty) ...<Widget>[
          const SizedBox(height: 14),
          CvResultJobsPanel(
            token: token,
            jobs: displayJobs,
            assistantStructured: assistantStructured,
            onOpenUrl: onOpenUrl,
          ),
        ],
      ],
    );
  }
}
