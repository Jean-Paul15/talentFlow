import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import '../theme/app_theme.dart';

// ── Shared blurred background orb ──
class TfBlurredOrb extends StatelessWidget {
  const TfBlurredOrb({
    super.key,
    required this.size,
    required this.color,
    this.blur = 70,
  });

  final double size;
  final Color color;
  final double blur;

  @override
  Widget build(BuildContext context) {
    return ImageFiltered(
      imageFilter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
      ),
    );
  }
}

enum TfCardVariant { compact, standard, hero, glass }

class TfCard extends StatelessWidget {
  const TfCard({
    super.key,
    required this.child,
    this.variant = TfCardVariant.standard,
    this.padding,
    this.backgroundColor,
    this.borderColor,
    this.onTap,
  });

  final Widget child;
  final TfCardVariant variant;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isHero = variant == TfCardVariant.hero;
    final isCompact = variant == TfCardVariant.compact;
    final isGlass = variant == TfCardVariant.glass;

    final baseColor =
        backgroundColor ??
        (isHero
            ? Colors.white.withValues(alpha: 0.92)
            : isGlass
            ? Colors.white.withValues(alpha: 0.86)
            : Colors.white.withValues(alpha: 0.96));

    final content = Container(
      padding:
          padding ??
          EdgeInsets.all(
            isHero
                ? 20
                : isCompact
                ? 14
                : 16,
          ),
      decoration: BoxDecoration(
        color: baseColor,
        borderRadius: BorderRadius.circular(
          isHero ? AppTheme.radiusL : AppTheme.radiusL,
        ),
        border: Border.all(
          color:
              borderColor ??
              (isHero
                  ? AppTheme.cardBorder
                  : isGlass
                  ? AppTheme.cardBorder
                  : AppTheme.cardBorder),
        ),
        boxShadow: isHero ? AppTheme.elevatedShadow : AppTheme.softShadow,
      ),
      child: child,
    );

    final glass = isGlass
        ? ClipRRect(
            borderRadius: BorderRadius.circular(AppTheme.radiusL),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
              child: content,
            ),
          )
        : content;

    if (onTap == null) return glass;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTheme.radiusL),
      child: glass,
    );
  }
}

class TfPanel extends StatelessWidget {
  const TfPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.backgroundColor,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      padding: padding,
      backgroundColor: backgroundColor,
      variant: TfCardVariant.standard,
      child: child,
    );
  }
}

class TfSectionHeader extends StatelessWidget {
  const TfSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  final String title;
  final String? subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: theme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: AppTheme.ink,
                ),
              ),
              if ((subtitle ?? '').trim().isNotEmpty) ...<Widget>[
                const SizedBox(height: 4),
                Text(
                  subtitle!,
                  style: theme.bodySmall?.copyWith(color: AppTheme.inkSoft),
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) ...<Widget>[const SizedBox(width: 12), trailing!],
      ],
    );
  }
}

class TfPill extends StatelessWidget {
  const TfPill({
    super.key,
    required this.label,
    this.color = AppTheme.mist,
    this.foreground = AppTheme.ink,
    this.icon,
  });

  final String label;
  final Color color;
  final Color foreground;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(AppTheme.radiusS),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 13, color: foreground),
            const SizedBox(width: 5),
          ],
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: foreground,
              fontWeight: FontWeight.w700,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}

class TfMetricCard extends StatelessWidget {
  const TfMetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.accent = AppTheme.gold,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      variant: TfCardVariant.compact,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(AppTheme.radiusS),
            ),
            child: Icon(icon, color: accent, size: 16),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.displaySmall?.copyWith(fontSize: 28, height: 1),
          ),
          const SizedBox(height: 2),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class TfStat extends StatelessWidget {
  const TfStat({
    super.key,
    required this.value,
    required this.label,
    this.statusLabel,
    this.statusColor = AppTheme.success,
  });

  final String value;
  final String label;
  final String? statusLabel;
  final Color statusColor;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      variant: TfCardVariant.compact,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.displaySmall?.copyWith(fontSize: 28, height: 1),
          ),
          const SizedBox(height: 2),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          if ((statusLabel ?? '').trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Row(
              children: <Widget>[
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 5),
                Text(
                  statusLabel!,
                  style: Theme.of(
                    context,
                  ).textTheme.labelSmall?.copyWith(color: statusColor),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class TfProgressRing extends StatelessWidget {
  const TfProgressRing({
    super.key,
    required this.value,
    required this.label,
    this.size = 80,
    this.strokeWidth = 5,
    this.trackColor = AppTheme.cardBorder,
    this.color = AppTheme.gold,
  });

  final int value;
  final String label;
  final double size;
  final double strokeWidth;
  final Color trackColor;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final reduced = AppTheme.reducedMotion(context);
    final progress = value.clamp(0, 100) / 100;
    final ring = SizedBox(
      width: size,
      height: size,
      child: TweenAnimationBuilder<double>(
        duration: reduced ? Duration.zero : const Duration(milliseconds: 820),
        curve: Curves.easeOutCubic,
        tween: Tween<double>(begin: 0, end: progress),
        builder: (_, double animated, __) {
          return CustomPaint(
            painter: _TfProgressRingPainter(
              progress: animated,
              strokeWidth: strokeWidth,
              trackColor: trackColor,
              color: color,
            ),
            child: Center(
              child: Text(
                '$value%',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  fontSize: size >= 80 ? 18 : 14,
                ),
              ),
            ),
          );
        },
      ),
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        ring,
        const SizedBox(height: 6),
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.labelSmall?.copyWith(color: AppTheme.inkSoft),
        ),
      ],
    );
  }
}

