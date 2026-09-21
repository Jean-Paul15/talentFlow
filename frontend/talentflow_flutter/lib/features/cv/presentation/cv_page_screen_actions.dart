part of 'cv_page_screen.dart';

class _CvPageActions {
  _CvPageActions(this._state) : _io = _CvPageIoActions(_state);

  final _CvPageState _state;
  final _CvPageIoActions _io;

  void _applyState(VoidCallback fn) => _state._applyState(fn);

  Future<void> recommend() async {
    final text = _state._cvCtrl.text.trim();
    final hasImportedSource = (_state._uploadedFileName ?? '')
        .trim()
        .isNotEmpty;
    if (!hasImportedSource || text.length < 30) {
      AppSnack.show(
        _state.context,
        message: 'Importe ton CV avant de lancer l’analyse.',
        type: AppSnackType.warning,
      );
      return;
    }
    _applyState(() {
      _state._loading = true;
      _state._savedHistoryId = null;
      _state._payload = null;
      _state._openResultsOnPayload = true;
    });
    try {
      final job = await _state._cvJobsStore.createTextJob(
        token: _state.widget.token,
        cvText: text,
        fileName: _state._uploadedFileName ?? 'cv.txt',
        topK: 5,
      );
      if (!_state.mounted) return;
      _applyState(() => _state._activeJob = job);
      _io.startPolling(job.jobId);
    } catch (e) {
      if (!_state.mounted) return;
      final userMessage = e.toString().replaceFirst('Exception: ', '');
      AppSnack.show(
        _state.context,
        message: userMessage,
        type: AppSnackType.error,
      );
    }
  }

  Future<void> resumeActiveJob() async {
    final jobId = await _state._cvJobsStore.loadActiveJobId();
    if (jobId == null || !_state.mounted) return;
    _state._openResultsOnPayload = false;
    try {
      final status = await _state._cvJobsStore.getJob(
        token: _state.widget.token,
        jobId: jobId,
      );
      if (!_state.mounted) return;
      _applyState(() {
        _state._activeJob = status;
        _state._loading =
            status.status != 'COMPLETED' && status.status != 'FAILED';
      });
      if (_state._loading) _io.startPolling(jobId);
      if (status.historyId != null && status.historyId!.isNotEmpty) {
        await _io.loadHistoryEntry(status.historyId!);
      }
    } catch (_) {
      await _state._cvJobsStore.saveActiveJobId(null);
    }
  }

  Future<void> pickAndExtractCv() => _io.pickAndExtractCv();

  Future<void> openUrl(String? url) => _io.openUrl(url);

  Future<void> openResultsPage() async {
    final payload = _state._payload;
    if (payload == null || !_state.mounted) return;
    await Navigator.of(_state.context).push(
      MaterialPageRoute<void>(
        builder: (_) => CvResultsPage(
          token: _state.widget.token,
          payload: payload,
          historyId: _state._savedHistoryId,
        ),
      ),
    );
  }
}
