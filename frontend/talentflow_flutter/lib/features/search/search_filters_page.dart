import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';

class SearchFilterValues {
  const SearchFilterValues({
    required this.location,
    required this.contractType,
    required this.country,
  });

  final String location;
  final String contractType;
  final String country;
}

class SearchFiltersPage extends StatefulWidget {
  const SearchFiltersPage({super.key, required this.initial});

  final SearchFilterValues initial;

  @override
  State<SearchFiltersPage> createState() => _SearchFiltersPageState();
}

class _SearchFiltersPageState extends State<SearchFiltersPage> {
  late final TextEditingController _locationCtrl = TextEditingController(
    text: widget.initial.location,
  );
  late final TextEditingController _contractCtrl = TextEditingController(
    text: widget.initial.contractType,
  );
  late final TextEditingController _countryCtrl = TextEditingController(
    text: widget.initial.country,
  );

  @override
  void dispose() {
    _locationCtrl.dispose();
    _contractCtrl.dispose();
    _countryCtrl.dispose();
    super.dispose();
  }

  void _reset() {
    _locationCtrl.clear();
    _contractCtrl.clear();
    _countryCtrl.clear();
    setState(() {});
  }

  void _apply() {
    Navigator.of(context).pop(
      SearchFilterValues(
        location: _locationCtrl.text,
        contractType: _contractCtrl.text,
        country: _countryCtrl.text,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          TfSectionHeader(
            title: 'Filtres recherche',
            subtitle: 'Affinez les offres avant de lancer la requête.',
            trailing: TextButton(
              onPressed: _reset,
              child: const Text('Réinitialiser'),
            ),
          ),
          const SizedBox(height: 12),
          TfPanel(
            child: Column(
              children: <Widget>[
                TextField(
                  controller: _locationCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Localisation',
                    prefixIcon: Icon(Icons.location_on_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _contractCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Type de contrat',
                    prefixIcon: Icon(Icons.badge_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _countryCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Pays',
                    prefixIcon: Icon(Icons.public_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: AppTheme.ctaGradient,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: FilledButton(
                      onPressed: _apply,
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                      ),
                      child: const Text('Appliquer les filtres'),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
