import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';

class HomeHeroPanel extends StatelessWidget {
  const HomeHeroPanel({
    super.key,
    required this.headline,
    required this.location,
    required this.country,
    required this.email,
    required this.preferredRolesCount,
    required this.onNavigateToCv,
    required this.onNavigateToSearch,
    required this.onOpenFavorites,
  });

  final String headline;
  final String location;
  final String country;
  final String email;
  final int preferredRolesCount;
  final VoidCallback onNavigateToCv;
  final VoidCallback onNavigateToSearch;
  final VoidCallback onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: AppTheme.ink,
        borderRadius: BorderRadius.circular(20),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppTheme.ink.withValues(alpha: 0.25),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Tag
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(Icons.auto_awesome, size: 14, color: AppTheme.gold),
                const SizedBox(width: 6),
                Text(
                  'Copilote candidature',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Transforme ton CV en plan\nclair de candidature.',
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
              height: 0.95,
              letterSpacing: -1,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            headline.isNotEmpty
                ? headline
                : 'Repère les offres crédibles, explique les écarts et décide quoi envoyer.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: const Color(0xFFB0C4D0),
            ),
          ),
          const SizedBox(height: 18),
          // Info chips
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              if (location.isNotEmpty)
                _InfoChip(icon: Icons.location_on_outlined, label: location),
              if (country.isNotEmpty)
                _InfoChip(icon: Icons.public, label: country),
              _InfoChip(
                icon: Icons.work_outline,
                label: preferredRolesCount == 0
                    ? 'Cible à préciser'
                    : '$preferredRolesCount rôles ciblés',
              ),
            ],
          ),
          const SizedBox(height: 24),
          // Action buttons
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onNavigateToCv,
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: AppTheme.ink,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                icon: const Icon(Icons.description_outlined, size: 18),
                label: const Text('Analyser mon CV'),
              ),
              OutlinedButton.icon(
                onPressed: onNavigateToSearch,
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.25)),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                icon: const Icon(Icons.search, size: 18),
                label: const Text('Explorer les offres'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 14, color: const Color(0xFF8AA0B0)),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFFB0C4D0),
              fontWeight: FontWeight.w600,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}
