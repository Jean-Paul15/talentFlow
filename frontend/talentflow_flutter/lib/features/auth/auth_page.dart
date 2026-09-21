import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import 'package:talentflow_flutter/core/auth/auth_api.dart';
import 'package:talentflow_flutter/core/feedback/app_snack.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';
import 'package:talentflow_flutter/features/legal/legal_document_page.dart';
import 'package:talentflow_flutter/features/legal/legal_documents.dart';

class AuthPage extends StatefulWidget {
  const AuthPage({super.key, required this.onAuthenticated});

  final Future<void> Function({
    required String token,
    required String email,
    required String name,
    String? refreshToken,
  })
  onAuthenticated;

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> with TickerProviderStateMixin {
  late final TabController _tabs;
  final _loginEmail = TextEditingController();
  final _loginPassword = TextEditingController();
  final _signupName = TextEditingController();
  final _signupEmail = TextEditingController();
  final _signupPassword = TextEditingController();

  bool _busy = false;
  bool _showLoginPassword = false;
  bool _showSignupPassword = false;
  bool _acceptTermsSignup = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _tabs.addListener(_onTabChanged);
  }

  void _onTabChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _tabs.removeListener(_onTabChanged);
    _tabs.dispose();
    _loginEmail.dispose();
    _loginPassword.dispose();
    _signupName.dispose();
    _signupEmail.dispose();
    _signupPassword.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final email = _loginEmail.text.trim();
    final password = _loginPassword.text;
    if (email.isEmpty || password.isEmpty) {
      AppSnack.show(
        context,
        message: 'Renseigne ton email et ton mot de passe.',
        type: AppSnackType.warning,
      );
      return;
    }
    setState(() {
      _busy = true;
    });
    try {
      final payload = await AuthApi.login(email: email, password: password);
      await widget.onAuthenticated(
        token: payload.accessToken,
        email: payload.email,
        name: payload.name,
        refreshToken: payload.refreshToken.isEmpty
            ? null
            : payload.refreshToken,
      );
    } catch (e) {
      final message = e.toString().replaceFirst('Exception: ', '');
      if (mounted) {
        AppSnack.show(context, message: message, type: AppSnackType.error);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _register() async {
    final name = _signupName.text.trim();
    final email = _signupEmail.text.trim();
    final password = _signupPassword.text;
    if (name.isEmpty || email.isEmpty || password.length < 6) {
      AppSnack.show(
        context,
        message: 'Nom, email et mot de passe (6 caract\u00E8res min.) requis.',
        type: AppSnackType.warning,
      );
      return;
    }
    if (!_acceptTermsSignup) {
      AppSnack.show(
        context,
        message:
            'Accepte les conditions d\'utilisation pour finaliser ton inscription.',
        type: AppSnackType.warning,
      );
      return;
    }
    setState(() {
      _busy = true;
    });
    try {
      final payload = await AuthApi.register(
        name: name,
        email: email,
        password: password,
        acceptTerms: _acceptTermsSignup,
      );
      await widget.onAuthenticated(
        token: payload.accessToken,
        email: payload.email,
        name: payload.name,
        refreshToken: payload.refreshToken.isEmpty
            ? null
            : payload.refreshToken,
      );
    } catch (e) {
      final message = e.toString().replaceFirst('Exception: ', '');
      if (mounted) {
        AppSnack.show(context, message: message, type: AppSnackType.error);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openLegal(LegalDocumentType type) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => LegalDocumentPage(type: type)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final form = _AuthPanel(
      tabs: _tabs,
      loginEmail: _loginEmail,
      loginPassword: _loginPassword,
      signupName: _signupName,
      signupEmail: _signupEmail,
      signupPassword: _signupPassword,
      showLoginPassword: _showLoginPassword,
      showSignupPassword: _showSignupPassword,
      busy: _busy,
      onToggleLoginPassword: () {
        setState(() => _showLoginPassword = !_showLoginPassword);
      },
      onToggleSignupPassword: () {
        setState(() => _showSignupPassword = !_showSignupPassword);
      },
      onOpenTerms: () => _openLegal(LegalDocumentType.termsOfUse),
      onOpenPrivacy: () => _openLegal(LegalDocumentType.privacyPolicy),
      acceptTermsSignup: _acceptTermsSignup,
      onAcceptTermsChanged: (value) {
        setState(() => _acceptTermsSignup = value);
      },
      onLogin: _login,
      onSignup: _register,
    );

    return Scaffold(
      backgroundColor: AppTheme.mist,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= 980;
            if (wide) {
              return Row(
                children: <Widget>[
                  const Expanded(
                    child: TfReveal(
                      delay: Duration(milliseconds: 40),
                      child: _AuthHero(),
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 470),
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: TfReveal(
                            delay: const Duration(milliseconds: 110),
                            child: form,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
              children: <Widget>[
                const TfReveal(
                  delay: Duration(milliseconds: 40),
                  child: _AuthHero(compact: true),
                ),
                const SizedBox(height: 12),
                TfReveal(delay: const Duration(milliseconds: 110), child: form),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _AuthHero extends StatelessWidget {
  const _AuthHero({this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(compact ? 28 : 34);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        compact ? 0 : 30,
        compact ? 0 : 24,
        compact ? 0 : 16,
        compact ? 0 : 24,
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: radius,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[
              Color(0xFF2D2A26),
              Color(0xFF40352E),
              Color(0xFF241F1A),
            ],
          ),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.10),
              blurRadius: 32,
              offset: const Offset(0, 18),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: radius,
          child: Stack(
            children: <Widget>[
              Positioned(
                top: compact ? -48 : -72,
                right: compact ? -28 : -42,
                child: _HeroOrb(
                  size: compact ? 140 : 210,
                  color: AppTheme.coral.withValues(alpha: 0.18),
                ),
              ),
              Positioned(
                bottom: compact ? -54 : -82,
                left: compact ? -36 : -50,
                child: _HeroOrb(
                  size: compact ? 120 : 180,
                  color: const Color(0xFFF0D48A).withValues(alpha: 0.18),
                ),
              ),
              Padding(
                padding: EdgeInsets.fromLTRB(
                  compact ? 18 : 26,
                  compact ? 18 : 26,
                  compact ? 18 : 26,
                  compact ? 20 : 28,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Container(
                          width: compact ? 46 : 52,
                          height: compact ? 46 : 52,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.10),
                            ),
                          ),
                          alignment: Alignment.center,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.asset(
                              'assets/images/logo.png',
                              width: compact ? 30 : 34,
                              height: compact ? 30 : 34,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => SizedBox(
                                width: compact ? 30 : 34,
                                height: compact ? 30 : 34,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'TalentFlow',
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: Colors.white,
                                  ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Plateforme candidature',
                              style: Theme.of(context).textTheme.labelMedium
                                  ?.copyWith(
                                    color: Colors.white.withValues(alpha: 0.68),
                                  ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    SizedBox(height: compact ? 18 : 30),
                    Text(
                      'Ton espace candidature, enfin lisible.',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontSize: compact ? 30 : 40,
                        height: 1.02,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Importe ton CV, rep\u00E8re les bons postes et avance avec un plan concret, plus rapide \u00E0 comprendre sur mobile.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withValues(alpha: 0.78),
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        TfPill(
                          label: 'ATS-lisse',
                          color: Colors.white.withValues(alpha: 0.10),
                          foreground: Colors.white,
                          icon: PhosphorIconsRegular.chartDonut,
                        ),
                        TfPill(
                          label: 'Matching cr\u00E9dible',
                          color: Colors.white.withValues(alpha: 0.10),
                          foreground: Colors.white,
                          icon: PhosphorIconsRegular.target,
                        ),
                        TfPill(
                          label: 'Plan 7 jours',
                          color: Colors.white.withValues(alpha: 0.10),
                          foreground: Colors.white,
                          icon: PhosphorIconsRegular.calendarCheck,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuthPanel extends StatelessWidget {
  const _AuthPanel({
    required this.tabs,
    required this.loginEmail,
    required this.loginPassword,
    required this.signupName,
    required this.signupEmail,
    required this.signupPassword,
    required this.showLoginPassword,
    required this.showSignupPassword,
    required this.busy,
    required this.onToggleLoginPassword,
    required this.onToggleSignupPassword,
    required this.onOpenTerms,
    required this.onOpenPrivacy,
    required this.acceptTermsSignup,
    required this.onAcceptTermsChanged,
    required this.onLogin,
    required this.onSignup,
  });

  final TabController tabs;
  final TextEditingController loginEmail;
  final TextEditingController loginPassword;
  final TextEditingController signupName;
  final TextEditingController signupEmail;
  final TextEditingController signupPassword;
  final bool showLoginPassword;
  final bool showSignupPassword;
  final bool busy;
  final VoidCallback onToggleLoginPassword;
  final VoidCallback onToggleSignupPassword;
  final VoidCallback onOpenTerms;
  final VoidCallback onOpenPrivacy;
  final bool acceptTermsSignup;
  final ValueChanged<bool> onAcceptTermsChanged;
  final Future<void> Function() onLogin;
  final Future<void> Function() onSignup;

  @override
  Widget build(BuildContext context) {
    final isLogin = tabs.index == 0;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: const Color(0xFFE7DED4)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 34,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: const Color(0xFFF5EEE6),
              borderRadius: BorderRadius.circular(18),
            ),
            child: TabBar(
              controller: tabs,
              indicator: BoxDecoration(
                color: AppTheme.coral,
                borderRadius: BorderRadius.circular(14),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: AppTheme.coral.withValues(alpha: 0.24),
                    blurRadius: 18,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              indicatorSize: TabBarIndicatorSize.tab,
              dividerColor: Colors.transparent,
              labelColor: Colors.white,
              unselectedLabelColor: AppTheme.inkSoft,
              labelStyle: Theme.of(context).textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w800,
                fontSize: 13,
              ),
              unselectedLabelStyle: Theme.of(context).textTheme.labelMedium
                  ?.copyWith(fontWeight: FontWeight.w700, fontSize: 13),
              tabs: const <Widget>[
                Tab(text: 'Connexion'),
                Tab(text: 'Inscription'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AnimatedSize(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            alignment: Alignment.topCenter,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              transitionBuilder: (child, animation) {
                final slide = Tween<Offset>(
                  begin: const Offset(0.02, 0.02),
                  end: Offset.zero,
                ).animate(animation);
                return FadeTransition(
                  opacity: animation,
                  child: SlideTransition(position: slide, child: child),
                );
              },
              child: isLogin
                  ? _AuthForm(
                      key: const ValueKey('login'),
                      first: _Field(
                        controller: loginEmail,
                        label: 'Email',
                        hint: 'koffi@mail.com',
                        icon: PhosphorIconsRegular.envelope,
                      ),
                      second: _Field(
                        controller: loginPassword,
                        label: 'Mot de passe',
                        obscure: !showLoginPassword,
                        onToggle: onToggleLoginPassword,
                        icon: PhosphorIconsRegular.lock,
                      ),
                      busy: busy,
                      cta: 'Se connecter',
                      onSubmit: onLogin,
                    )
                  : _AuthForm(
                      key: const ValueKey('signup'),
                      first: _Field(
                        controller: signupName,
                        label: 'Nom complet',
                        hint: 'Koffi Agbesi',
                        icon: PhosphorIconsRegular.user,
                      ),
                      second: _Field(
                        controller: signupEmail,
                        label: 'Email',
                        hint: 'koffi@mail.com',
                        icon: PhosphorIconsRegular.envelope,
                      ),
                      third: _Field(
                        controller: signupPassword,
                        label: 'Mot de passe',
                        obscure: !showSignupPassword,
                        onToggle: onToggleSignupPassword,
                        icon: PhosphorIconsRegular.lock,
                      ),
                      extraBeforeSubmit: _SignupConsentAnimated(
                        value: acceptTermsSignup,
                        onChanged: onAcceptTermsChanged,
                        onOpenTerms: onOpenTerms,
                        onOpenPrivacy: onOpenPrivacy,
                      ),
                      busy: busy,
                      cta: 'Cr\u00E9er mon compte',
                      onSubmit: onSignup,
                    ),
            ),
          ),
          const SizedBox(height: 12),
          _LegalNotice(onOpenTerms: onOpenTerms, onOpenPrivacy: onOpenPrivacy),
        ],
      ),
    );
  }
}

class _LegalNotice extends StatelessWidget {
  const _LegalNotice({required this.onOpenTerms, required this.onOpenPrivacy});

  final VoidCallback onOpenTerms;
  final VoidCallback onOpenPrivacy;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Text(
          'En continuant, tu acceptes nos conditions d\'utilisation et notre politique de confidentialit\u00E9.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppTheme.inkSoft,
            height: 1.45,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 6,
          children: <Widget>[
            TextButton(
              onPressed: onOpenTerms,
              style: TextButton.styleFrom(
                foregroundColor: AppTheme.ink,
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                minimumSize: const Size(0, 32),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('Conditions d\'utilisation'),
            ),
            TextButton(
              onPressed: onOpenPrivacy,
              style: TextButton.styleFrom(
                foregroundColor: AppTheme.ink,
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                minimumSize: const Size(0, 32),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('Politique de confidentialit\u00E9'),
            ),
          ],
        ),
      ],
    );
  }
}

class _SignupConsentAnimated extends StatelessWidget {
  const _SignupConsentAnimated({
    required this.value,
    required this.onChanged,
    required this.onOpenTerms,
    required this.onOpenPrivacy,
  });

  final bool value;
  final ValueChanged<bool> onChanged;
  final VoidCallback onOpenTerms;
  final VoidCallback onOpenPrivacy;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: value ? const Color(0xFFFFF2E8) : const Color(0xFFF8F3ED),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: value
              ? AppTheme.coral.withValues(alpha: 0.66)
              : const Color(0xFFE7DED4),
        ),
        boxShadow: value
            ? <BoxShadow>[
                BoxShadow(
                  color: AppTheme.coral.withValues(alpha: 0.14),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ]
            : const <BoxShadow>[],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              splashColor: AppTheme.coral.withValues(alpha: 0.15),
              highlightColor: AppTheme.coral.withValues(alpha: 0.08),
              onTap: () => onChanged(!value),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: <Widget>[
                    _AnimatedConsentCheckbox(
                      value: value,
                      onTap: () => onChanged(!value),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'J\'accepte les conditions d\'utilisation.',
                        style: textTheme.bodySmall?.copyWith(
                          color: AppTheme.ink,
                          fontWeight: FontWeight.w700,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(left: 36),
            child: Wrap(
              spacing: 6,
              runSpacing: 4,
              children: <Widget>[
                TextButton(
                  onPressed: onOpenTerms,
                  style: TextButton.styleFrom(
                    foregroundColor: AppTheme.ink,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 6,
                    ),
                    minimumSize: const Size(0, 0),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Lire les conditions'),
                ),
                TextButton(
                  onPressed: onOpenPrivacy,
                  style: TextButton.styleFrom(
                    foregroundColor: AppTheme.ink,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 6,
                    ),
                    minimumSize: const Size(0, 0),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Politique de confidentialit\u00E9'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AnimatedConsentCheckbox extends StatelessWidget {
  const _AnimatedConsentCheckbox({required this.value, required this.onTap});

  final bool value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      checked: value,
      label: 'Acceptation des conditions',
      child: InkResponse(
        onTap: onTap,
        radius: 18,
        borderRadius: BorderRadius.circular(8),
        splashColor: AppTheme.coral.withValues(alpha: 0.18),
        child: AnimatedScale(
          scale: value ? 1.06 : 1,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutBack,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: value ? AppTheme.coral : Colors.white,
              borderRadius: BorderRadius.circular(7),
              border: Border.all(
                color: value ? AppTheme.coral : const Color(0xFFD8CCBF),
                width: 1.6,
              ),
              boxShadow: value
                  ? <BoxShadow>[
                      BoxShadow(
                        color: AppTheme.coral.withValues(alpha: 0.24),
                        blurRadius: 12,
                        offset: const Offset(0, 5),
                      ),
                    ]
                  : const <BoxShadow>[],
            ),
            child: Center(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 170),
                switchInCurve: Curves.easeOutBack,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  return FadeTransition(
                    opacity: animation,
                    child: ScaleTransition(scale: animation, child: child),
                  );
                },
                child: value
                    ? Icon(
                        PhosphorIconsBold.check,
                        key: const ValueKey<String>('checked'),
                        size: 14,
                        color: Colors.white,
                      )
                    : const SizedBox(
                        key: ValueKey<String>('unchecked'),
                        width: 14,
                        height: 14,
                      ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _AuthForm extends StatelessWidget {
  const _AuthForm({
    super.key,
    required this.first,
    required this.second,
    this.third,
    this.extraBeforeSubmit,
    required this.busy,
    required this.cta,
    required this.onSubmit,
  });

  final Widget first;
  final Widget second;
  final Widget? third;
  final Widget? extraBeforeSubmit;
  final bool busy;
  final String cta;
  final Future<void> Function() onSubmit;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        first,
        const SizedBox(height: 12),
        second,
        if (third != null) ...<Widget>[const SizedBox(height: 12), third!],
        if (extraBeforeSubmit != null) ...<Widget>[
          const SizedBox(height: 10),
          extraBeforeSubmit!,
        ],
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: FilledButton(
            onPressed: busy ? null : onSubmit,
            style: FilledButton.styleFrom(
              backgroundColor: AppTheme.coral,
              foregroundColor: Colors.white,
              disabledBackgroundColor: AppTheme.coral.withValues(alpha: 0.56),
              disabledForegroundColor: Colors.white.withValues(alpha: 0.72),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              textStyle: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            child: busy
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : Text(cta),
          ),
        ),
      ],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.label,
    this.hint,
    this.obscure = false,
    this.onToggle,
    this.icon,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final bool obscure;
  final VoidCallback? onToggle;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      cursorColor: AppTheme.coral,
      style: Theme.of(context).textTheme.bodyMedium,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        filled: true,
        fillColor: const Color(0xFFF8F3ED),
        prefixIcon: icon != null
            ? Padding(
                padding: const EdgeInsets.only(left: 14, right: 10),
                child: Icon(icon, size: 18, color: AppTheme.coral),
              )
            : null,
        prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
        suffixIcon: onToggle == null
            ? null
            : IconButton(
                onPressed: onToggle,
                icon: Icon(
                  obscure
                      ? PhosphorIconsRegular.eye
                      : PhosphorIconsRegular.eyeSlash,
                  size: 18,
                  color: AppTheme.inkMuted,
                ),
              ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFE7DED4)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFE7DED4)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppTheme.coral, width: 1.6),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppTheme.danger, width: 1.2),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppTheme.danger, width: 1.4),
        ),
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
          colors: <Color>[color, color.withValues(alpha: 0.02)],
        ),
      ),
    );
  }
}
