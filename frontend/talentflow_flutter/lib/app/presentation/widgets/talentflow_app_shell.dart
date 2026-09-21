import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import 'package:talentflow_flutter/core/theme/app_theme.dart';

import 'package:talentflow_flutter/features/cv/cv_page.dart';
import 'package:talentflow_flutter/features/favorites/favorites_page.dart';
import 'package:talentflow_flutter/features/history/history_page.dart';
import 'package:talentflow_flutter/features/home/home_page.dart';
import 'package:talentflow_flutter/features/profile/profile_page.dart';
import 'package:talentflow_flutter/features/search/search_page.dart';
import 'talentflow_app_shell_view.dart';

class TalentFlowAppShell extends StatefulWidget {
  const TalentFlowAppShell({
    super.key,
    required this.token,
    required this.email,
    required this.name,
    required this.onLogout,
    required this.onOpenOnboarding,
  });

  final String token;
  final String email;
  final String name;
  final Future<void> Function() onLogout;
  final VoidCallback onOpenOnboarding;

  @override
  State<TalentFlowAppShell> createState() => _TalentFlowAppShellState();
}

class _TalentFlowAppShellState extends State<TalentFlowAppShell> {
  int _index = 0;

  Future<void> _openFavorites() async {
    HapticFeedback.lightImpact();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext sheetCtx) {
        final height = MediaQuery.of(context).size.height * 0.88;
        return Container(
          height: height,
          decoration: const BoxDecoration(
            color: AppTheme.paper,
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: FavoritesPage(token: widget.token, asSheet: true),
        );
      },
    );
  }

  List<Widget> _pages() => <Widget>[
    HomePage(
      token: widget.token,
      fallbackEmail: widget.email,
      fallbackName: widget.name,
      onNavigate: (int index) => setState(() => _index = index),
      onOpenFavorites: _openFavorites,
    ),
    SearchPage(token: widget.token),
    CvPage(token: widget.token),
    HistoryPage(token: widget.token),
    ProfilePage(
      token: widget.token,
      fallbackEmail: widget.email,
      onOpenOnboarding: widget.onOpenOnboarding,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return TalentFlowAppShellView(
      index: _index,
      pages: _pages(),
      onSelected: (int value) => setState(() => _index = value),
      onLogout: widget.onLogout,
      onOpenFavorites: _openFavorites,
    );
  }
}
