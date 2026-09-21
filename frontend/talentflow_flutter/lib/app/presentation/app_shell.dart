import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:talentflow_flutter/core/cache/cache_runtime_service.dart';
import 'package:talentflow_flutter/core/feedback/app_snack.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:talentflow_flutter/core/app_config.dart';
import 'package:talentflow_flutter/core/network/graphql_api.dart';
import 'package:talentflow_flutter/core/session/auth_session_events.dart';
import 'package:talentflow_flutter/core/session/session_store.dart';
import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/features/auth/auth_page.dart';
import 'package:talentflow_flutter/features/onboarding/onboarding_page.dart';
import 'package:talentflow_flutter/features/splash/splash_page.dart';

import 'widgets/talentflow_app_shell.dart';

const String _kOnboardingLegacyKey = 'tf_onboarding_seen_v1';
const String _kOnboardingSeenMajorKey = 'tf_onboarding_seen_major_v1';
const int _kOnboardingLegacyBaselineVersion = 1;
const int _kOnboardingMajorVersion = 2;

Future<void> runTalentFlowApp() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.init();
  await CacheRuntimeService.init();
  runApp(const _Bootstrap());
}

enum _Phase { splash, onboarding, app }

class _Bootstrap extends StatefulWidget {
  const _Bootstrap();

  @override
  State<_Bootstrap> createState() => _BootstrapState();
}

class _BootstrapState extends State<_Bootstrap> with WidgetsBindingObserver {
  final SessionStore _store = SessionStore();

  _Phase _phase = _Phase.splash;
  SessionData? _session;
  Timer? _refreshTimer;
  bool _refreshInFlight = false;
  bool _splashAnimDone = false;
  bool _bootDone = false;
  int _onboardingSeenMajor = 0;

