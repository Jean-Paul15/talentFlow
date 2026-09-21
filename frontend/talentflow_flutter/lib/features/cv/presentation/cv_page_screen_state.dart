part of 'cv_page_screen.dart';

class _CvPageState extends State<CvPage> {
  late final _CvPageActions _actions = _CvPageActions(this);

  final _cvCtrl = TextEditingController();
  final CvUploadService _cvUploadService = CvUploadService();
  final CvLocalExtractor _cvLocalExtractor = CvLocalExtractor();
  final CvJobsStore _cvJobsStore = CvJobsStore();

  bool _loading = false;
  bool _uploading = false;
  Map<String, dynamic>? _payload;
  CvJobStatus? _activeJob;
  Timer? _jobTimer;
  String? _uploadedFileName;
  String? _uploadStrategy;
  int? _uploadChars;
  double? _uploadQuality;
  bool? _uploadOcrUsed;
  int _uploadCelebrationTick = 0;
  String? _savedHistoryId;
  bool _openResultsOnPayload = false;

  @override
  void initState() {
    super.initState();
    _actions.resumeActiveJob();
  }

  @override
  void dispose() {
    _jobTimer?.cancel();
    _cvCtrl.dispose();
    super.dispose();
  }

  void _applyState(VoidCallback fn) => setState(fn);

  @override
  Widget build(BuildContext context) {
    final payload = _payload;
    final atsLite = atsLiteOf(payload);
    final assistantStructured = assistantStructuredOf(payload);

    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 10, 24, 28),
      children: <Widget>[
        const TfSectionHeader(
          title: 'Analyse CV',
          subtitle:
              'Importe ton CV, récupère un diagnostic exploitable et cible des opportunités crédibles.',
        ),
        const SizedBox(height: 14),
        LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= 980;
            final composer = CvComposerPanel(
              cvController: _cvCtrl,
              uploadedFileName: _uploadedFileName,
              uploadStrategy: _uploadStrategy,
              uploadChars: _uploadChars,
              uploadQuality: _uploadQuality,
              uploadOcrUsed: _uploadOcrUsed,
              uploadCelebrationTick: _uploadCelebrationTick,
              loading: _loading,
              uploading: _uploading,
              activeJob: _activeJob,
              onPickCv: _uploading ? null : _actions.pickAndExtractCv,
              onRecommend: _loading ? null : _actions.recommend,
            );

            final insights = AnimatedSwitcher(
              duration: const Duration(milliseconds: 260),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeOutCubic,
              child: _loading
                  ? const CvLoadingState()
                  : payload == null
                  ? const TfPanel(
                      child: TfEmptyState(
                        title: 'Aucun diagnostic pour l\u2019instant',
                        message:
                            'Importe un CV et lance une analyse pour obtenir un score d\u2019alignement.',
                        icon: Icons.psychology_alt_outlined,
                      ),
                    )
                  : TfPanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          TfSectionHeader(
                            title:
                                (assistantStructured?['mode'] ?? '')
                                        .toString() ==
                                    'no_match'
                                ? 'Diagnostic pr\u00EAt : aucun match cr\u00E9dible'
                                : 'Diagnostic pr\u00EAt : match trouv\u00E9',
                            subtitle:
                                'Ouvre la page r\u00E9sultats pour voir les d\u00E9tails.',
                          ),
                          const SizedBox(height: 14),
                          Wrap(
                            spacing: 14,
                            runSpacing: 14,
                            children: <Widget>[
                              TfProgressRing(
                                value: (atsLite?['overallScore'] ?? 0) as int,
                                label: 'Global',
                                size: 88,
                              ),
                              TfProgressRing(
                                value: (atsLite?['structureScore'] ?? 0) as int,
                                label: 'Structure',
                                size: 72,
                              ),
                              TfProgressRing(
                                value: (atsLite?['alignmentScore'] ?? 0) as int,
                                label: 'Alignement',
                                size: 72,
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          TfCallout(
                            title: 'Synth\u00E8se rapide',
                            message:
                                (assistantStructured?['profileSummary'] ?? '')
                                    .toString()
                                    .trim()
                                    .isNotEmpty
                                ? (assistantStructured?['profileSummary'] ?? '')
                                      .toString()
                                : (payload['assistantMessage'] ?? '')
                                      .toString(),
                            icon: Icons.psychology_alt_outlined,
                          ),
                          const SizedBox(height: 14),
                          FilledButton.icon(
                            onPressed: _actions.openResultsPage,
                            icon: const Icon(Icons.arrow_forward),
                            label: const Text(
                              'Ouvrir le r\u00E9sultat complet',
                            ),
                          ),
                        ],
                      ),
                    ),
            );

            if (wide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(flex: 5, child: composer),
                  const SizedBox(width: 16),
                  Expanded(flex: 6, child: insights),
                ],
              );
            }
            return Column(
              children: <Widget>[
                composer,
                const SizedBox(height: 14),
                insights,
              ],
            );
          },
        ),
      ],
    );
  }
}
