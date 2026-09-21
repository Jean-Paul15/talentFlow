
import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

import 'home_page_data.dart';
import 'home_page_loading_state.dart';

class HomePageView extends StatelessWidget {
  const HomePageView({
    super.key,
    required this.loading,
    required this.error,
    required this.me,
    required this.latestReco,
    required this.favoriteCount,
    required this.fallbackEmail,
    required this.onRefresh,
    required this.onNavigate,
    required this.onOpenFavorites,
  });

  final bool loading;
  final String? error;
  final Map<String, dynamic> me;
  final Map<String, dynamic>? latestReco;
  final int favoriteCount;
  final String fallbackEmail;
  final Future<void> Function() onRefresh;
  final ValueChanged<int> onNavigate;
  final VoidCallback onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    final assistant =
        latestReco?['assistantStructured'] as Map<String, dynamic>?;
    final ats = latestReco?['atsLite'] as Map<String, dynamic>?;
    final name =
        ((me['name'] ?? '').toString().trim().isEmpty
                ? (me['email'] ?? fallbackEmail).toString().split('@').first
                : (me['name'] ?? '').toString())
            .trim();
    final summary = (assistant?['profileSummary'] ?? '').toString();
    final mode = (assistant?['mode'] ?? '').toString();
    final watchlist = watchlistQueriesOf(me, latestReco);
    final profileCompleteness = profileCompletenessOf(me);
    final score = (ats?['overallScore'] ?? 0) as int;
    final actionPlan = actionPlanOf(ats, assistant).take(4).toList();
    final jobs = (latestReco?['jobs'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .take(4)
        .toList();

    return RefreshIndicator(
      onRefresh: onRefresh,
      color: AppTheme.coral,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 22),
        children: <Widget>[
          TfReveal(
            delay: const Duration(milliseconds: 60),
            child: _HomeHero(
              name: name,
              summary: summary,
              onAnalyze: () => onNavigate(2),
              onExplore: () => onNavigate(1),
              onOpenFavorites: onOpenFavorites,
            ),
          ),
          const SizedBox(height: 12),
          TfReveal(
            delay: const Duration(milliseconds: 150),
            child: _MetricsGrid(
              score: score,
              profileCompleteness: profileCompleteness,
              favoriteCount: favoriteCount,
              offerCount: mode == 'no_match' ? 0 : jobs.length,
              noMatch: mode == 'no_match',
            ),
          ),
          const SizedBox(height: 12),
          if (loading) ...<Widget>[
            const HomeLoadingState(),
            const SizedBox(height: 12),
          ],
          if ((error ?? '').isNotEmpty) ...<Widget>[
            TfCallout(
              title: 'Chargement partiel',
              message: error!,
              icon: PhosphorIconsRegular.warning,
              color: AppTheme.warning,
            ),
            const SizedBox(height: 12),
          ],
          TfReveal(
            delay: const Duration(milliseconds: 240),
            child: _SectionCard(
              title: 'Plan d’action',
              icon: PhosphorIconsBold.lightning,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  AppTheme.coral.withValues(alpha: 0.12),
                  const Color(0xFFF7EFE2),
                ],
              ),
              borderColor: AppTheme.coral.withValues(alpha: 0.22),
              iconColor: AppTheme.coral,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: actionPlan.isEmpty
                    ? <Widget>[
                        Text(
                          'Lance une analyse CV pour activer tes recommandations.',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: AppTheme.inkSoft,
                                height: 1.45,
                              ),
                        ),
                      ]
                    : actionPlan
                        .asMap()
                        .entries
                        .map(
                          (e) => _NumberedItem(index: e.key, text: e.value),
                        )
                        .toList(),
              ),
            ),
          ),
          const SizedBox(height: 10),
          if (watchlist.isNotEmpty) ...<Widget>[
            TfReveal(
              delay: const Duration(milliseconds: 330),
              child: _SectionCard(
                title: 'Veille ciblée',
                icon: PhosphorIconsBold.binoculars,
                iconColor: AppTheme.inkMuted,
                child: TfChipBar(items: watchlist, onTap: (_) => onNavigate(1)),
              ),
            ),
            const SizedBox(height: 10),
          ],
          TfReveal(
            delay: const Duration(milliseconds: 440),
            child: _SectionCard(
              title: 'Offres suggérées',
              icon: PhosphorIconsBold.briefcase,
              iconColor: AppTheme.inkMuted,
              trailing: TextButton(
                onPressed: () => onNavigate(1),
                style: TextButton.styleFrom(
                  foregroundColor: AppTheme.coral,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  minimumSize: const Size(0, 28),
                ),
                child: const Text('Tout voir'),
              ),
              child: jobs.isEmpty
                  ? const TfEmptyIllustration(
                      title: 'Aucune offre',
                      message: 'Lance une recherche ou une analyse CV.',
                      icon: PhosphorIconsRegular.briefcase,
                    )
                  : SizedBox(
                      height: 154,
                      child: ListView.separated(
                        scrollDirection: Axis.horizontal,
                        itemCount: jobs.length,
                        separatorBuilder: (_, __) => const SizedBox(width: 10),
                        itemBuilder: (_, i) {
                          final job = jobs[i];
                          final title = (job['title'] ?? '').toString();
                          final company = (job['company'] ?? '').toString();
                          final location = (job['location'] ?? '').toString();
                          final scoreRaw = job['score'];
                          final scorePercent = scoreRaw is num
                              ? (scoreRaw <= 1 ? (scoreRaw * 100) : scoreRaw)
                                    .round()
                                    .clamp(0, 100)
                              : 0;
                          return SizedBox(
                            width: 226,
                            child: TfJobCard(
                              title: title,
                              contextLine: <String>[
                                company,
                                location,
                              ].where((e) => e.isNotEmpty).join(' · '),
                              matchLabel: 'Match $scorePercent%',
                              dateLabel: 'Récent',
                              onTap: () => onNavigate(1),
                            ),
                          );
                        },
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HomeHero extends StatelessWidget {
  const _HomeHero({
    required this.name,
    required this.summary,
    required this.onAnalyze,
    required this.onExplore,
    required this.onOpenFavorites,
  });

  final String name;
  final String summary;
  final VoidCallback onAnalyze;
  final VoidCallback onExplore;
  final VoidCallback onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: const Color(0xFFE7DED4)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(26),
        child: Stack(
          children: <Widget>[
            Positioned(
              top: -52,
              right: -36,
              child: _HeroOrb(
                size: 170,
                color: AppTheme.coral.withValues(alpha: 0.10),
              ),
            ),
            Positioned(
              bottom: -58,
              left: -44,
              child: _HeroOrb(
                size: 160,
                color: const Color(0xFFF0D48A).withValues(alpha: 0.14),
              ),
            ),
            Container(
              decoration: const BoxDecoration(
                border: Border(
                  left: BorderSide(color: AppTheme.coral, width: 4),
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    TfPill(
                      label: 'Recommandations live',
                      color: AppTheme.coral.withValues(alpha: 0.12),
                      foreground: AppTheme.coral,
                      icon: PhosphorIconsBold.sparkle,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Bonjour, $name',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            height: 1.05,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      summary.isEmpty
                          ? 'Analyse ton CV et avance sur les offres qui comptent.'
                          : summary,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppTheme.inkSoft,
                            height: 1.5,
                          ),
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        SizedBox(
                          height: 46,
                          child: FilledButton.icon(
                            onPressed: onAnalyze,
                            style: FilledButton.styleFrom(
                              backgroundColor: AppTheme.coral,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                              textStyle: Theme.of(context)
                                  .textTheme
                                  .labelLarge
                                  ?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            icon: const Icon(
                              PhosphorIconsBold.fileText,
                              size: 16,
                            ),
                            label: const Text('Analyser CV'),
                          ),
                        ),
                        SizedBox(
                          height: 46,
                          child: OutlinedButton(
                            onPressed: onExplore,
                            style: OutlinedButton.styleFrom(
                              foregroundColor: AppTheme.ink,
                              side: const BorderSide(color: Color(0xFFE1D6CA)),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                              textStyle: Theme.of(context)
                                  .textTheme
                                  .labelLarge
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                            child: const Text('Explorer'),
                          ),
                        ),
                        SizedBox(
                          height: 46,
                          width: 46,
                          child: IconButton(
                            onPressed: onOpenFavorites,
                            style: IconButton.styleFrom(
                              backgroundColor: AppTheme.mist,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                                side: const BorderSide(
                                  color: Color(0xFFE1D6CA),
                                ),
                              ),
                            ),
                            icon: const Icon(
                              PhosphorIconsRegular.heart,
                              size: 18,
                              color: AppTheme.ink,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({
    required this.score,
    required this.profileCompleteness,
    required this.favoriteCount,
    required this.offerCount,
    required this.noMatch,
  });

  final int score;
  final int profileCompleteness;
  final int favoriteCount;
  final int offerCount;
  final bool noMatch;

  @override
  Widget build(BuildContext context) {
    final metrics = <Widget>[
      _Metric(
        label: 'ATS',
        value: score,
        suffix: '%',
        icon: PhosphorIconsBold.chartDonut,
        accent: AppTheme.coral,
      ),
      _Metric(
        label: 'Profil',
        value: profileCompleteness,
        suffix: '%',
        icon: PhosphorIconsBold.userCircle,
        accent: AppTheme.teal,
      ),
      _Metric(
        label: 'Favoris',
        value: favoriteCount,
        icon: PhosphorIconsBold.heart,
        accent: AppTheme.goldDark,
      ),
      _Metric(
        label: noMatch ? 'À renforcer' : 'Offres',
        value: offerCount,
        icon: PhosphorIconsBold.briefcase,
        accent: noMatch ? AppTheme.warning : AppTheme.success,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 620;
        final spacing = 8.0;
        final width = narrow
            ? (constraints.maxWidth - spacing) / 2
            : (constraints.maxWidth - (spacing * 3)) / 4;
        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: metrics
              .map((metric) => SizedBox(width: width, child: metric))
              .toList(),
        );
      },
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
    this.suffix = '',
  });

  final String label;
  final int value;
  final IconData icon;
  final Color accent;
  final String suffix;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: accent, size: 16),
          ),
          const SizedBox(height: 10),
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0, end: value.toDouble()),
            duration: const Duration(milliseconds: 900),
            curve: Curves.easeOutCubic,
            builder: (context, animated, _) {
              final display = value == value.round()
                  ? animated.round().toString()
                  : animated.toStringAsFixed(0);
              return Text(
                '$display$suffix',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      height: 1,
                      fontFeatures: const <FontFeature>[
                        FontFeature.tabularFigures(),
                      ],
                    ),
              );
            },
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  fontSize: 11,
                  color: AppTheme.inkSoft,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
    this.trailing,
    this.gradient,
    this.borderColor,
    this.iconColor = AppTheme.inkSoft,
  });

  final String title;
  final IconData icon;
  final Widget child;
  final Widget? trailing;
  final Gradient? gradient;
  final Color? borderColor;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: gradient == null ? Colors.white : null,
        gradient: gradient,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: borderColor ?? const Color(0xFFE7DED4)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 20,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, size: 15, color: iconColor),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _NumberedItem extends StatelessWidget {
  const _NumberedItem({required this.index, required this.text});

  final int index;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            margin: const EdgeInsets.only(top: 2),
            width: 22,
            height: 22,
            decoration: BoxDecoration(
              color: AppTheme.coral.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '${index + 1}',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppTheme.coral,
                      fontWeight: FontWeight.w800,
                      fontSize: 10,
                    ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppTheme.ink,
                    fontSize: 13,
                    height: 1.45,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroOrb extends StatelessWidget {
  const _HeroOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: <Color>[
            color,
            color.withValues(alpha: 0.02),
          ],
        ),
      ),
    );
  }
}


