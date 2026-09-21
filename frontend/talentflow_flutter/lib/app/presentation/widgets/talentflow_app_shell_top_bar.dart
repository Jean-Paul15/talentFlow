import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';

class TalentFlowTopBar extends StatelessWidget {
  const TalentFlowTopBar({
    super.key,
    required this.compact,
    required this.onLogout,
    required this.onOpenFavorites,
  });

  final bool compact;
  final Future<void> Function() onLogout;
  final Future<void> Function() onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(compact ? 4 : 0, 4, compact ? 4 : 0, 0),
      child: Row(
        children: <Widget>[
          const _BrandLogo(size: 28),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'TalentFlow',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: AppTheme.ink,
                    ),
              ),
              if (!compact)
                Text(
                  'Candidatures plus lisibles',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: AppTheme.inkSoft,
                        fontSize: 11,
                      ),
                ),
            ],
          ),
          const Spacer(),
          IconButton(
            tooltip: 'Favoris',
            onPressed: () {
              HapticFeedback.lightImpact();
              onOpenFavorites();
            },
            style: IconButton.styleFrom(
              backgroundColor: AppTheme.mist,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppTheme.radiusS),
              ),
            ),
            icon: const Icon(
              PhosphorIconsRegular.heart,
              size: 18,
              color: AppTheme.inkSoft,
            ),
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
          const SizedBox(width: 4),
          IconButton(
            tooltip: 'Déconnexion',
            onPressed: () {
              HapticFeedback.mediumImpact();
              onLogout();
            },
            style: IconButton.styleFrom(
              backgroundColor: AppTheme.mist,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppTheme.radiusS),
              ),
            ),
            icon: const Icon(
              PhosphorIconsRegular.signOut,
              size: 18,
              color: AppTheme.inkSoft,
            ),
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
        ],
      ),
    );
  }
}

class _BrandLogo extends StatelessWidget {
  const _BrandLogo({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/images/logo.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => Image.asset(
        'assets/images/logo.png',
        width: size,
        height: size,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => Icon(
          PhosphorIconsRegular.briefcaseMetal,
          size: size,
          color: AppTheme.inkSoft,
        ),
      ),
    );
  }
}
