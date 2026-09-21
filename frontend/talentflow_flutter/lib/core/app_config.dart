import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ServerConfig {
  const ServerConfig({
    required this.apiBaseUrl,
    required this.graphqlPath,
    required this.hasRuntimeOverride,
  });

  final String apiBaseUrl;
  final String graphqlPath;
  final bool hasRuntimeOverride;

  String get graphqlUrl => '$apiBaseUrl$graphqlPath';
  String get healthUrl => '$apiBaseUrl/health';
}

class ApiConnectionProbe {
  const ApiConnectionProbe({
    required this.ok,
    required this.message,
    required this.healthUrl,
    this.statusCode,
  });

  final bool ok;
  final String message;
  final String healthUrl;
  final int? statusCode;
}

class AppConfig {
  static const bool allowRuntimeApiOverride = !kReleaseMode;

  static const String defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.example.com',
  );

  static const String defaultGraphqlPath = String.fromEnvironment(
    'GRAPHQL_PATH',
    defaultValue: '/graphql',
  );

  static const String _apiBaseUrlOverrideKey = 'tf_api_base_url_override_v1';
  static final ValueNotifier<ServerConfig> _config = ValueNotifier<ServerConfig>(
    ServerConfig(
      apiBaseUrl: _normalizeBaseUrl(defaultApiBaseUrl),
      graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
      hasRuntimeOverride: false,
    ),
  );

  static ValueListenable<ServerConfig> get listenable => _config;

  static ServerConfig get current => _config.value;
  static String get apiBaseUrl => current.apiBaseUrl;
  static String get graphqlPath => current.graphqlPath;
  static String get graphqlUrl => current.graphqlUrl;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    if (!allowRuntimeApiOverride) {
      await prefs.remove(_apiBaseUrlOverrideKey);
      _config.value = ServerConfig(
        apiBaseUrl: _normalizeBaseUrl(defaultApiBaseUrl),
        graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
        hasRuntimeOverride: false,
      );
      return;
    }
    final override = prefs.getString(_apiBaseUrlOverrideKey);
    final safeOverride = _sanitizeOverride(override);
    if (override != null && safeOverride == null) {
      await prefs.remove(_apiBaseUrlOverrideKey);
    }
    _config.value = ServerConfig(
      apiBaseUrl: _normalizeBaseUrl(
        safeOverride == null || safeOverride.trim().isEmpty
            ? defaultApiBaseUrl
            : safeOverride,
      ),
      graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
      hasRuntimeOverride: safeOverride != null && safeOverride.trim().isNotEmpty,
    );
  }

  static Future<void> setApiBaseUrlOverride(String? value) async {
    final prefs = await SharedPreferences.getInstance();
    if (!allowRuntimeApiOverride) {
      await prefs.remove(_apiBaseUrlOverrideKey);
      _config.value = ServerConfig(
        apiBaseUrl: _normalizeBaseUrl(defaultApiBaseUrl),
        graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
        hasRuntimeOverride: false,
      );
      return;
    }
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      await prefs.remove(_apiBaseUrlOverrideKey);
      _config.value = ServerConfig(
        apiBaseUrl: _normalizeBaseUrl(defaultApiBaseUrl),
        graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
        hasRuntimeOverride: false,
      );
      return;
    }

    final normalized = _normalizeBaseUrl(trimmed);
    await prefs.setString(_apiBaseUrlOverrideKey, normalized);
    _config.value = ServerConfig(
      apiBaseUrl: normalized,
      graphqlPath: _normalizeGraphqlPath(defaultGraphqlPath),
      hasRuntimeOverride: true,
    );
  }

  static Future<ApiConnectionProbe> probeConnection() async {
    final uri = Uri.parse(current.healthUrl);
    try {
      final response = await http
          .get(uri, headers: const <String, String>{'Accept': 'application/json'})
          .timeout(const Duration(seconds: 8));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return ApiConnectionProbe(
          ok: true,
          message: 'Connexion OK vers ${current.apiBaseUrl}',
          healthUrl: current.healthUrl,
          statusCode: response.statusCode,
        );
      }
      return ApiConnectionProbe(
        ok: false,
        message:
            'Le service est temporairement indisponible. Réessaie dans quelques instants.',
        healthUrl: current.healthUrl,
        statusCode: response.statusCode,
      );
    } on TimeoutException {
      return ApiConnectionProbe(
        ok: false,
        message: 'Délai dépassé pendant le test de connexion.',
        healthUrl: current.healthUrl,
      );
    } catch (e) {
      return ApiConnectionProbe(
        ok: false,
        message:
            'Connexion au serveur impossible. Vérifie ta connexion puis réessaie.',
        healthUrl: current.healthUrl,
      );
    }
  }

  static String _normalizeBaseUrl(String raw) {
    var value = raw.trim();
    value = value.replaceAll(RegExp(r'\\s+'), '');
    if (value.isEmpty) {
      value = defaultApiBaseUrl;
    }
    if (!value.startsWith('http://') && !value.startsWith('https://')) {
      value = 'http://$value';
    }

    final graphPath = _normalizeGraphqlPath(defaultGraphqlPath);
    if (value.endsWith(graphPath)) {
      value = value.substring(0, value.length - graphPath.length);
    }

    while (value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    return value;
  }

  static String? _sanitizeOverride(String? raw) {
    if (!allowRuntimeApiOverride) {
      return null;
    }
    final trimmed = raw?.trim();
    if (trimmed == null || trimmed.isEmpty) {
      return null;
    }

    final normalized = _normalizeBaseUrl(trimmed);
    final uri = Uri.tryParse(normalized);
    final host = (uri?.host ?? '').toLowerCase();
    const localHosts = <String>{
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      '10.0.2.2',
    };
    if (localHosts.contains(host)) {
      return null;
    }
    return normalized;
  }

  static String _normalizeGraphqlPath(String raw) {
    var value = raw.trim();
    value = value.replaceAll(RegExp(r'\\s+'), '');
    if (value.isEmpty) {
      value = '/graphql';
    }
    if (!value.startsWith('/')) {
      value = '/$value';
    }
    while (value.length > 1 && value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    return value;
  }
}

