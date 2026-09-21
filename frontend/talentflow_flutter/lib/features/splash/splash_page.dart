import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/tf_lottie_loader.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key, required this.onDone});

  final VoidCallback onDone;

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> with TickerProviderStateMixin {
  late final AnimationController _logoCtrl;
  late final AnimationController _loaderCtrl;

  late final Animation<double> _logoFade;
  late final Animation<double> _logoScale;

  @override
  void initState() {
    super.initState();

    _logoCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _logoFade = CurvedAnimation(
      parent: _logoCtrl,
      curve: const Interval(0.08, 1.0, curve: Curves.easeOut),
    );
    _logoScale = Tween<double>(begin: 0.78, end: 1.0).animate(
      CurvedAnimation(parent: _logoCtrl, curve: Curves.elasticOut),
    );

    _loaderCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();

    _startSequence();
  }

  Future<void> _startSequence() async {
    await Future<void>.delayed(const Duration(milliseconds: 90));
    if (!mounted) return;
    _logoCtrl.forward();

    await Future<void>.delayed(const Duration(milliseconds: 1800));
    if (!mounted) return;
    widget.onDone();
  }

  @override
  void dispose() {
    _logoCtrl.dispose();
    _loaderCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        children: <Widget>[
          _SplashAmbientBackdrop(animation: _loaderCtrl),
          SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    FadeTransition(
                      opacity: _logoFade,
                      child: ScaleTransition(
                        scale: _logoScale,
                        child: const _LogoBadge(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'TalentFlow',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontSize: 30,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -1.0,
                            color: AppTheme.ink,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Espace candidature intelligent',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppTheme.inkSoft,
                            fontSize: 15,
                            height: 1.35,
                          ),
                    ),
                    const SizedBox(height: 26),
                    const TfLottieLoader(width: 84, height: 28),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SplashAmbientBackdrop extends StatelessWidget {
  const _SplashAmbientBackdrop({required this.animation});

  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (_, __) {
        final t = animation.value;
        final driftX = math.sin(t * math.pi * 2) * 10;
        final driftY = math.cos(t * math.pi * 2) * 8;

        return Stack(
          children: <Widget>[
            Positioned(
              top: -130 + driftY,
              right: -110 + driftX,
              child: TfBlurredOrb(
                size: 300,
                color: AppTheme.gold.withValues(alpha: 0.08),
                blur: 88,
              ),
            ),
            Positioned(
              bottom: -120 - driftY,
              left: -120 - driftX,
              child: TfBlurredOrb(
                size: 280,
                color: AppTheme.teal.withValues(alpha: 0.06),
                blur: 90,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _LogoBadge extends StatelessWidget {
  const _LogoBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 112,
      height: 112,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: Colors.white,
        border: Border.all(color: AppTheme.cardBorder),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppTheme.gold.withValues(alpha: 0.16),
            blurRadius: 38,
            spreadRadius: 1,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Center(
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Image.asset(
            'assets/images/logo.png',
            width: 88,
            height: 88,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: AppTheme.mist,
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.auto_awesome,
                color: AppTheme.goldDark,
                size: 34,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

