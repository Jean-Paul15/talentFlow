import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvComposerUploadInfo extends StatelessWidget {
  const CvComposerUploadInfo({
    super.key,
    required this.uploadedFileName,
    required this.uploadStrategy,
    required this.uploadChars,
    required this.uploadQuality,
    required this.uploadOcrUsed,
  });

  final String? uploadedFileName;
  final String? uploadStrategy;
  final int? uploadChars;
  final double? uploadQuality;
  final bool? uploadOcrUsed;

  String _friendlyUploadLabel() {
    final value = (uploadStrategy ?? '').trim().toLowerCase();
    if (value.isEmpty) return 'CV importé';
    if (value == 'ocr_fallback' || value == 'ocr_recovery') {
      return 'Lecture assistée activée';
    }
    if (value == 'docx_mammoth' || value == 'plain_text') {
      return 'Texte préparé pour l’analyse';
    }
    return 'CV importé';
  }

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: <Widget>[
        TfPill(label: uploadedFileName!, icon: Icons.description_outlined),
        if ((uploadStrategy ?? '').isNotEmpty)
          TfPill(
            label: _friendlyUploadLabel(),
            color: const Color(0xFFDDF7E8),
            foreground: AppTheme.success,
            icon: Icons.auto_fix_high,
          ),
        if (uploadChars != null)
          TfPill(label: '${uploadChars!} caractères', icon: Icons.text_fields),
        if (uploadQuality != null)
          TfPill(
            label: 'Lecture ${(uploadQuality! * 100).round()}%',
            icon: Icons.insights_outlined,
          ),
        if (uploadOcrUsed == true)
          const TfPill(
            label: 'OCR activé',
            icon: Icons.document_scanner_outlined,
          ),
      ],
    );
  }
}