class _TfProgressRingPainter extends CustomPainter {
  _TfProgressRingPainter({
    required this.progress,
    required this.strokeWidth,
    required this.trackColor,
    required this.color,
  });

  final double progress;
  final double strokeWidth;
  final Color trackColor;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final track = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(rect, -math.pi / 2, 2 * math.pi, false, track);

    if (progress <= 0) return;

    final arcPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      rect,
      -math.pi / 2,
      (2 * math.pi * progress).clamp(0, 2 * math.pi),
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _TfProgressRingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.strokeWidth != strokeWidth ||
        oldDelegate.trackColor != trackColor ||
        oldDelegate.color != color;
  }
}

class TfScoreCard extends StatelessWidget {
  const TfScoreCard({
    super.key,
    required this.label,
    required this.score,
    required this.caption,
    this.color = AppTheme.gold,
  });

  final String label;
  final int score;
  final String caption;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      variant: TfCardVariant.compact,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          TfProgressRing(
            value: score,
            label: label,
            size: 80,
            strokeWidth: 5,
            color: color,
          ),
          const SizedBox(height: 8),
          Text(caption, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class TfCallout extends StatelessWidget {
  const TfCallout({
    super.key,
    required this.title,
    required this.message,
    this.icon = PhosphorIconsRegular.info,
    this.color = AppTheme.teal,
  });

  final String title;
  final String message;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(AppTheme.radiusM),
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  message,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppTheme.inkSoft),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class TfBulletGroup extends StatelessWidget {
  const TfBulletGroup({
    super.key,
    required this.title,
    required this.items,
    this.icon,
    this.emptyMessage = 'Aucun point pour le moment.',
  });

  final String title;
  final List<String> items;
  final IconData? icon;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            if (icon != null) ...<Widget>[
              Icon(icon, size: 14, color: AppTheme.inkSoft),
              const SizedBox(width: 6),
            ],
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (items.isEmpty)
          Text(emptyMessage, style: Theme.of(context).textTheme.bodySmall)
        else
          ...items.map(
            (String item) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    margin: const EdgeInsets.only(top: 6),
                    width: 5,
                    height: 5,
                    decoration: const BoxDecoration(
                      color: AppTheme.gold,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class TfEmptyIllustration extends StatelessWidget {
  const TfEmptyIllustration({
    super.key,
    required this.title,
    required this.message,
    this.icon = PhosphorIconsRegular.sparkle,
    this.action,
  });

  final String title;
  final String message;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: AppTheme.mist,
                borderRadius: BorderRadius.circular(AppTheme.radiusL),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Icon(icon, color: AppTheme.inkSoft, size: 24),
            )
            .animate(target: 1)
            .fade(duration: 280.ms)
            .scale(begin: const Offset(0.94, 0.94), duration: 300.ms),
        const SizedBox(height: 12),
        Text(
          title,
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text(
          message,
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppTheme.inkSoft),
        ),
        if (action != null) ...<Widget>[const SizedBox(height: 14), action!],
      ],
    );
  }
}

class TfEmptyState extends StatelessWidget {
  const TfEmptyState({
    super.key,
    required this.title,
    required this.message,
    this.icon = PhosphorIconsRegular.magnifyingGlass,
    this.action,
  });

  final String title;
  final String message;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return TfCard(
      padding: const EdgeInsets.all(24),
      child: TfEmptyIllustration(
        title: title,
        message: message,
        icon: icon,
        action: action,
      ),
    );
  }
}

class TfReveal extends StatefulWidget {
  const TfReveal({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.duration = const Duration(milliseconds: 250),
    this.offset = const Offset(0, 0.03),
  });

  final Widget child;
  final Duration delay;
  final Duration duration;
  final Offset offset;

  @override
  State<TfReveal> createState() => _TfRevealState();
}

