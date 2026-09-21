part of 'cv_page_screen.dart';

const String _recommendationHistoryQuery = r'''
query RecommendationHistoryEntry($id: String!) {
  recommendationHistoryEntry(id: $id) {
    id
    queryUsed
    totalResults
    assistantMessage
    llmUsed
    llmProvider
    llmModel
    llmError
    llmStatus
    assistantStructured {
      mode
      profileSummary
      strengths
      gaps
      scoreExplanation
      offerPlaybooks {
        jobId
        title
        url
        whyFit
        cvDelta
        rewrite { targetTitle targetSummary experienceBullets }
        evidence
      }
      actions
      reasonIfNoMatch
      recommendedJobs { jobId title why url cvImprovement }
    }
    atsLite { overallScore structureScore alignmentScore evidenceScore readinessLabel summary matchedKeywords missingKeywords suggestions actionPlan }
    cvAnalysis { skills experienceYears educationLevel rawTextPreview }
    jobs { id title company location contractType sourceName sourceUrl postedDate score summary }
  }
}
''';

class _CvPageIoActions {
  _CvPageIoActions(this._state);

  final _CvPageState _state;

  void _applyState(VoidCallback fn) => _state._applyState(fn);

  void _applyExtractedCv(
    CvUploadExtractionResult extracted, {
    required String successMessage,
    required AppSnackType snackType,
  }) {
    _applyState(() {
      _state._uploadedFileName = extracted.fileName;
      _state._uploadStrategy = _statusLabelFor(extracted);
      _state._uploadChars = extracted.extractedChars;
      _state._uploadQuality = extracted.qualityScore;
      _state._uploadOcrUsed = extracted.ocrUsed;
      _state._uploadCelebrationTick++;
      _state._cvCtrl.text = extracted.text;
      _state._savedHistoryId = null;
    });
    AppSnack.show(_state.context, message: successMessage, type: snackType);
  }

  String _statusLabelFor(CvUploadExtractionResult extracted) {
    if (extracted.ocrUsed) return 'Lecture assistée activée';
    if (extracted.documentKind == 'ambiguous') {
      return 'Texte préparé pour l’analyse';
    }
    return 'CV importé';
  }

  String _successMessageFor(
    CvUploadExtractionResult extracted, {
    required bool fallbackUsed,
  }) {
    if (extracted.documentKind == 'ambiguous') {
      return 'Le document a été lu. Une vérification renforcée sera appliquée avant le diagnostic.';
    }
    if (fallbackUsed) {
      return 'Le CV a été lu correctement et préparé pour l’analyse.';
    }
    return 'CV importé : ${extracted.fileName}. L’analyse peut démarrer.';
  }

  void startPolling(String jobId) {
    _state._jobTimer?.cancel();
    _state._jobTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final job = await _state._cvJobsStore.getJob(
          token: _state.widget.token,
          jobId: jobId,
        );
        if (!_state.mounted) return;
        _applyState(() {
          _state._activeJob = job;
          _state._loading =
              job.status == 'QUEUED' || job.status == 'IN_PROGRESS';
        });
        if (job.status == 'FAILED') {
          AppSnack.show(
            _state.context,
            message: job.error ?? 'Le traitement du CV a échoué.',
            type: AppSnackType.error,
          );
        }
        if (job.status == 'COMPLETED' || job.status == 'FAILED') {
          _state._jobTimer?.cancel();
          await _state._cvJobsStore.saveActiveJobId(null);
          if (job.historyId != null && job.historyId!.isNotEmpty) {
            await loadHistoryEntry(job.historyId!);
          }
        }
      } catch (e) {
        if (!_state.mounted) return;
        AppSnack.show(
          _state.context,
          message: ApiErrorParser.normalizeNetworkException(
            e,
            timeoutMessage:
                'Le traitement prend trop de temps. Réessaie dans un instant.',
            offlineMessage: 'Connexion indisponible pour le suivi. Réessaie.',
            fallbackMessage: 'Suivi temporairement indisponible. Réessaie.',
          ),
          type: AppSnackType.error,
        );
      }
    });
  }

  Future<void> loadHistoryEntry(String historyId) async {
    final data = await GraphQlApi.request(
      document: _recommendationHistoryQuery,
      variables: {'id': historyId},
      token: _state.widget.token,
    );
    final entry = data['recommendationHistoryEntry'] as Map<String, dynamic>?;
    if (!_state.mounted || entry == null) return;
    _applyState(() {
      _state._payload = entry;
      _state._savedHistoryId = historyId;
      _state._loading = false;
    });
    if (_state._openResultsOnPayload) {
      _state._openResultsOnPayload = false;
      await _state._actions.openResultsPage();
    }
  }

  Future<void> pickAndExtractCv() async {
    PlatformFile? selectedFile;
    Uint8List? selectedBytes;
    _applyState(() {
      _state._uploading = true;
    });
    try {
      final result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: const <String>['pdf', 'docx', 'txt', 'md'],
      );
      if (result == null || result.files.isEmpty) return;

      selectedFile = result.files.single;
      selectedBytes = selectedFile.bytes;
      if (selectedBytes == null || selectedBytes.isEmpty) {
        throw Exception('Impossible de lire le fichier sélectionné.');
      }

      final extracted = await _state._cvUploadService.extractText(
        token: _state.widget.token,
        fileName: selectedFile.name,
        bytes: selectedBytes,
      );
      if (!_state.mounted) return;
      if (extracted.documentKind == 'non_cv') {
        throw CvUploadException(
          message: extracted.userMessage,
          code: 'NOT_A_CV',
          canTryLocalFallback: false,
        );
      }
      _applyExtractedCv(
        extracted,
        successMessage: _successMessageFor(extracted, fallbackUsed: false),
        snackType: extracted.documentKind == 'ambiguous'
            ? AppSnackType.warning
            : AppSnackType.success,
      );
    } on CvUploadException catch (error) {
      if (!_state.mounted) return;
      final localExtraction =
          error.canTryLocalFallback &&
              selectedFile != null &&
              selectedBytes != null
          ? await _state._cvLocalExtractor.tryExtract(
              fileName: selectedFile.name,
              bytes: selectedBytes,
            )
          : null;
      if (!_state.mounted) return;
      if (localExtraction != null && localExtraction.text.trim().length >= 30) {
        if (localExtraction.documentKind == 'non_cv') {
          AppSnack.show(
            _state.context,
            message: localExtraction.userMessage,
            type: AppSnackType.error,
          );
          return;
        }
        _applyExtractedCv(
          localExtraction,
          successMessage: _successMessageFor(
            localExtraction,
            fallbackUsed: true,
          ),
          snackType: localExtraction.documentKind == 'ambiguous'
              ? AppSnackType.warning
              : AppSnackType.info,
        );
        return;
      }
      AppSnack.show(
        _state.context,
        message: error.message,
        type: AppSnackType.error,
      );
    } catch (e) {
      if (!_state.mounted) return;
      final userMessage = ApiErrorParser.normalizeNetworkException(
        e,
        timeoutMessage: 'L’import prend trop de temps. Réessaie avec ce CV.',
        offlineMessage:
            'Connexion indisponible. Vérifie le réseau puis réessaie.',
        fallbackMessage: 'Impossible de lire ce document pour le moment.',
      );
      AppSnack.show(
        _state.context,
        message: userMessage,
        type: AppSnackType.error,
      );
    } finally {
      if (_state.mounted) {
        _applyState(() => _state._uploading = false);
      }
    }
  }

  Future<void> openUrl(String? url) async {
    final raw = (url ?? '').trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}
