import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/cache/cache_runtime_service.dart';
import '../../core/feedback/app_snack.dart';
import '../../core/history/recommendation_history_store.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';
import '../history/history_detail_page.dart';
import '../jobs/job_detail_page.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key, required this.token});

  final String token;

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final RecommendationHistoryStore _store = RecommendationHistoryStore();
  bool _loading = true;
  List<RecommendationHistoryEntry> _entries =
      const <RecommendationHistoryEntry>[];

  @override
  void initState() {
    super.initState();
    CacheRuntimeService.changeTick.addListener(_onCacheVersionChanged);
    _load();
  }

  @override
  void dispose() {
    CacheRuntimeService.changeTick.removeListener(_onCacheVersionChanged);
    super.dispose();
  }

  void _onCacheVersionChanged() {
    if (!mounted) return;
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final entries = await _store.read(token: widget.token);
      if (!mounted) return;
      setState(() {
        _entries = entries;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      final message = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _entries = const <RecommendationHistoryEntry>[];
        _loading = false;
      });
      AppSnack.show(context, message: message, type: AppSnackType.error);
    }
  }

  Future<void> _delete(String id) async {
    await _store.delete(token: widget.token, id: id);
    if (!mounted) return;
    AppSnack.show(
      context,
      message: '\u00C9l\u00E9ment supprim\u00E9 de l\'historique.',
      type: AppSnackType.info,
    );
    await _load();
  }

  Future<void> _openUrl(String? url) async {
    final raw = (url ?? '').trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  String _statusLabel(RecommendationHistoryEntry entry) {
    final mode = (entry.assistantStructured?['mode'] ?? '').toString();
    if (mode == 'no_match') return 'Aucun match';
    if (entry.llmStatus == 'used_cached') return 'Analyse optimisée';
    if (entry.llmStatus.isNotEmpty) return 'Analyse prête';
    return 'Prêt';
  }

  Color _statusColor(RecommendationHistoryEntry entry) {
    final mode = (entry.assistantStructured?['mode'] ?? '').toString();
    if (mode == 'no_match') return AppTheme.warning;
    if (entry.llmStatus == 'used_cached') return AppTheme.teal;
    return AppTheme.success;
  }

  List<Map<String, dynamic>> _displayJobs(RecommendationHistoryEntry entry) {
    final structured = entry.assistantStructured;
    if (structured == null) return entry.jobs;
    final mode = (structured['mode'] ?? '').toString();
    if (mode == 'no_match') return const <Map<String, dynamic>>[];
    return entry.jobs;
  }

  String _summary(RecommendationHistoryEntry entry) {
    final structured = entry.assistantStructured;
    final profileSummary = (structured?['profileSummary'] ?? '').toString();
    final reason = (structured?['reasonIfNoMatch'] ?? '').toString();
    if (profileSummary.isNotEmpty) return profileSummary;
    if (reason.isNotEmpty) return reason;
    return entry.assistantMessage;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.gold,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 4),
            child: Row(
              children: <Widget>[
                Text(
                  'Historique',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                if (_entries.isNotEmpty) ...<Widget>[
                  const SizedBox(width: 8),
                  Text(
                    '${_entries.length}',
                    style: Theme.of(
                      context,
                    ).textTheme.labelMedium?.copyWith(color: AppTheme.inkSoft),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 8),
          if (_loading) ...<Widget>[
            const TfSkeletonBlock(height: 120),
            const SizedBox(height: 10),
            const TfSkeletonBlock(height: 120),
          ] else ...<Widget>[
            if (_entries.isEmpty)
              TfEmptyIllustration(
                title: 'Aucune analyse sauvegardée',
                message:
                    'Lance une analyse CV pour créer ton premier historique.',
                icon: PhosphorIconsRegular.clockCounterClockwise,
              ),
            ..._entries.asMap().entries.map((entry) {
              final i = entry.key;
              final item = entry.value;
              final jobs = _displayJobs(item);
              final createdAt = DateTime.tryParse(item.createdAtIso)?.toLocal();
              final dateLabel = createdAt == null
                  ? ''
                  : '${createdAt.day}/${createdAt.month}/${createdAt.year}';
              final statusColor = _statusColor(item);

              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Dismissible(
                  key: ValueKey(item.id),
                  direction: DismissDirection.endToStart,
                  confirmDismiss: (_) async {
                    HapticFeedback.mediumImpact();
                    return true;
                  },
                  onDismissed: (_) => _delete(item.id),
                  background: Container(
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.symmetric(horizontal: 18),
                    decoration: BoxDecoration(
                      color: AppTheme.danger.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Icon(
                      PhosphorIconsRegular.trash,
                      color: AppTheme.danger,
                      size: 20,
                    ),
                  ),
                  child: TfReveal(
                    delay: Duration(milliseconds: i * 50),
                    child: TfCard(
                      variant: TfCardVariant.compact,
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Row(
                            children: <Widget>[
                              if (dateLabel.isNotEmpty) ...<Widget>[
                                Icon(
                                  PhosphorIconsRegular.calendar,
                                  size: 13,
                                  color: AppTheme.inkMuted,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  dateLabel,
                                  style: Theme.of(context).textTheme.bodySmall
                                      ?.copyWith(
                                        color: AppTheme.inkSoft,
                                        fontSize: 12,
                                      ),
                                ),
                                const SizedBox(width: 10),
                              ],
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 3,
                                ),
                                decoration: BoxDecoration(
                                  color: statusColor.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  _statusLabel(item),
                                  style: Theme.of(context).textTheme.labelSmall
                                      ?.copyWith(
                                        color: statusColor,
                                        fontWeight: FontWeight.w700,
                                        fontSize: 10,
                                      ),
                                ),
                              ),
                              const Spacer(),
                              Text(
                                '${jobs.length} offre${jobs.length > 1 ? 's' : ''}',
                                style: Theme.of(context).textTheme.labelMedium
                                    ?.copyWith(
                                      color: AppTheme.goldDark,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 12,
                                    ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            _summary(item),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(fontSize: 13, height: 1.4),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: <Widget>[
                              Expanded(
                                child: SizedBox(
                                  height: 36,
                                  child: FilledButton.icon(
                                    onPressed: () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => HistoryDetailPage(
                                            token: widget.token,
                                            entry: item,
                                          ),
                                        ),
                                      );
                                    },
                                    style: FilledButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                      ),
                                      textStyle: const TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    icon: const Icon(
                                      PhosphorIconsRegular.eye,
                                      size: 15,
                                    ),
                                    label: const Text('D\u00E9tail'),
                                  ),
                                ),
                              ),
                              if (jobs.isNotEmpty) ...<Widget>[
                                const SizedBox(width: 8),
                                SizedBox(
                                  height: 36,
                                  child: OutlinedButton(
                                    onPressed: () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => JobDetailPage(
                                            token: widget.token,
                                            job: jobs.first,
                                          ),
                                        ),
                                      );
                                    },
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                      ),
                                      textStyle: const TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    child: const Text('1re offre'),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                SizedBox(
                                  height: 36,
                                  child: IconButton(
                                    onPressed: () => _openUrl(
                                      (jobs.first['sourceUrl'] ?? '')
                                          .toString(),
                                    ),
                                    style: IconButton.styleFrom(
                                      side: const BorderSide(
                                        color: AppTheme.cardBorder,
                                      ),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                    ),
                                    icon: const Icon(
                                      PhosphorIconsRegular.arrowSquareOut,
                                      size: 16,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}
