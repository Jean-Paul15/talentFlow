import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/cv/cv_job_status.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

import 'cv_page_composer_source_actions.dart';
import 'cv_page_composer_upload_info.dart';
import 'cv_page_job_progress_panel.dart';
import 'cv_page_upload_celebration.dart';

class CvComposerPanel extends StatelessWidget {
  const CvComposerPanel({
    super.key,
    required this.cvController,
    required this.uploadedFileName,
    required this.uploadStrategy,
    required this.uploadChars,
    required this.uploadQuality,
    required this.uploadOcrUsed,
    required this.uploadCelebrationTick,
    required this.loading,
    required this.uploading,
    required this.activeJob,
    required this.onPickCv,
    required this.onRecommend,
  });

  final TextEditingController cvController;
  final String? uploadedFileName;
  final String? uploadStrategy;
  final int? uploadChars;
  final double? uploadQuality;
  final bool? uploadOcrUsed;
  final int uploadCelebrationTick;
  final bool loading;
  final bool uploading;
  final CvJobStatus? activeJob;
  final Future<void> Function()? onPickCv;
  final Future<void> Function()? onRecommend;

  @override
  Widget build(BuildContext context) {
    final hasInput = cvController.text.trim().length >= 30;

    return Column(
      children: <Widget>[
        TfReveal(
          child: TfPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Icon(
                      PhosphorIconsBold.fileArrowUp,
                      size: 14,
                      color: AppTheme.inkSoft,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Import CV',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Importe ton CV puis lance le diagnostic. La saisie manuelle n\u2019est plus propos\u00E9e.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppTheme.inkSoft),
                ),
                const SizedBox(height: 12),
                Stack(
                  clipBehavior: Clip.none,
                  children: <Widget>[
                    CvComposerSourceActions(
                      uploading: uploading,
                      onPickCv: onPickCv,
                    ),
                    Positioned.fill(
                      child: CvUploadCelebration(
                        trigger: uploadCelebrationTick,
                      ),
                    ),
                  ],
                ),
                if (uploadedFileName != null) ...<Widget>[
                  const SizedBox(height: 10),
                  TfReveal(
                    delay: const Duration(milliseconds: 60),
                    child: CvComposerUploadInfo(
                      uploadedFileName: uploadedFileName,
                      uploadStrategy: uploadStrategy,
                      uploadChars: uploadChars,
                      uploadQuality: uploadQuality,
                      uploadOcrUsed: uploadOcrUsed,
                    ),
                  ),
                ],
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: hasInput
                        ? AppTheme.success.withValues(alpha: 0.08)
                        : AppTheme.warning.withValues(alpha: 0.10),
                    border: Border.all(
                      color: hasInput
                          ? AppTheme.success.withValues(alpha: 0.28)
                          : AppTheme.warning.withValues(alpha: 0.25),
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: <Widget>[
                      Icon(
                        hasInput
                            ? PhosphorIconsRegular.checkCircle
                            : PhosphorIconsRegular.warningCircle,
                        size: 15,
                        color: hasInput ? AppTheme.success : AppTheme.warning,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          hasInput
                              ? 'CV prêt pour le diagnostic.'
                              : 'Importe un PDF, DOCX ou TXT avant de continuer.',
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(
                                color: AppTheme.ink,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: (!hasInput || loading)
                        ? null
                        : () => onRecommend?.call(),
                    icon: loading
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(PhosphorIconsBold.sparkle, size: 14),
                    label: Text(
                      loading
                          ? 'Analyse en cours...'
                          : 'Lancer l\u2019analyse compl\u00E8te',
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (activeJob != null) ...<Widget>[
          const SizedBox(height: 10),
          TfReveal(
            delay: const Duration(milliseconds: 80),
            child: CvJobProgressPanel(job: activeJob!),
          ),
        ],
      ],
    );
  }
}
