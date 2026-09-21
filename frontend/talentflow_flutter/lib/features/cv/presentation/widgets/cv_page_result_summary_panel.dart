import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/reports/report_download_button.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

import 'cv_page_result_summary_highlights.dart';

class CvResultSummaryPanel extends StatelessWidget {
  const CvResultSummaryPanel({
    super.key,
    required this.token,
    required this.historyId,
    required this.mode,
    required this.llmLabel,
    required this.totalResults,
    required this.overallScore,
    required this.structureScore,
    required this.alignmentScore,
    required this.evidenceScore,
    required this.readiness,
    required this.profileSummary,
    required this.reasonIfNoMatch,
    required this.assistantMessage,
    required this.experienceYears,
    required this.educationLevel,
    required this.llmError,
  });

  final String token;
  final String? historyId;
  final String mode;
  final String llmLabel;
  final int totalResults;
  final int overallScore;
  final int structureScore;
  final int alignmentScore;
  final int evidenceScore;
  final String readiness;
  final String profileSummary;
  final String reasonIfNoMatch;
  final String assistantMessage;
  final String experienceYears;
  final String educationLevel;
  final String llmError;

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          TfSectionHeader(
            title: 'Diagnostic candidat',
            subtitle:
                'Synthèse finale pour décider vite: candidater, ajuster le CV ou recentrer la cible.',
            trailing: ReportDownloadButton(
              token: token,
              historyId: historyId,
              compact: true,
            ),
          ),
          const SizedBox(height: 14),
          CvResultSummaryHighlights(
            mode: mode,
            llmLabel: llmLabel,
            totalResults: totalResults,
            overallScore: overallScore,
            structureScore: structureScore,
            alignmentScore: alignmentScore,
            evidenceScore: evidenceScore,
            readiness: readiness,
            experienceYears: experienceYears,
            educationLevel: educationLevel,
          ),
          const SizedBox(height: 14),
          TfCallout(
            title: mode == 'no_match'
                ? 'Diagnostic prioritaire'
                : 'Lecture rapide du profil',
            message: mode == 'no_match' && reasonIfNoMatch.isNotEmpty
                ? reasonIfNoMatch
                : (profileSummary.isEmpty ? assistantMessage : profileSummary),
            icon: mode == 'no_match'
                ? Icons.track_changes_outlined
                : Icons.auto_graph_outlined,
            color: mode == 'no_match' ? AppTheme.warning : AppTheme.teal,
          ),
          if (llmError.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            const TfCallout(
              title: 'Retour technique',
              message:
                  'Une étape d’assistance a échoué, mais le diagnostic de secours reste exploitable.',
              icon: Icons.warning_amber_outlined,
              color: AppTheme.warning,
            ),
          ],
        ],
      ),
    );
  }
}


