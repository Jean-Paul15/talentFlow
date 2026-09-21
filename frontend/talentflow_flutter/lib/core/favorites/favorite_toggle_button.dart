import 'package:flutter/material.dart';

import '../feedback/app_snack.dart';
import '../theme/app_theme.dart';
import 'favorites_store.dart';

class FavoriteToggleButton extends StatefulWidget {
  const FavoriteToggleButton({
    super.key,
    required this.token,
    required this.job,
    this.initialValue,
    this.compact = false,
    this.onChanged,
  });

  final String token;
  final Map<String, dynamic> job;
  final bool? initialValue;
  final bool compact;
  final ValueChanged<bool>? onChanged;

  @override
  State<FavoriteToggleButton> createState() => _FavoriteToggleButtonState();
}

class _FavoriteToggleButtonState extends State<FavoriteToggleButton> {
  final FavoritesStore _store = FavoritesStore();
  bool _loading = false;
  bool _favorite = false;
  bool _resolved = false;

  String get _jobId =>
      (widget.job['jobId'] ?? widget.job['id'] ?? '').toString().trim();

  @override
  void initState() {
    super.initState();
    if (widget.initialValue != null) {
      _favorite = widget.initialValue!;
      _resolved = true;
    } else {
      _resolve();
    }
  }

  Future<void> _resolve() async {
    if (_jobId.isEmpty) {
      if (!mounted) return;
      setState(() => _resolved = true);
      return;
    }
    try {
      final value = await _store.isFavorite(token: widget.token, jobId: _jobId);
      if (!mounted) return;
      setState(() {
        _favorite = value;
        _resolved = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _resolved = true);
    }
  }

  Future<void> _toggle() async {
    if (_jobId.isEmpty || _loading) return;
    setState(() => _loading = true);
    try {
      if (_favorite) {
        await _store.remove(token: widget.token, jobId: _jobId);
      } else {
        await _store.save(token: widget.token, job: widget.job);
      }
      if (!mounted) return;
      final next = !_favorite;
      setState(() => _favorite = next);
      widget.onChanged?.call(next);
      AppSnack.show(
        context,
        message: next ? 'Offre ajoutée aux favoris.' : 'Offre retirée des favoris.',
        type: AppSnackType.success,
      );
    } catch (e) {
      if (!mounted) return;
      AppSnack.show(
        context,
        message: e.toString().replaceFirst('Exception: ', ''),
        type: AppSnackType.error,
      );
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isActive = _favorite;
    final icon = _loading
        ? const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Icon(
            isActive ? Icons.favorite : Icons.favorite_border,
            color: isActive ? AppTheme.coral : null,
          );

    if (widget.compact) {
      return IconButton(
        tooltip: isActive ? 'Retirer des favoris' : 'Ajouter aux favoris',
        onPressed: (!_resolved || _loading || _jobId.isEmpty) ? null : _toggle,
        icon: icon,
      );
    }

    return FilledButton.tonalIcon(
      onPressed: (!_resolved || _loading || _jobId.isEmpty) ? null : _toggle,
      icon: icon,
      label: Text(isActive ? 'Favori' : 'Ajouter aux favoris'),
    );
  }
}