  @override
  void initState() {
    super.initState();
    AuthSessionEvents.unauthorizedTick.addListener(_onUnauthorizedSignal);
    WidgetsBinding.instance.addObserver(this);
    _doInit();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    AuthSessionEvents.unauthorizedTick.removeListener(_onUnauthorizedSignal);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_syncCacheVersions(showFeedback: true, force: true));
    }
  }

  Future<void> _syncCacheVersions({
    required bool showFeedback,
    bool force = false,
  }) async {
    try {
      final snapshot = await CacheRuntimeService.syncWithBackend(force: force);
      if (!mounted || !showFeedback || !snapshot.hasChanges) return;
      if (_phase != _Phase.app || !(_session?.isAuthenticated ?? false)) return;
      AppSnack.show(
        context,
        message: 'Données mises à jour.',
        type: AppSnackType.info,
        duration: const Duration(seconds: 2),
      );
    } catch (_) {
      // Silent in bootstrap/resume.
    }
  }

  Future<void> _doInit() async {
    final results = await Future.wait<dynamic>(<Future<dynamic>>[
      _store.read(),
      SharedPreferences.getInstance(),
    ]);

    final session = results[0] as SessionData;
    final prefs = results[1] as SharedPreferences;

    await _syncCacheVersions(showFeedback: false, force: true);
    _session = await _validatedSession(session);
    final legacySeen = prefs.getBool(_kOnboardingLegacyKey) ?? false;
    final storedMajor = prefs.getInt(_kOnboardingSeenMajorKey);
    _onboardingSeenMajor =
        storedMajor ?? (legacySeen ? _kOnboardingLegacyBaselineVersion : 0);
    _bootDone = true;
    _tryAdvance();
  }

  Future<SessionData> _validatedSession(SessionData session) async {
    if (!session.isAuthenticated) return session;
    try {
      await GraphQlApi.request(
        document: 'query ValidateSession { me { id } }',
        token: session.token,
      );
      _scheduleRefresh(session);
      return session;
    } on GraphQlAuthException {
      final refreshed = await _refreshSession(session);
      if (refreshed != null) {
        _scheduleRefresh(refreshed);
        return refreshed;
      }
      await _store.clear();
      return const SessionData(
        token: null,
        refreshToken: null,
        email: null,
        name: null,
      );
    } catch (_) {
      // Keep session for transient network issues; auto logout is handled on
      // definitive auth failures.
      _scheduleRefresh(session);
      return session;
    }
  }

  void _onSplashAnimDone() {
    _splashAnimDone = true;
    _tryAdvance();
  }

  void _tryAdvance() {
    if (!_splashAnimDone || !_bootDone || !mounted) return;
    setState(() {
      _phase = _onboardingSeenMajor >= _kOnboardingMajorVersion
          ? _Phase.app
          : _Phase.onboarding;
    });
  }

  Future<void> _completeOnboarding() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kOnboardingLegacyKey, true);
    await prefs.setInt(_kOnboardingSeenMajorKey, _kOnboardingMajorVersion);
    if (!mounted) return;
    setState(() {
      _onboardingSeenMajor = _kOnboardingMajorVersion;
      _phase = _Phase.app;
    });
  }

  void _reopenOnboarding() {
    if (!mounted) return;
    setState(() => _phase = _Phase.onboarding);
  }

  Future<void> _onAuth({
    required String token,
    required String email,
    required String name,
    String? refreshToken,
  }) async {
    await _store.save(
      token: token,
      refreshToken: refreshToken,
      email: email,
      name: name,
    );
    if (!mounted) return;
    setState(() {
      _session = SessionData(
        token: token,
        refreshToken: refreshToken,
        email: email,
        name: name,
      );
    });
    _scheduleRefresh(_session!);
    await _syncCacheVersions(showFeedback: false, force: true);
  }

  Future<void> _logout() async {
    _refreshTimer?.cancel();
    await _store.clear();
    if (!mounted) return;
    setState(() {
      _session = const SessionData(
        token: null,
        refreshToken: null,
        email: null,
        name: null,
      );
    });
  }

  void _onUnauthorizedSignal() {
    final session = _session;
    if (session == null || !session.isAuthenticated) return;
    _attemptRefreshOrLogout();
  }

  Future<void> _attemptRefreshOrLogout() async {
    final session = _session;
    if (session == null || !session.isAuthenticated) return;
    if (_refreshInFlight) return;
    final refreshed = await _refreshSession(session);
    if (refreshed != null) {
      if (!mounted) return;
      setState(() => _session = refreshed);
      _scheduleRefresh(refreshed);
      return;
    }
    await _logout();
  }

  Future<SessionData?> _refreshSession(SessionData current) async {
    final refreshToken = (current.refreshToken ?? '').trim();
    if (refreshToken.isEmpty) return null;
    _refreshInFlight = true;
    try {
      final res = await http
          .post(
            Uri.parse('${AppConfig.apiBaseUrl}/auth/refresh'),
            headers: const <String, String>{
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            },
            body: jsonEncode(<String, dynamic>{'refreshToken': refreshToken}),
          )
          .timeout(const Duration(seconds: 15));
      if (res.statusCode < 200 || res.statusCode >= 300) return null;
      final payload = jsonDecode(res.body) as Map<String, dynamic>;
      final accessToken = (payload['access_token'] ?? '').toString().trim();
      final nextRefresh = (payload['refresh_token'] ?? refreshToken)
          .toString()
          .trim();
      final user = (payload['user'] as Map<String, dynamic>? ?? const {});
      if (accessToken.isEmpty) return null;

      final refreshed = SessionData(
        token: accessToken,
        refreshToken: nextRefresh,
        email: (user['email'] ?? current.email ?? '').toString(),
        name: (user['name'] ?? current.name ?? '').toString(),
      );
      await _store.save(
        token: refreshed.token!,
        refreshToken: refreshed.refreshToken,
        email: refreshed.email,
        name: refreshed.name,
      );
      return refreshed;
    } catch (_) {
      return null;
    } finally {
      _refreshInFlight = false;
    }
  }

  void _scheduleRefresh(SessionData session) {
    _refreshTimer?.cancel();
    final token = session.token;
    if (token == null || token.isEmpty) return;
    final claims = _jwtClaims(token);
    if (claims == null) return;
    final leadSeconds = _computeRefreshLeadSeconds(claims);
    final refreshAt = DateTime.fromMillisecondsSinceEpoch(
      (claims.exp - leadSeconds) * 1000,
      isUtc: true,
    ).toLocal();
    final now = DateTime.now();
    final delay = refreshAt.difference(now);
    if (delay <= Duration.zero) {
      unawaited(_attemptRefreshOrLogout());
      return;
    }
    _refreshTimer = Timer(delay, () {
      unawaited(_attemptRefreshOrLogout());
    });
  }

  _JwtClaims? _jwtClaims(String token) {
    final parts = token.split('.');
    if (parts.length < 2) return null;
    try {
      final normalized = base64Url.normalize(parts[1]);
      final payload =
          jsonDecode(utf8.decode(base64Url.decode(normalized)))
              as Map<String, dynamic>;
      final exp = payload['exp'];
      final iat = payload['iat'];
      final expValue = (exp is int)
          ? exp
          : (exp is num)
          ? exp.toInt()
          : null;
      if (expValue == null) return null;
      final iatValue = (iat is int)
          ? iat
          : (iat is num)
          ? iat.toInt()
          : null;
      return _JwtClaims(exp: expValue, iat: iatValue);
    } catch (_) {
      return null;
    }
  }

  int _computeRefreshLeadSeconds(_JwtClaims claims) {
    final ttl = (claims.iat != null && claims.exp > claims.iat!)
        ? (claims.exp - claims.iat!)
        : 0;
    if (ttl <= 0) return 300;
    final dynamicLead = (ttl * 0.10).round();
    return dynamicLead.clamp(120, 600);
  }

  @override
  Widget build(BuildContext context) {
    final Widget home;
    switch (_phase) {
      case _Phase.splash:
        home = SplashPage(onDone: _onSplashAnimDone);
      case _Phase.onboarding:
        home = OnboardingPage(onDone: _completeOnboarding);
      case _Phase.app:
        final session =
            _session ??
            const SessionData(
              token: null,
              refreshToken: null,
              email: null,
              name: null,
            );
        home = session.isAuthenticated
            ? TalentFlowAppShell(
                token: session.token!,
                email: session.email ?? '',
                name: session.name ?? '',
                onLogout: _logout,
                onOpenOnboarding: _reopenOnboarding,
              )
            : AuthPage(onAuthenticated: _onAuth);
    }

    return MaterialApp(
      title: 'TalentFlow',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      builder: (BuildContext context, Widget? child) {
        final mq = MediaQuery.of(context);
        final clamped = mq.textScaler.scale(1.0).clamp(0.85, 1.15);
        return MediaQuery(
          data: mq.copyWith(textScaler: TextScaler.linear(clamped)),
          child: child!,
        );
      },
      home: home,
    );
  }
}

class _JwtClaims {
  const _JwtClaims({required this.exp, required this.iat});

  final int exp;
  final int? iat;
}
