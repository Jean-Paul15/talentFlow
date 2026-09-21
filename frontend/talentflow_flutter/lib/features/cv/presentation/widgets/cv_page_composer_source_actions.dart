import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

class CvComposerSourceActions extends StatelessWidget {
  const CvComposerSourceActions({
    super.key,
    required this.uploading,
    required this.onPickCv,
  });

  final bool uploading;
  final Future<void> Function()? onPickCv;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: uploading ? null : () => onPickCv?.call(),
      icon: uploading
          ? const SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(PhosphorIconsRegular.uploadSimple, size: 14),
      label: const Text('Importer PDF / DOCX / TXT'),
    );
  }
}
