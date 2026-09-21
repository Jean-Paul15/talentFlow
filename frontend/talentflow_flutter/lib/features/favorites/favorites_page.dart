import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:url_launcher/url_launcher.dart';

import '../../core/cache/cache_runtime_service.dart';
import '../../core/feedback/app_snack.dart';
import '../../core/favorites/favorites_store.dart';
import '../../core/jobs/source_label.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';
import '../jobs/job_detail_page.dart';

class FavoritesPage extends StatefulWidget {
  const FavoritesPage({super.key, required this.token, this.asSheet = false});

  final String token;
  final bool asSheet;

  @override
  State<FavoritesPage> createState() => _FavoritesPageState();
}

class _FavoritesPageState extends State<FavoritesPage> {
  final FavoritesStore _store = FavoritesStore();
  bool _loading = true;
  List<FavoriteEntry> _entries = const <FavoriteEntry>[];

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
    setState(() {
      _loading = true;
    });
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
        _entries = const <FavoriteEntry>[];
        _loading = false;
      });
      AppSnack.show(context, message: message, type: AppSnackType.error);
    }
  }

  Future<void> _remove(FavoriteEntry entry) async {
    await _store.remove(token: widget.token, jobId: entry.jobId);
    await _load();
  }

  Future<void> _openUrl(String? url) async {
    final raw = (url ?? '').trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Widget _sheetHeader(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Center(
          child: Container(
            margin: const EdgeInsets.only(top: 12, bottom: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppTheme.mist,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 16, 12),
          child: Row(
            children: <Widget>[
              Text(
                'Favoris',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              if (!_loading)
                TfPill(
                  label:
                      '${_entries.length} offre${_entries.length > 1 ? 's' : ''}',
                  icon: Icons.favorite,
                  color: const Color(0xFFFFECE8),
                  foreground: AppTheme.coral,
                ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
                tooltip: 'Fermer',
              ),
            ],
          ),
        ),
        const Divider(height: 1),
      ],
    );
  }

  Widget _buildContent(BuildContext context) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Center(child: CircularProgressIndicator(color: AppTheme.teal)),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.teal,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: <Widget>[
          if (!widget.asSheet) ...<Widget>[
            TfSectionHeader(
              title: 'Offres sauvegard\u00E9es',
              subtitle:
                  'Garde tes offres prioritaires sous la main pour candidater vite.',
              trailing: TfPill(
                label:
                    '${_entries.length} offre${_entries.length > 1 ? 's' : ''}',
                icon: Icons.favorite,
                color: const Color(0xFFFFECE8),
                foreground: AppTheme.coral,
              ),
            ),
            const SizedBox(height: 16),
          ],
          if (_entries.isEmpty && !_loading)
            TfEmptyState(
              title: 'Aucun favori pour le moment',
              message: 'Ajoute des offres depuis la recherche ou le détail.',
              icon: Icons.favorite_border,
              action: FilledButton.icon(
                onPressed: () {
                  if (widget.asSheet) Navigator.of(context).pop();
                },
                icon: const Icon(Icons.search),
                label: const Text('Rechercher des offres'),
              ),
            ),
          ..._entries.asMap().entries.map((
            MapEntry<int, FavoriteEntry> mapEntry,
          ) {
            final idx = mapEntry.key;
            final entry = mapEntry.value;
            final createdAt = DateTime.tryParse(entry.createdAtIso)?.toLocal();
            final job = entry.toJobMap();

            return TfReveal(
              delay: Duration(milliseconds: idx * 50),
              child: Dismissible(
                key: Key(entry.jobId),
                direction: DismissDirection.endToStart,
                background: Container(
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 24),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.danger.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: const Icon(
                    Icons.delete_outline,
                    color: AppTheme.danger,
                    size: 28,
                  ),
                ),
                confirmDismiss: (_) async {
                  HapticFeedback.mediumImpact();
                  return true;
                },
                onDismissed: (_) async {
                  await _remove(entry);
                  if (!mounted) return;
                  AppSnack.show(
                    this.context,
                    message: 'Offre retir\u00E9e des favoris.',
                    type: AppSnackType.info,
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TfPressable(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) =>
                            JobDetailPage(token: widget.token, job: job),
                      ),
                    ),
                    child: TfPanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              if (sourceLabel(entry.sourceName).isNotEmpty)
                                TfPill(
                                  label: sourceLabel(entry.sourceName),
                                  color: const Color(0xFFFDEBD2),
                                  foreground: const Color(0xFF8A5B12),
                                ),
                              if (entry.postedDate.isNotEmpty)
                                TfPill(
                                  label: entry.postedDate,
                                  icon: Icons.schedule,
                                ),
                              TfPill(
                                label: createdAt == null
                                    ? entry.createdAtIso
                                    : '${createdAt.day}/${createdAt.month}/${createdAt.year}',
                                icon: Icons.bookmark_added_outlined,
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            entry.title,
                            style: Theme.of(context).textTheme.headlineSmall
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              if (entry.company.isNotEmpty)
                                Chip(label: Text(entry.company)),
                              if (entry.location.isNotEmpty)
                                Chip(label: Text(entry.location)),
                              if (entry.contractType.isNotEmpty)
                                Chip(label: Text(entry.contractType)),
                              if (entry.salary.isNotEmpty)
                                Chip(label: Text(entry.salary)),
                              if (entry.score != null)
                                TfPill(
                                  label:
                                      'Score ${entry.score!.toStringAsFixed(3)}',
                                  color: const Color(0xFFDDF7E8),
                                  foreground: AppTheme.success,
                                ),
                            ],
                          ),
                          if (entry.description.isNotEmpty) ...<Widget>[
                            const SizedBox(height: 12),
                            Text(
                              entry.description.length > 220
                                  ? '${entry.description.substring(0, 220)}...'
                                  : entry.description,
                              style: Theme.of(context).textTheme.bodyMedium
                                  ?.copyWith(color: AppTheme.inkSoft),
                            ),
                          ],
                          const SizedBox(height: 14),
                          Row(
                            children: <Widget>[
                              FilledButton.tonalIcon(
                                onPressed: () => _openUrl(entry.sourceUrl),
                                icon: const Icon(Icons.open_in_new, size: 16),
                                label: const Text('Ouvrir'),
                              ),
                              const Spacer(),
                              Text(
                                '<- glisser pour retirer',
                                style: Theme.of(context).textTheme.bodySmall
                                    ?.copyWith(color: AppTheme.inkSoft),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.asSheet) {
      return Column(
        mainAxisSize: MainAxisSize.max,
        children: <Widget>[
          _sheetHeader(context),
          Expanded(child: _buildContent(context)),
        ],
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Favoris')),
      body: Container(
        decoration: AppTheme.appBackground,
        child: _buildContent(context),
      ),
    );
  }
}