class _TfRevealState extends State<TfReveal>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _opacity;
  late final Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: widget.duration);
    _opacity = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _slide = Tween<Offset>(
      begin: widget.offset,
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic));
    _play();
  }

  Future<void> _play() async {
    if (widget.delay > Duration.zero) {
      await Future<void>.delayed(widget.delay);
    }
    if (!mounted) return;
    if (AppTheme.reducedMotion(context)) {
      _ctrl.value = 1;
      return;
    }
    _ctrl.forward();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: SlideTransition(position: _slide, child: widget.child),
    );
  }
}

class TfSkeletonBlock extends StatefulWidget {
  const TfSkeletonBlock({
    super.key,
    this.width,
    this.height = 14,
    this.radius = 8,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  State<TfSkeletonBlock> createState() => _TfSkeletonBlockState();
}

class _TfSkeletonBlockState extends State<TfSkeletonBlock>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        final alpha = 0.34 + (_ctrl.value * 0.24);
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            color: AppTheme.cardBorder.withValues(alpha: alpha),
            borderRadius: BorderRadius.circular(widget.radius),
          ),
        );
      },
    );
  }
}

class TfPressable extends StatefulWidget {
  const TfPressable({
    super.key,
    required this.child,
    required this.onTap,
    this.borderRadius = const BorderRadius.all(Radius.circular(16)),
  });

  final Widget child;
  final VoidCallback onTap;
  final BorderRadius borderRadius;

  @override
  State<TfPressable> createState() => _TfPressableState();
}

class _TfPressableState extends State<TfPressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      onTap: () {
        HapticFeedback.selectionClick();
        widget.onTap();
      },
      child: AnimatedScale(
        duration: const Duration(milliseconds: 140),
        scale: _pressed ? 0.988 : 1,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 140),
          opacity: _pressed ? 0.94 : 1,
          child: ClipRRect(
            borderRadius: widget.borderRadius,
            child: widget.child,
          ),
        ),
      ),
    );
  }
}

class TfActionTile extends StatelessWidget {
  const TfActionTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.accent = AppTheme.gold,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return TfPressable(
      onTap: onTap,
      child: TfCard(
        variant: TfCardVariant.compact,
        child: Row(
          children: <Widget>[
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(AppTheme.radiusS),
              ),
              child: Icon(icon, color: accent, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              PhosphorIconsRegular.caretRight,
              size: 16,
              color: AppTheme.inkMuted,
            ),
          ],
        ),
      ),
    );
  }
}

class TfJobCard extends StatelessWidget {
  const TfJobCard({
    super.key,
    required this.title,
    required this.contextLine,
    required this.matchLabel,
    required this.dateLabel,
    this.favorite,
    this.onTap,
  });

  final String title;
  final String contextLine;
  final String matchLabel;
  final String dateLabel;
  final Widget? favorite;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return TfPressable(
      onTap: onTap ?? () {},
      child: TfCard(
        variant: TfCardVariant.compact,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              contextLine,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Text(
                  matchLabel,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: AppTheme.goldDark,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(width: 8),
                Text(dateLabel, style: Theme.of(context).textTheme.bodySmall),
                const Spacer(),
                favorite ??
                    const Icon(
                      PhosphorIconsRegular.heart,
                      size: 16,
                      color: AppTheme.inkMuted,
                    ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class TfChipBar extends StatelessWidget {
  const TfChipBar({
    super.key,
    required this.items,
    this.onTap,
    this.activeValue,
  });

  final List<String> items;
  final ValueChanged<String>? onTap;
  final String? activeValue;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 34,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (_, int index) {
          final value = items[index];
          final active = activeValue == value;
          return InkWell(
            borderRadius: BorderRadius.circular(AppTheme.radiusS),
            onTap: onTap == null ? null : () => onTap!(value),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: active
                    ? AppTheme.gold.withValues(alpha: 0.12)
                    : AppTheme.mist,
                borderRadius: BorderRadius.circular(AppTheme.radiusS),
                border: Border.all(
                  color: active
                      ? AppTheme.gold.withValues(alpha: 0.25)
                      : AppTheme.cardBorder,
                ),
              ),
              child: Text(
                value,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: active ? AppTheme.goldDark : AppTheme.inkSoft,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class TfBottomSheet {
  static Future<T?> show<T>({
    required BuildContext context,
    required String title,
    required Widget child,
    Widget? primaryAction,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      useSafeArea: true,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) {
        return Container(
          decoration: BoxDecoration(
            color: AppTheme.paper,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const SizedBox(height: 8),
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: AppTheme.cardBorder,
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 12, 6),
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(PhosphorIconsRegular.x, size: 18),
                    ),
                  ],
                ),
              ),
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                  child: child,
                ),
              ),
              if (primaryAction != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
                  child: primaryAction,
                ),
            ],
          ),
        );
      },
    );
  }
}
