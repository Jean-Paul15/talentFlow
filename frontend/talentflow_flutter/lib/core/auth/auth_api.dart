import 'dart:convert';

import 'package:http/http.dart' as http;

import '../app_config.dart';
import '../network/graphql_api.dart';

class AuthPayload {
  const AuthPayload({
    required this.accessToken,
    required this.refreshToken,
    required this.email,
    required this.name,
  });

  final String accessToken;
  final String refreshToken;
  final String email;
  final String name;
}

class AuthApi {
  static Future<AuthPayload> login({
    required String email,
    required String password,
  }) async {
    try {
      const doc = r'''
mutation Login($input: LoginInput!) {
  login(input: $input) { accessToken refreshToken user { id email name } }
}
''';
      final data = await GraphQlApi.request(
        document: doc,
        variables: <String, dynamic>{
          'input': <String, dynamic>{'email': email, 'password': password},
        },
        timeout: const Duration(seconds: 10),
      );
      final payload = data['login'] as Map<String, dynamic>;
      return _fromGraphQlPayload(
        payload,
        fallbackEmail: email,
        fallbackName: email.split('@').first,
      );
    } catch (error) {
      if (!_shouldFallbackToRest(error)) {
        throw Exception(_normalizeAuthMessage(error.toString()));
      }
      try {
        return _loginViaRest(email: email, password: password);
      } catch (restError) {
        throw Exception(_normalizeAuthMessage(restError.toString()));
      }
    }
  }

  static Future<AuthPayload> register({
    required String name,
    required String email,
    required String password,
    required bool acceptTerms,
  }) async {
    try {
      const doc = r'''
mutation Register($input: RegisterInput!) {
  register(input: $input) { accessToken refreshToken user { id email name } }
}
''';
      final data = await GraphQlApi.request(
        document: doc,
        variables: <String, dynamic>{
          'input': <String, dynamic>{
            'name': name,
            'email': email,
            'password': password,
            'acceptTerms': acceptTerms,
          },
        },
        timeout: const Duration(seconds: 10),
      );
      final payload = data['register'] as Map<String, dynamic>;
      return _fromGraphQlPayload(
        payload,
        fallbackEmail: email,
        fallbackName: name,
      );
    } catch (error) {
      if (!_shouldFallbackToRest(error)) {
        throw Exception(_normalizeAuthMessage(error.toString()));
      }
      try {
        return _registerViaRest(
          name: name,
          email: email,
          password: password,
          acceptTerms: acceptTerms,
        );
      } catch (restError) {
        throw Exception(_normalizeAuthMessage(restError.toString()));
      }
    }
  }

