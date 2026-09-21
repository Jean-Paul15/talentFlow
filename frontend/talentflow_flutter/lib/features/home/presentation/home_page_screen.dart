import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/cache/cache_runtime_service.dart';
import 'package:talentflow_flutter/core/feedback/app_snack.dart';

import 'widgets/home_page_snapshot_loader.dart';
import 'widgets/home_page_view.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.token,
    required this.fallbackEmail,
    required this.fallbackName,
    required this.onNavigate,
    required this.onOpenFavorites,
  });

  final String token;
  final String fallbackEmail;
  final String fallbackName;
  final ValueChanged<int> onNavigate;
  final VoidCallback onOpenFavorites;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _loading = true;
  Map<String, dynamic>? _me;
  Map<String, dynamic>? _latestReco;
  int _favoriteCount = 0;

  @override
  void initState() {
    super.initState();
    CacheRuntimeService.changeTick.addListener(_onCacheVersionChanged);
    _loadSnapshot();
  }

  @override
  void dispose() {
    CacheRuntimeService.changeTick.removeListener(_onCacheVersionChanged);
    super.dispose();
  }

  void _onCacheVersionChanged() {
    if (!mounted) return;
    _loadSnapshot(silent: true);
  }

  Future<void> _loadSnapshot({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
      });
    }

    final cached = await loadHomePageSnapshotCached();
    if (cached != null && mounted) {
      setState(() {
        _me = cached.me;
        _latestReco = cached.latestReco;
        _favoriteCount = cached.favoriteCount;
        _loading = false;
      });
    }

    try {
      final snapshot = await loadHomePageSnapshot(token: widget.token);
      if (!mounted) return;
      setState(() {
        _me = snapshot.me;
        _latestReco = snapshot.latestReco;
        _favoriteCount = snapshot.favoriteCount;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      final message = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _loading = false;
      });
      AppSnack.show(context, message: message, type: AppSnackType.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    return HomePageView(
      loading: _loading,
      error: null,
      me: _me ?? <String, dynamic>{},
      latestReco: _latestReco,
      favoriteCount: _favoriteCount,
      fallbackEmail: widget.fallbackEmail,
      onRefresh: _loadSnapshot,
      onNavigate: widget.onNavigate,
      onOpenFavorites: widget.onOpenFavorites,
    );
  }
}
