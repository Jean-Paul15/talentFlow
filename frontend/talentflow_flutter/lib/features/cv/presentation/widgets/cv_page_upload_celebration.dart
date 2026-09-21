import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';

class CvUploadCelebration extends StatefulWidget {
  const CvUploadCelebration({
    super.key,
    required this.trigger,
  });

  final int trigger;

  @override
  State<CvUploadCelebration> createState() => _CvUploadCelebrationState();
}

class _CvUploadCelebrationState extends State<CvUploadCelebration>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );

  @override
  void didUpdateWidget(covariant CvUploadCelebration oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.trigger != oldWidget.trigger && widget.trigger > 0) {
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: CurvedAnimation(
          parent: _controller,
          curve: Curves.easeOutCubic,
        ),
        builder: (context, _) {
          final t = _controller.value;
          if (t == 0) return const SizedBox.shrink();
          return Stack(
            children: <Widget>[
              _BurstIcon(
                top: 4 - (t * 28),
                left: 16 + (t * 10),
                angle: -0.45,
                opacity: 1 - t,
                icon: PhosphorIconsFill.sparkle,
                color: AppTheme.goldDark,
              ),
              _BurstIcon(
                top: 18 - (t * 34),
                right: 24 + (t * 8),
                angle: 0.4,
                opacity: 1 - t,
                icon: PhosphorIconsFill.confetti,
                color: AppTheme.teal,
              ),
              _BurstIcon(
                top: 42 - (t * 32),
                left: 58 - (t * 18),
                angle: -0.2,
                opacity: 1 - t,
                icon: PhosphorIconsFill.starFour,
                color: AppTheme.coral,
              ),
              _BurstIcon(
                top: 52 - (t * 30),
                right: 72 - (t * 14),
                angle: 0.18,
                opacity: 1 - t,
                icon: PhosphorIconsFill.sparkle,
                color: AppTheme.warning,
              ),
            ],
          );
        },
      ),
    );
  }
}

class _BurstIcon extends StatelessWidget {
  const _BurstIcon({
    this.top,
    this.left,
    this.right,
    required this.angle,
    required this.opacity,
    required this.icon,
    required this.color,
  });

  final double? top;
  final double? left;
  final double? right;
  final double angle;
  final double opacity;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: top,
      left: left,
      right: right,
      child: Transform.rotate(
        angle: angle,
        child: Opacity(
          opacity: opacity.clamp(0, 1),
          child: Icon(icon, size: 18, color: color),
        ),
      ),
    );
  }
}
