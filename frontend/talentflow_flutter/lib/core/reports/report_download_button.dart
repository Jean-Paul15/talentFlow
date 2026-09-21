import 'package:flutter/material.dart';

import '../feedback/app_snack.dart';
import 'report_download_service.dart';

class ReportDownloadButton extends StatefulWidget {
  const ReportDownloadButton({
    super.key,
    required this.token,
    required this.historyId,
    this.compact = false,
  });

  final String token;
  final String? historyId;
  final bool compact;

  @override
  State<ReportDownloadButton> createState() => _ReportDownloadButtonState();
}

class _ReportDownloadButtonState extends State<ReportDownloadButton> {
  final ReportDownloadService _service = ReportDownloadService();
  bool _downloading = false;
  bool _sharing = false;
  String? _error;

  Future<void> _download() async {
    final historyId = (widget.historyId ?? '').trim();
    if (historyId.isEmpty || _downloading || _sharing) return;
    setState(() {
      _downloading = true;
      _error = null;
    });
    try {
      final result = await _service.downloadHistoryPdf(
        token: widget.token,
        historyId: historyId,
      );
      if (!mounted) return;
      AppSnack.show(
        context,
        message: 'Rapport prêt: ${result.fileName}',
        type: AppSnackType.success,
      );
    } catch (e) {
      _handleError(e);
    } finally {
      if (mounted) {
        setState(() => _downloading = false);
      }
    }
  }

  Future<void> _share() async {
    final historyId = (widget.historyId ?? '').trim();
    if (historyId.isEmpty || _sharing || _downloading) return;
    setState(() {
      _sharing = true;
      _error = null;
    });
    try {
      final result = await _service.shareHistoryPdf(
        token: widget.token,
        historyId: historyId,
      );
      if (!mounted) return;
      AppSnack.show(
        context,
        message: 'Rapport partagé: ${result.fileName}',
        type: AppSnackType.success,
      );
    } catch (e) {
      _handleError(e);
    } finally {
      if (mounted) {
        setState(() => _sharing = false);
      }
    }
  }

  void _handleError(Object error) {
    if (!mounted) return;
    setState(() {
      _error = error.toString().replaceFirst('Exception: ', '');
    });
    AppSnack.show(
      context,
      message: _error!,
      type: AppSnackType.error,
    );
  }

  @override
  Widget build(BuildContext context) {
    final disabled =
        _downloading || _sharing || (widget.historyId ?? '').trim().isEmpty;
    final isBusy = _downloading || _sharing;
    final label = _downloading
        ? 'Génération...'
        : widget.compact
        ? 'PDF'
        : 'Télécharger le rapport';
    final icon = isBusy
        ? const SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : const Icon(Icons.picture_as_pdf_outlined);

    if (widget.compact) {
      return AnimatedScale(
        scale: isBusy ? 0.98 : 1,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        child: FilledButton.tonalIcon(
          onPressed: disabled ? null : _download,
          icon: icon,
          label: Text(label),
        ),
      );
    }

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: <Widget>[
        AnimatedScale(
          scale: isBusy ? 0.98 : 1,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          child: FilledButton.tonalIcon(
            onPressed: disabled ? null : _download,
            icon: icon,
            label: Text(label),
          ),
        ),
        OutlinedButton.icon(
          onPressed: disabled ? null : _share,
          icon: const Icon(Icons.ios_share_rounded),
          label: const Text('Partager'),
        ),
      ],
    );
  }
}

