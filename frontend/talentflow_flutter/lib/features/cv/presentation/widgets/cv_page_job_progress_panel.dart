import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/cv/cv_job_status.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/tf_lottie_loader.dart';

class CvJobProgressPanel extends StatefulWidget {
  const CvJobProgressPanel({super.key, required this.job});

  final CvJobStatus job;

  @override
  State<CvJobProgressPanel> createState() => _CvJobProgressPanelState();
}

class _CvJobProgressPanelState extends State<CvJobProgressPanel>
    with SingleTickerProviderStateMixin {
  late final AnimationController _msgCtrl;
  int _lastProgress = 0;

  @override
  void initState() {
    super.initState();
    _msgCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 4400),
    )..repeat();
    _lastProgress = widget.job.progress;
  }

  @override
  void didUpdateWidget(CvJobProgressPanel old) {
    super.didUpdateWidget(old);
    final progress = widget.job.progress;
    for (final int milestone in <int>[25, 50, 75, 100]) {
      if (_lastProgress < milestone && progress >= milestone) {
        milestone == 100
            ? HapticFeedback.heavyImpact()
            : HapticFeedback.lightImpact();
        break;
      }
    }
    _lastProgress = progress;
  }

  @override
  void dispose() {
    _msgCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final done = widget.job.status == 'COMPLETED';
    final failed = widget.job.status == 'FAILED';
    final color = failed
        ? AppTheme.danger
        : (done ? AppTheme.success : AppTheme.teal);
    final progress = (widget.job.progress / 100).clamp(0.0, 1.0);
    final currentStep = _stepIndexFromStage(widget.job.stage);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.20)),
      ),
      child: Column(
        children: <Widget>[
          SizedBox(
            width: 96,
            height: 96,
            child: Stack(
              alignment: Alignment.center,
              children: <Widget>[
                CircularProgressIndicator(
                  value: 1.0,
                  strokeWidth: 7,
                  strokeCap: StrokeCap.round,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    color.withValues(alpha: 0.14),
                  ),
                ),
                TweenAnimationBuilder<double>(
                  tween: Tween<double>(begin: 0, end: progress),
                  duration: const Duration(milliseconds: 600),
                  curve: Curves.easeOutCubic,
                  builder: (BuildContext context, double value, Widget? _) {
                    return CircularProgressIndicator(
                      value: value,
                      strokeWidth: 7,
                      strokeCap: StrokeCap.round,
                      backgroundColor: Colors.transparent,
                      valueColor: AlwaysStoppedAnimation<Color>(color),
                    );
                  },
                ),
                Text(
                  '${widget.job.progress}%',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: color,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _PipelineSteps(currentStep: currentStep, done: done, failed: failed),
          const SizedBox(height: 14),
          if (!done && !failed)
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 320),
              transitionBuilder: (Widget child, Animation<double> anim) {
                return FadeTransition(
                  opacity: anim,
                  child: SlideTransition(
                    position: Tween<Offset>(
                      begin: const Offset(0, 0.2),
                      end: Offset.zero,
                    ).animate(anim),
                    child: child,
                  ),
                );
              },
              child: Text(
                _headlineForStep(currentStep),
                key: ValueKey<String>(
                  '${widget.job.stage}_${widget.job.progress}',
                ),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppTheme.inkSoft,
                  fontWeight: FontWeight.w700,
                ),
              ),
            )
          else if (done)
            Text(
              'Analyse finalisée avec succès',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            )
          else
            Text(
              'Analyse interrompue: ${widget.job.stageLabel}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppTheme.danger,
                fontWeight: FontWeight.w700,
              ),
            ),
          const SizedBox(height: 8),
          Text(
            widget.job.etaHint,
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppTheme.inkSoft),
          ),
          if (!done && !failed) ...<Widget>[
            const SizedBox(height: 12),
            const TfLottieLoader(width: 76, height: 24),
          ],
        ],
      ),
    );
  }

  String _headlineForStep(int step) {
    switch (step) {
      case 0:
        return 'Réception sécurisée du CV';
      case 1:
        return 'Lecture intelligente de ton profil';
      case 2:
        return 'Sélection des offres les plus crédibles';
      case 3:
        return 'Finalisation du plan de candidature';
      default:
        return 'Traitement en cours';
    }
  }

  int _stepIndexFromStage(String stage) {
    switch (stage) {
      case 'QUEUED':
        return 0;
      case 'EXTRACT_TEXT':
      case 'OCR_IF_NEEDED':
      case 'ANALYZE_PROFILE':
        return 1;
      case 'SEARCH_MATCHING':
      case 'LLM_SYNTHESIS':
        return 2;
      case 'SAVE_HISTORY':
      case 'COMPLETED':
      case 'FAILED':
        return 3;
      default:
        final idx = (_msgCtrl.value * 4).floor();
        return idx.clamp(0, 3);
    }
  }
}

class _PipelineSteps extends StatelessWidget {
  const _PipelineSteps({
    required this.currentStep,
    required this.done,
    required this.failed,
  });

  final int currentStep;
  final bool done;
  final bool failed;

  static const List<String> _labels = <String>[
    'Réception',
    'Lecture',
    'Matching',
    'Finalisation',
  ];

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 8,
      runSpacing: 8,
      children: List<Widget>.generate(_labels.length, (int index) {
        final reached = done || index <= currentStep;
        final isActive = !done && !failed && index == currentStep;
        final Color bg = reached
            ? AppTheme.teal.withValues(alpha: isActive ? 0.20 : 0.14)
            : AppTheme.inkSoft.withValues(alpha: 0.08);
        final Color fg = reached ? AppTheme.teal : AppTheme.inkSoft;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: fg.withValues(alpha: 0.20)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                reached
                    ? PhosphorIconsBold.checkCircle
                    : PhosphorIconsRegular.circle,
                size: 12,
                color: fg,
              ),
              const SizedBox(width: 6),
              Text(
                _labels[index],
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: fg,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        );
      }),
    );
  }
}

