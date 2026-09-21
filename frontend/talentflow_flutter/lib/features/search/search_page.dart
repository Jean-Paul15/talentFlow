import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';

import '../../core/favorites/favorite_toggle_button.dart';
import '../../core/feedback/app_snack.dart';
import '../../core/jobs/source_label.dart';
import '../../core/network/graphql_api.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';
import '../jobs/job_detail_page.dart';
import 'search_filters_page.dart';

class SearchPage extends StatefulWidget {
  const SearchPage({super.key, required this.token});

  final String token;

  @override
  State<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends State<SearchPage> {
  final TextEditingController _queryCtrl = TextEditingController();
  String _location = '';
  String _contractType = '';
  String _country = '';
  bool _loading = false;
  List<Map<String, dynamic>> _results = <Map<String, dynamic>>[];
  int _total = 0;

  @override
  void dispose() {
    _queryCtrl.dispose();
    super.dispose();
  }

  int get _activeFilterCount {
    int c = 0;
    if (_location.trim().isNotEmpty) c++;
    if (_contractType.trim().isNotEmpty) c++;
    if (_country.trim().isNotEmpty) c++;
    return c;
  }

  List<String> get _activeFilterLabels => <String>[
    if (_location.trim().isNotEmpty) _location.trim(),
    if (_contractType.trim().isNotEmpty) _contractType.trim(),
    if (_country.trim().isNotEmpty) _country.trim(),
  ];

  Future<void> _search() async {
    final query = _queryCtrl.text.trim();
    if (query.isEmpty) {
      const warning = 'Saisis un poste, une compétence ou une entreprise.';
      AppSnack.show(context, message: warning, type: AppSnackType.warning);
      return;
    }

    HapticFeedback.lightImpact();
    setState(() {
      _loading = true;
    });

    try {
      const doc = r'''
query SearchJobs($input: SearchJobsInput!) {
  searchJobs(input: $input) {
    total
    results { id title company location contractType sourceName sourceUrl postedDate score salary description }
  }
}
''';

      final input = <String, dynamic>{'query': query, 'limit': 20};
      if (_location.trim().isNotEmpty) input['location'] = _location.trim();
      if (_contractType.trim().isNotEmpty) {
        input['contractType'] = _contractType.trim();
      }
      if (_country.trim().isNotEmpty) input['country'] = _country.trim();

      final data = await GraphQlApi.request(
        document: doc,
        variables: <String, dynamic>{'input': input},
        token: widget.token,
      );
      final payload = data['searchJobs'] as Map<String, dynamic>;
      final results = (payload['results'] as List<dynamic>? ?? <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .toList();
      if (!mounted) return;
      setState(() {
        _results = results;
        _total = (payload['total'] ?? results.length) as int;
      });
    } catch (error) {
      if (!mounted) return;
      final message = error.toString().replaceFirst('Exception: ', '');
      AppSnack.show(context, message: message, type: AppSnackType.error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openFilters() async {
    final result = await showModalBottomSheet<SearchFilterValues>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FractionallySizedBox(
        heightFactor: 0.9,
        child: SearchFiltersPage(
          initial: SearchFilterValues(
            location: _location,
            contractType: _contractType,
            country: _country,
          ),
        ),
      ),
    );
    if (result == null || !mounted) return;
    setState(() {
      _location = result.location;
      _contractType = result.contractType;
      _country = result.country;
    });
  }

  int _score(dynamic value) {
    if (value is! num) return 0;
    if (value <= 1) return (value * 100).round().clamp(0, 100);
    return value.round().clamp(0, 100);
  }

  @override
  Widget build(BuildContext context) {
    const quickQueries = <String>[
      'Développeur backend',
      'Comptable confirmé',
      'Data analyst',
      'DevOps',
      'Marketing digital',
    ];

    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
      children: <Widget>[
        TfReveal(
          delay: const Duration(milliseconds: 40),
          child: TfCard(
            variant: TfCardVariant.glass,
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Recherche d’offres',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _queryCtrl,
                  onSubmitted: (_) => _search(),
                  decoration: InputDecoration(
                    hintText: 'Poste, compétence, entreprise…',
                    prefixIcon: Icon(
                      PhosphorIconsRegular.magnifyingGlass,
                      color: AppTheme.inkMuted,
                      size: 16,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: <Widget>[
                    Badge(
                      isLabelVisible: _activeFilterCount > 0,
                      label: Text(
                        '$_activeFilterCount',
                        style: const TextStyle(fontSize: 9),
                      ),
                      backgroundColor: AppTheme.gold,
                      child: SizedBox(
                        height: 38,
                        child: OutlinedButton.icon(
                          onPressed: _openFilters,
                          icon: const Icon(
                            PhosphorIconsRegular.faders,
                            size: 14,
                          ),
                          label: const Text('Filtres'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: SizedBox(
                        height: 38,
                        child: FilledButton.icon(
                          onPressed: _loading ? null : _search,
                          icon: _loading
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(
                                  PhosphorIconsBold.magnifyingGlass,
                                  size: 14,
                                ),
                          label: Text(_loading ? 'Recherche…' : 'Lancer'),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TfChipBar(
                  items: quickQueries,
                  onTap: (query) {
                    _queryCtrl.text = query;
                    _search();
                  },
                ),
                if (_activeFilterLabels.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 6),
                  TfChipBar(items: _activeFilterLabels),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2),
          child: Text(
            _results.isEmpty
                ? 'Aucun résultat'
                : '$_total résultat${_total > 1 ? 's' : ''}',
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: AppTheme.inkSoft),
          ),
        ),
        const SizedBox(height: 8),
        if (_results.isEmpty && !_loading)
          TfEmptyIllustration(
            title: 'Aucune offre',
            message: 'Teste une requête ou ajuste les filtres.',
            icon: PhosphorIconsRegular.briefcase,
          ),
        ..._results.asMap().entries.map((entry) {
          final idx = entry.key;
          final job = entry.value;
          final title = (job['title'] ?? '').toString();
          final company = (job['company'] ?? '').toString();
          final location = (job['location'] ?? '').toString();
          final salary = (job['salary'] ?? '').toString();
          final score = _score(job['score']);
          final contextLine = <String>[
            company,
            location,
            (job['contractType'] ?? '').toString(),
            sourceLabel((job['sourceName'] ?? '').toString()),
          ].where((value) => value.isNotEmpty).join(' · ');
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: TfReveal(
              delay: Duration(milliseconds: 80 + (idx * 30)),
              child: TfJobCard(
                title: title,
                contextLine: contextLine,
                matchLabel: 'Match $score%',
                dateLabel: salary.isEmpty ? 'Récent' : salary,
                favorite: FavoriteToggleButton(token: widget.token, job: job),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) =>
                        JobDetailPage(token: widget.token, job: job),
                  ),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }
}
