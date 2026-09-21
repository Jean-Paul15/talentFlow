import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key, required this.onDone});

  final VoidCallback onDone;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage>
    with SingleTickerProviderStateMixin {
  final PageController _controller = PageController();
  int _index = 0;

  late final AnimationController _contentCtrl;
  late final Animation<double> _contentFade;
  late final Animation<Offset> _contentSlide;

  static const _slides = <_Slide>[
    _Slide(
      icon: PhosphorIconsBold.fileText,
      title: 'Analyse ton CV en quelques secondes',
      subtitle:
          'On repère tes points forts et ce que tu peux améliorer avant d’envoyer.',
      backgroundGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFFFFF7F1),
          Color(0xFFFFE7DA),
        ],
      ),
      accent: Color(0xFFE85D3F),
      heroGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFFFF8A67),
          Color(0xFFE84C2F),
        ],
      ),
      halo: Color(0x33E85D3F),
      ctaForeground: Colors.white,
    ),
    _Slide(
      icon: PhosphorIconsBold.target,
      title: 'Reçois des offres vraiment ciblées',
      subtitle:
          'On privilégie la pertinence, pas la quantité, pour éviter les faux matchs.',
      backgroundGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFFF2FBF5),
          Color(0xFFD9F1E5),
        ],
      ),
      accent: Color(0xFF2E7A57),
      heroGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFF53A275),
          Color(0xFF226745),
        ],
      ),
      halo: Color(0x332E7A57),
      ctaForeground: Colors.white,
    ),
    _Slide(
      icon: PhosphorIconsBold.listChecks,
      title: 'Passe à l’action avec un plan clair',
      subtitle: 'Tu repars avec des étapes concrètes à suivre sur 7 jours.',
      backgroundGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFFFFF8E7),
          Color(0xFFFFE5B0),
        ],
      ),
      accent: Color(0xFFC98A0C),
      heroGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[
          Color(0xFFF6B633),
          Color(0xFFC88600),
        ],
      ),
      halo: Color(0x33C98A0C),
      ctaForeground: AppTheme.ink,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _contentCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 380),
    );
    _contentFade = CurvedAnimation(
      parent: _contentCtrl,
      curve: Curves.easeOut,
    );
    _contentSlide =
        Tween<Offset>(begin: const Offset(0, 0.08), end: Offset.zero).animate(
          CurvedAnimation(parent: _contentCtrl, curve: Curves.easeOutCubic),
        );
    _contentCtrl.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    _contentCtrl.dispose();
    super.dispose();
  }

  void _onPageChanged(int value) {
    setState(() => _index = value);
    _contentCtrl
      ..reset()
      ..forward();
  }

  void _next() {
    HapticFeedback.selectionClick();
    if (_index == _slides.length - 1) {
      widget.onDone();
      return;
    }
    _controller.nextPage(
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    final slide = _slides[_index];
    final isLast = _index == _slides.length - 1;

    return Scaffold(
      backgroundColor: AppTheme.paper,
      body: AnimatedContainer(
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeOutCubic,
        decoration: BoxDecoration(gradient: slide.backgroundGradient),
        child: Stack(
          children: <Widget>[
            _OnboardingAmbientBackdrop(
              slide: slide,
              animation: _contentCtrl,
            ),
            SafeArea(
              child: Column(
                children: <Widget>[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 10, 10, 4),
                    child: Row(
                      children: <Widget>[
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.asset(
                            'assets/images/logo.png',
                            width: 30,
                            height: 30,
                            fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) =>
                                const SizedBox(width: 30, height: 30),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'TalentFlow',
                          style: Theme.of(context).textTheme.labelMedium
                              ?.copyWith(
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.15,
                              ),
                        ),
                        const Spacer(),
                        TextButton(
                          onPressed: widget.onDone,
                          style: TextButton.styleFrom(
                            foregroundColor: AppTheme.inkSoft,
                          ),
                          child: const Text('Passer'),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: PageView.builder(
                      controller: _controller,
                      itemCount: _slides.length,
                      onPageChanged: _onPageChanged,
                      itemBuilder: (context, i) {
                        final current = _slides[i];
                        return Padding(
                          padding: const EdgeInsets.fromLTRB(22, 12, 22, 0),
                          child: Column(
                            children: <Widget>[
                              const Spacer(flex: 2),
                              _SlideIllustration(
                                slide: current,
                                active: i == _index,
                              ),
                              const SizedBox(height: 26),
                              FadeTransition(
                                opacity: _contentFade,
                                child: SlideTransition(
                                  position: _contentSlide,
                                  child: Column(
                                    children: <Widget>[
                                      Text(
                                        current.title,
                                        textAlign: TextAlign.center,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge
                                            ?.copyWith(
                                              fontSize: 27,
                                              height: 1.12,
                                              fontWeight: FontWeight.w700,
                                            ),
                                      ),
                                      const SizedBox(height: 12),
                                      Text(
                                        current.subtitle,
                                        textAlign: TextAlign.center,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyLarge
                                            ?.copyWith(
                                              color: AppTheme.inkSoft,
                                              height: 1.48,
                                            ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const Spacer(flex: 3),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                    child: Row(
                      children: <Widget>[
                        Row(
                          children: List<Widget>.generate(_slides.length, (i) {
                            final active = i == _index;
                            return AnimatedContainer(
                              duration: const Duration(milliseconds: 240),
                              curve: Curves.easeOutCubic,
                              margin: const EdgeInsets.only(right: 6),
                              width: active ? 24 : 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: active
                                    ? slide.accent
                                    : AppTheme.cardBorder,
                                borderRadius: BorderRadius.circular(999),
                              ),
                            );
                          }),
                        ),
                        const Spacer(),
                        FilledButton.icon(
                          onPressed: _next,
                          style: FilledButton.styleFrom(
                            backgroundColor: slide.accent,
                            foregroundColor: slide.ctaForeground,
                            minimumSize: const Size(0, 48),
                            padding: const EdgeInsets.symmetric(horizontal: 18),
                            textStyle: const TextStyle(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          icon: Icon(
                            isLast
                                ? PhosphorIconsBold.check
                                : PhosphorIconsBold.arrowRight,
                            size: 15,
                          ),
                          label: Text(isLast ? 'Commencer' : 'Suivant'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingAmbientBackdrop extends StatelessWidget {
  const _OnboardingAmbientBackdrop({
    required this.slide,
    required this.animation,
  });

  final _Slide slide;
  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (_, __) {
        final progress = animation.value;
        final drift = (0.5 - progress) * 14;

        return Stack(
          children: <Widget>[
            Positioned(
              top: -110 + drift,
              right: -100 - drift,
              child: TfBlurredOrb(
                size: 240,
                color: slide.halo,
                blur: 82,
              ),
            ),
            Positioned(
              bottom: -90 - drift,
              left: -110 + drift,
              child: TfBlurredOrb(
                size: 220,
                color: slide.halo.withValues(alpha: 0.72),
                blur: 76,
              ),
            ),
            Positioned(
              top: 102,
              left: -14,
              child: Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: slide.accent.withValues(alpha: 0.1),
                ),
              ),
            ),
            Positioned(
              bottom: 150,
              right: -8,
              child: Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: slide.accent.withValues(alpha: 0.16),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _SlideIllustration extends StatelessWidget {
  const _SlideIllustration({
    required this.slide,
    required this.active,
  });

  final _Slide slide;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final iconColor = slide.ctaForeground == AppTheme.ink
        ? AppTheme.ink
        : Colors.white;

    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.88, end: active ? 1.0 : 0.96),
      duration: const Duration(milliseconds: 760),
      curve: Curves.elasticOut,
      builder: (context, scale, child) {
        return Transform.scale(
          scale: scale,
          child: child,
        );
      },
      child: SizedBox(
        width: 168,
        height: 168,
        child: Stack(
          alignment: Alignment.center,
          children: <Widget>[
            Positioned(
              top: 8,
              right: 24,
              child: _AccentSpark(color: slide.accent.withValues(alpha: 0.18)),
            ),
            Positioned(
              bottom: 18,
              left: 18,
              child: _AccentSpark(color: slide.accent.withValues(alpha: 0.14)),
            ),
            Positioned(
              bottom: 8,
              right: 36,
              child: _AccentSpark(color: slide.accent.withValues(alpha: 0.11)),
            ),
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: slide.heroGradient,
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: slide.accent.withValues(alpha: 0.24),
                    blurRadius: 32,
                    spreadRadius: 2,
                    offset: const Offset(0, 16),
                  ),
                ],
              ),
              child: Center(
                child: Icon(
                  slide.icon,
                  size: 56,
                  color: iconColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AccentSpark extends StatelessWidget {
  const _AccentSpark({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 18,
      height: 18,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
      ),
    );
  }
}

class _Slide {
  const _Slide({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.backgroundGradient,
    required this.accent,
    required this.heroGradient,
    required this.halo,
    required this.ctaForeground,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Gradient backgroundGradient;
  final Color accent;
  final Gradient heroGradient;
  final Color halo;
  final Color ctaForeground;
}