  static Future<AuthPayload> _loginViaRest({
    required String email,
    required String password,
  }) async {
    final response = await http
        .post(
          Uri.parse('${AppConfig.apiBaseUrl}/auth/login'),
          headers: const <String, String>{
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(<String, dynamic>{
            'email': email,
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return _fromRestResponse(
      response: response,
      fallbackEmail: email,
      fallbackName: email.split('@').first,
    );
  }

  static Future<AuthPayload> _registerViaRest({
    required String name,
    required String email,
    required String password,
    required bool acceptTerms,
  }) async {
    final response = await http
        .post(
          Uri.parse('${AppConfig.apiBaseUrl}/auth/register'),
          headers: const <String, String>{
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(<String, dynamic>{
            'name': name,
            'email': email,
            'password': password,
            'acceptTerms': acceptTerms,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return _fromRestResponse(
      response: response,
      fallbackEmail: email,
      fallbackName: name,
    );
  }

  static AuthPayload _fromGraphQlPayload(
    Map<String, dynamic> payload, {
    required String fallbackEmail,
    required String fallbackName,
  }) {
    final user =
        payload['user'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final accessToken = (payload['accessToken'] ?? '').toString().trim();
    final refreshToken = (payload['refreshToken'] ?? '').toString().trim();
    if (accessToken.isEmpty) {
      throw Exception('Connexion impossible pour le moment. Réessaie.');
    }
    return AuthPayload(
      accessToken: accessToken,
      refreshToken: refreshToken,
      email: (user['email'] ?? fallbackEmail).toString(),
      name: (user['name'] ?? fallbackName).toString(),
    );
  }

  static AuthPayload _fromRestResponse({
    required http.Response response,
    required String fallbackEmail,
    required String fallbackName,
  }) {
    final body = _decodeJsonBody(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = _extractErrorMessage(body);
      throw Exception(message);
    }
    final user = body['user'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final accessToken = (body['access_token'] ?? '').toString().trim();
    final refreshToken = (body['refresh_token'] ?? '').toString().trim();
    if (accessToken.isEmpty) {
      throw Exception('Connexion impossible pour le moment. Réessaie.');
    }
    return AuthPayload(
      accessToken: accessToken,
      refreshToken: refreshToken,
      email: (user['email'] ?? fallbackEmail).toString(),
      name: (user['name'] ?? fallbackName).toString(),
    );
  }

  static Map<String, dynamic> _decodeJsonBody(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {
      // Fall through to a generic shape.
    }
    return <String, dynamic>{'message': body};
  }

  static String _extractErrorMessage(Map<String, dynamic> body) {
    final raw =
        (body['message'] ??
                body['error'] ??
                'Connexion impossible pour le moment. Réessaie.')
            .toString()
            .trim();
    final normalized = raw.toLowerCase();
    if (normalized.contains('invalides')) {
      return 'Email ou mot de passe incorrect.';
    }
    if (normalized.contains('existe deja')) {
      return 'Un compte existe déjà avec cet email.';
    }
    if (normalized.contains('conditions') ||
        normalized.contains('accept') ||
        normalized.contains('terms')) {
      return 'Accepte les conditions d’utilisation pour créer ton compte.';
    }
    if (normalized.contains('timeout') ||
        normalized.contains('timed out') ||
        normalized.contains('socket') ||
        normalized.contains('network')) {
      return 'Connexion au serveur impossible pour le moment. Réessaie.';
    }
    return raw.isEmpty ? 'Connexion impossible pour le moment. Réessaie.' : raw;
  }

  static String _normalizeAuthMessage(String rawError) {
    final raw = rawError.replaceFirst('Exception: ', '').trim();
    final normalized = raw.toLowerCase();
    if (normalized.contains('invalides') ||
        normalized.contains('invalid credentials') ||
        normalized.contains('mot de passe incorrect') ||
        normalized.contains('email ou mot de passe')) {
      return 'Email ou mot de passe incorrect.';
    }
    if (normalized.contains('existe deja') ||
        normalized.contains('already exists') ||
        normalized.contains('already in use')) {
      return 'Un compte existe déjà avec cet email.';
    }
    if (normalized.contains('conditions') ||
        normalized.contains('accept') ||
        normalized.contains('terms')) {
      return 'Accepte les conditions d’utilisation pour créer ton compte.';
    }
    if (normalized.contains('traceid') ||
        normalized.contains('statuscode') ||
        normalized.contains('internal_error')) {
      return 'Connexion impossible pour le moment. Réessaie dans quelques instants.';
    }
    if (normalized.contains('timeout') ||
        normalized.contains('timed out') ||
        normalized.contains('socket') ||
        normalized.contains('network') ||
        normalized.contains('failed host lookup') ||
        normalized.contains('clientexception')) {
      return 'Connexion au serveur impossible pour le moment. Réessaie.';
    }
    return raw.isEmpty ? 'Connexion impossible pour le moment. Réessaie.' : raw;
  }

  static bool _shouldFallbackToRest(Object error) {
    final message = error.toString().toLowerCase();
    return message.contains('trop de temps') ||
        message.contains('timeout') ||
        message.contains('connexion api impossible') ||
        message.contains('failed host lookup') ||
        message.contains('socketexception') ||
        message.contains('clientexception') ||
        message.contains('configuration api invalide');
  }
}
