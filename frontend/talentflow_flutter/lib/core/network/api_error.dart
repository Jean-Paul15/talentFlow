import 'dart:convert';

class ApiErrorResponse {
  const ApiErrorResponse({
    required this.statusCode,
    required this.message,
    this.code,
  });

  final int statusCode;
  final String message;
  final String? code;
}

class ApiErrorParser {
  static ApiErrorResponse fromHttp(
    int statusCode,
    String body, {
    required String defaultMessage,
  }) {
    final code = _extractCode(body);
    if (code == 'SERVICE_MAINTENANCE') {
      return ApiErrorResponse(
        statusCode: statusCode,
        message: 'Maintenance en cours. Réessaie dans quelques instants.',
        code: code,
      );
    }
    final message = _extractMessage(body);
    return ApiErrorResponse(
      statusCode: statusCode,
      message: message.isEmpty ? defaultMessage : message,
      code: code,
    );
  }

  static String extractMessage(String body) => _extractMessage(body);

  static String? extractCode(String body) => _extractCode(body);

  static String normalizeNetworkException(
    Object error, {
    required String timeoutMessage,
    required String offlineMessage,
    required String fallbackMessage,
  }) {
    final raw = error.toString().replaceFirst('Exception: ', '').trim();
    final lowered = raw.toLowerCase();
    if (lowered.contains('timeoutexception') || lowered.contains('timed out')) {
      return timeoutMessage;
    }
    if (lowered.contains('failed host lookup') ||
        lowered.contains('socketexception') ||
        lowered.contains('connection refused') ||
        lowered.contains('clientexception')) {
      return offlineMessage;
    }
    if (lowered.contains('formatexception')) {
      return fallbackMessage;
    }
    return sanitizeMessageForUi(raw, fallbackMessage: fallbackMessage);
  }

  static String sanitizeMessageForUi(
    String raw, {
    required String fallbackMessage,
  }) {
    final cleaned = raw
        .replaceAll(RegExp(r'\s+'), ' ')
        .replaceAll(RegExp(r'Exception:\s*', caseSensitive: false), '')
        .trim();
    if (cleaned.isEmpty) return fallbackMessage;

    final lowered = cleaned.toLowerCase();
    const technicalHints = <String>[
      'traceid',
      'stack',
      'stacktrace',
      'invalid prisma',
      'prisma.',
      'invocation',
      'platformexception',
      'timeoutexception',
      'socketexception',
      'clientexception',
      'graphql',
      'jsonrpc',
      'mcp-session-id',
      'http 500',
      'http 502',
      'http 503',
      'typeerror',
      'rangeerror',
      'null check operator used on a null value',
    ];
    if (technicalHints.any(lowered.contains)) {
      return fallbackMessage;
    }
    return cleaned;
  }

  static String _extractMessage(String raw) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        final code = decoded['code'];
        if (code is String && code.trim().toUpperCase() == 'SERVICE_MAINTENANCE') {
          return 'Maintenance en cours. Réessaie dans quelques instants.';
        }

        final message = decoded['message'] ?? decoded['error'];
        if (message is String && message.trim().isNotEmpty) {
          return sanitizeMessageForUi(
            message.trim(),
            fallbackMessage: 'Une erreur est survenue. Réessaie dans un instant.',
          );
        }
        if (message is List) {
          final joined = message
              .map((dynamic item) => '$item'.trim())
              .where((String item) => item.isNotEmpty)
              .join(', ');
          if (joined.isNotEmpty) {
            return sanitizeMessageForUi(
              joined,
              fallbackMessage: 'Une erreur est survenue. Réessaie dans un instant.',
            );
          }
        }
        final detail = decoded['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          return sanitizeMessageForUi(
            detail.trim(),
            fallbackMessage: 'Une erreur est survenue. Réessaie dans un instant.',
          );
        }
        if (detail is Map<String, dynamic>) {
          final nested = detail['message'];
          if (nested is String && nested.trim().isNotEmpty) {
            return sanitizeMessageForUi(
              nested.trim(),
              fallbackMessage: 'Une erreur est survenue. Réessaie dans un instant.',
            );
          }
        }
      }
    } catch (_) {
      // Ignore parsing issues and use the raw body.
    }
    return sanitizeMessageForUi(
      raw.trim(),
      fallbackMessage: 'Une erreur est survenue. Réessaie dans un instant.',
    );
  }

  static String? _extractCode(String raw) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        final code = decoded['code'];
        if (code is String && code.trim().isNotEmpty) {
          return code.trim().toUpperCase();
        }
        final detail = decoded['detail'];
        if (detail is Map<String, dynamic>) {
          final nested = detail['code'];
          if (nested is String && nested.trim().isNotEmpty) {
            return nested.trim().toUpperCase();
          }
        }
      }
    } catch (_) {
      // Ignore parsing issues and keep null.
    }
    return null;
  }
}
