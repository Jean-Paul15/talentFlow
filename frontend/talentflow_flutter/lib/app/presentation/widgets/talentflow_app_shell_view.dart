import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'talentflow_app_shell_desktop_rail.dart';
import 'talentflow_app_shell_top_bar.dart';

class TalentFlowAppShellView extends StatelessWidget {
  const TalentFlowAppShellView({
    super.key,
    required this.index,
    required this.pages,
    required this.onSelected,
    required this.onLogout,
    required this.onOpenFavorites,
  });

  final int index;
  final List<Widget> pages;
  final ValueChanged<int> onSelected;
  final Future<void> Function() onLogout;
  final Future<void> Function() onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    final destinations = <({IconData icon, String label})>[
      (icon: PhosphorIconsRegular.house, label: 'Accueil'),
      (icon: PhosphorIconsRegular.magnifyingGlass, label: 'Recherche'),
      (icon: PhosphorIconsRegular.fileText, label: 'CV'),
      (icon: PhosphorIconsRegular.clockCounterClockwise, label: 'Historique'),
      (icon: PhosphorIconsRegular.userCircle, label: 'Profil'),
    ];

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final wide = constraints.maxWidth >= 1000;
        return Scaffold(
          body: Container(
            decoration: AppTheme.appBackground,
            child: SafeArea(
              child: wide
                  ? Row(
                      children: <Widget>[
                        TalentFlowDesktopRail(
                          index: index,
                          onSelected: onSelected,
                          onLogout: onLogout,
                        ),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(0, 16, 16, 16),
                            child: Column(
                              children: <Widget>[
                                TalentFlowTopBar(
                                  compact: false,
                                  onLogout: onLogout,
                                  onOpenFavorites: onOpenFavorites,
                                ),
                                const SizedBox(height: 12),
                                Expanded(
                                  child: AnimatedSwitcher(
                                    duration: const Duration(milliseconds: 200),
                                    switchInCurve: Curves.easeOut,
                                    switchOutCurve: Curves.easeIn,
                                    child: KeyedSubtree(
                                      key: ValueKey<int>(index),
                                      child: pages[index],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    )
                  : Column(
                      children: <Widget>[
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: TalentFlowTopBar(
                            compact: true,
                            onLogout: onLogout,
                            onOpenFavorites: onOpenFavorites,
                          ),
                        ),
                        Expanded(
                          child: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 180),
                            switchInCurve: Curves.easeOut,
                            switchOutCurve: Curves.easeIn,
                            child: KeyedSubtree(
                              key: ValueKey<int>(index),
                              child: pages[index],
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
          ),
          bottomNavigationBar: wide
              ? null
              : _BottomBar(
                  index: index,
                  items: destinations,
                  onSelected: (int i) {
                    HapticFeedback.selectionClick();
                    onSelected(i);
                  },
                ),
        );
      },
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.index,
    required this.items,
    required this.onSelected,
  });

  final int index;
  final List<({IconData icon, String label})> items;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: const Border(top: BorderSide(color: AppTheme.cardBorder)),
      ),
      padding: const EdgeInsets.fromLTRB(8, 6, 8, 10),
      child: Row(
        children: List<Widget>.generate(items.length, (int i) {
          final selected = i == index;
          final item = items[i];
          return Expanded(
            child: InkWell(
              borderRadius: BorderRadius.circular(AppTheme.radiusS),
              onTap: () => onSelected(i),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    PhosphorIcon(
                      item.icon,
                      size: 20,
                      color: selected ? AppTheme.ink : AppTheme.inkMuted,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item.label,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: selected ? AppTheme.ink : AppTheme.inkMuted,
                        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
