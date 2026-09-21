import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';

class TalentFlowDesktopRail extends StatelessWidget {
  const TalentFlowDesktopRail({
    super.key,
    required this.index,
    required this.onSelected,
    required this.onLogout,
  });

  final int index;
  final ValueChanged<int> onSelected;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    final items =
        <({int index, IconData icon, IconData selectedIcon, String label})>[
          (
            index: 0,
            icon: PhosphorIconsRegular.house,
            selectedIcon: PhosphorIconsFill.house,
            label: 'Accueil',
          ),
          (
            index: 1,
            icon: PhosphorIconsRegular.magnifyingGlass,
            selectedIcon: PhosphorIconsFill.magnifyingGlass,
            label: 'Recherche',
          ),
          (
            index: 2,
            icon: PhosphorIconsRegular.fileText,
            selectedIcon: PhosphorIconsFill.fileText,
            label: 'CV',
          ),
          (
            index: 3,
            icon: PhosphorIconsRegular.clockCounterClockwise,
            selectedIcon: PhosphorIconsFill.clockCounterClockwise,
            label: 'Historique',
          ),
          (
            index: 4,
            icon: PhosphorIconsRegular.userCircle,
            selectedIcon: PhosphorIconsFill.userCircle,
            label: 'Profil',
          ),
        ];

    return Padding(
      padding: const EdgeInsets.all(16),
      child: SizedBox(
        width: 200,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 18, 14, 14),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusL),
            border: Border.all(color: AppTheme.cardBorder),
            boxShadow: AppTheme.softShadow,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Image.asset(
                  'assets/images/logo.png',
                  width: 28,
                  height: 28,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => Image.asset(
                    'assets/images/logo.png',
                    width: 28,
                    height: 28,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) =>
                        const SizedBox(width: 28, height: 28),
                  ),
                ),
              ),
              const SizedBox(height: 22),
              ...items.map((item) {
                final selected = index == item.index;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Material(
                    color: selected ? AppTheme.mist : Colors.transparent,
                    borderRadius: BorderRadius.circular(AppTheme.radiusM),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(AppTheme.radiusM),
                      splashColor: AppTheme.mist,
                      onTap: () {
                        HapticFeedback.selectionClick();
                        onSelected(item.index);
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        child: Row(
                          children: <Widget>[
                            PhosphorIcon(
                              selected ? item.selectedIcon : item.icon,
                              color: selected
                                  ? AppTheme.ink
                                  : AppTheme.inkMuted,
                              size: 18,
                            ),
                            const SizedBox(width: 10),
                            Text(
                              item.label,
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(
                                    color: selected
                                        ? AppTheme.ink
                                        : AppTheme.inkMuted,
                                    fontWeight: selected
                                        ? FontWeight.w700
                                        : FontWeight.w500,
                                    fontSize: 13,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: TextButton.icon(
                  onPressed: () {
                    HapticFeedback.mediumImpact();
                    onLogout();
                  },
                  style: TextButton.styleFrom(
                    foregroundColor: AppTheme.inkSoft,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                  ),
                  icon: const Icon(PhosphorIconsRegular.signOut, size: 16),
                  label: const Text(
                    'Déconnexion',
                    style: TextStyle(fontWeight: FontWeight.w500, fontSize: 13),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
