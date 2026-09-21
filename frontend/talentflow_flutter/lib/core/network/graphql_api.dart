import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../app_config.dart';
import '../session/auth_session_events.dart';
import 'api_error.dart';

class GraphQlAuthException implements Exception {
  const GraphQlAuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

class GraphQlApi {
  static Future<Map<String, dynamic>> request({
    required String document,
    Map<String, dynamic>? variables,
    String? token,
    Duration timeout = const Duration(seconds: 25),
  }) async {
    try {
      final uri = Uri.parse(AppConfig.graphqlUrl.trim());
      final headers = <String, String>{
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (token != null && token.trim().isNotEmpty)
          'Authorization': 'Bearer ${token.trim()}',
      };
      final payload = <String, dynamic>{
        'query': document,
        'variables': variables ?? <String, dynamic>{},
      };

      final response = await http
          .post(uri, headers: headers, body: jsonEncode(payload))
          .timeout(timeout);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        if (response.statusCode == 401 || response.statusCode == 403) {
          AuthSessionEvents.notifyUnauthorized();
          throw const GraphQlAuthException(
            'Session expirée. Reconnecte-toi pour continuer.',
          );
        }
        final apiError = ApiErrorParser.fromHttp(
          response.statusCode,
          response.body,
          defaultMessage: response.statusCode >= 500
              ? 'Le service est temporairement indisponible. Réessaie dans quelques instants.'
              : 'La requête n\'a pas abouti. Réessaie.',
        );
        throw Exception(apiError.message);
      }

      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw Exception('Réponse GraphQL invalide.');
      }

      final errors = decoded['errors'];
      if (errors is List && errors.isNotEmpty) {
        final first = errors.first;
        final rawMessage = first is Map<String, dynamic>
            ? (first['message'] ?? 'Erreur GraphQL').toString()
            : 'Erreur GraphQL';
        final lowered = rawMessage.toLowerCase();
        if (lowered.contains('unauthorized') ||
            lowered.contains('forbidden') ||
            lowered.contains('jwt') ||
            lowered.contains('token') ||
            lowered.contains('non autoris')) {
          AuthSessionEvents.notifyUnauthorized();
          throw const GraphQlAuthException(
            'Session expirée. Reconnecte-toi pour continuer.',
          );
        }
        throw Exception(
          ApiErrorParser.sanitizeMessageForUi(
            rawMessage,
            fallbackMessage:
                'Une erreur empêche le chargement pour le moment. Réessaie.',
          ),
        );
      }

      final data = decoded['data'];
      if (data is! Map<String, dynamic>) {
        throw Exception('Réponse GraphQL invalide.');
      }
      return data;
    } on TimeoutException {
      throw Exception(
        'Le serveur met trop de temps à répondre. Réessaie dans quelques instants.',
      );
    } on GraphQlAuthException {
      rethrow;
    } catch (error) {
      final message = ApiErrorParser.normalizeNetworkException(
        error,
        timeoutMessage:
            'Le serveur met trop de temps à répondre. Réessaie dans quelques instants.',
        offlineMessage:
            'Connexion au serveur impossible. Vérifie ta connexion puis réessaie.',
        fallbackMessage:
            'Une erreur technique empêche l\'analyse pour le moment.',
      );
      throw Exception(message);
    }
  }
}
