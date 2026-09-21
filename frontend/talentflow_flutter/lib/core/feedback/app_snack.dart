import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import '../theme/app_theme.dart';

enum AppSnackType { success, info, warning, error }

class AppSnack {
  static void show(
    BuildContext context, {
    required String message,
    AppSnackType type = AppSnackType.info,
    Duration duration = const Duration(seconds: 3),
  }) {
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();

    final style = _style(type);
    messenger.showSnackBar(
      SnackBar(
        duration: duration,
        behavior: SnackBarBehavior.floating,
        elevation: 0,
        backgroundColor: Colors.transparent,
        margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        content: Container(
          decoration: BoxDecoration(
            color: style.background,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: style.border),
            boxShadow: AppTheme.softShadow,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: <Widget>[
              Icon(style.icon, size: 18, color: style.foreground),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  message,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: style.foreground,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static _SnackStyle _style(AppSnackType type) {
    switch (type) {
      case AppSnackType.success:
        return const _SnackStyle(
          background: Color(0xFFEAFBF1),
          border: Color(0xFFB8E8CA),
          foreground: Color(0xFF0C7A35),
          icon: PhosphorIconsBold.checkCircle,
        );
      case AppSnackType.warning:
        return const _SnackStyle(
          background: Color(0xFFFFF7E6),
          border: Color(0xFFF5D99B),
          foreground: Color(0xFF8A5B12),
          icon: PhosphorIconsBold.warningCircle,
        );
      case AppSnackType.error:
        return const _SnackStyle(
          background: Color(0xFFFFECEB),
          border: Color(0xFFF4B5B1),
          foreground: Color(0xFFB42318),
          icon: PhosphorIconsBold.xCircle,
        );
      case AppSnackType.info:
        return const _SnackStyle(
          background: Color(0xFFEAF5FF),
          border: Color(0xFFB7D8F6),
          foreground: Color(0xFF145DA0),
          icon: PhosphorIconsBold.info,
        );
    }
  }
}

class _SnackStyle {
  const _SnackStyle({
    required this.background,
    required this.border,
    required this.foreground,
    required this.icon,
  });

  final Color background;
  final Color border;
  final Color foreground;
  final IconData icon;
}
