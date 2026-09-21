import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../app_config.dart';
import '../network/api_error.dart';

class CvUploadException implements Exception {
  const CvUploadException({
    required this.message,
    this.statusCode,
    this.code,
    this.canTryLocalFallback = false,
  });

  final String message;
  final int? statusCode;
  final String? code;
  final bool canTryLocalFallback;

  @override
  String toString() => message;
}

class CvUploadExtractionResult {
  const CvUploadExtractionResult({
    required this.fileName,
    required this.mimeType,
    required this.size,
    required this.strategy,
    required this.qualityScore,
    required this.pagesProcessed,
    required this.ocrUsed,
    required this.extractedChars,
    required this.text,
    required this.documentKind,
    required this.cvConfidence,
    required this.userMessage,
  });

  final String fileName;
  final String mimeType;
  final int size;
  final String strategy;
  final double qualityScore;
  final int pagesProcessed;
  final bool ocrUsed;
  final int extractedChars;
  final String text;
  final String documentKind;
  final double cvConfidence;
  final String userMessage;

  factory CvUploadExtractionResult.fromMap(Map<String, dynamic> json) {
    return CvUploadExtractionResult(
      fileName: (json['fileName'] ?? '').toString(),
      mimeType: (json['mimeType'] ?? '').toString(),
      size: _toInt(json['size']),
      strategy: (json['strategy'] ?? '').toString(),
      qualityScore: _toDouble(json['qualityScore']),
      pagesProcessed: _toInt(json['pagesProcessed']),
      ocrUsed: json['ocrUsed'] == true,
      extractedChars: _toInt(json['extractedChars']),
      text: (json['text'] ?? '').toString(),
      documentKind: (json['documentKind'] ?? 'cv').toString(),
      cvConfidence: _toDouble(json['cvConfidence']),
      userMessage: (json['userMessage'] ?? '').toString(),
    );
  }

  static int _toInt(dynamic value) => int.tryParse('${value ?? 0}') ?? 0;
  static double _toDouble(dynamic value) => double.tryParse('${value ?? 0}') ?? 0;
}

class CvUploadService {
  Future<CvUploadExtractionResult> extractText({
    required String token,
    required String fileName,
    required Uint8List bytes,
  }) async {
    try {
      final uri = Uri.parse('${AppConfig.apiBaseUrl}/search/extract-cv-text');
      final request = http.MultipartRequest('POST', uri)
        ..headers['Authorization'] = 'Bearer $token';
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: fileName,
        ),
      );

      final response = await request.send().timeout(const Duration(seconds: 45));
      final body = await response.stream.bytesToString();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw _buildUploadException(response.statusCode, body);
      }

      final payload = jsonDecode(body) as Map<String, dynamic>;
      return CvUploadExtractionResult.fromMap(payload);
    } on CvUploadException {
      rethrow;
    } catch (error) {
      throw CvUploadException(
        message: ApiErrorParser.normalizeNetworkException(
          error,
          timeoutMessage:
              'Le serveur met trop de temps \u00e0 lire ce fichier. R\u00e9essaie dans quelques instants.',
          offlineMessage:
              'Connexion au serveur impossible. R\u00e9essaie quand la connexion revient.',
          fallbackMessage:
              'Le document ne peut pas \u00eatre lu pour le moment. R\u00e9essaie avec un autre fichier.',
        ),
        canTryLocalFallback: true,
      );
    }
  }

  CvUploadException _buildUploadException(int statusCode, String body) {
    final apiError = ApiErrorParser.fromHttp(
      statusCode,
      body,
      defaultMessage: 'Le document ne peut pas \u00eatre lu pour le moment.',
    );

    if (statusCode == 413) {
      return const CvUploadException(
        message: 'Le fichier est trop volumineux. Limite: 5 Mo.',
        statusCode: 413,
      );
    }
    if (statusCode == 415) {
      return const CvUploadException(
        message: 'Format non support\u00e9. Utilise PDF, DOCX ou TXT.',
        statusCode: 415,
      );
    }
    if (statusCode == 422 && apiError.code == 'NOT_A_CV') {
      return CvUploadException(
        message: apiError.message,
        statusCode: statusCode,
        code: apiError.code,
        // Allow one local extraction pass to avoid false negatives on
        // server-side PDF parsing; if local classification is still non-CV,
        // UI remains blocked with a clear product message.
        canTryLocalFallback: true,
      );
    }
    if (statusCode >= 500) {
      return const CvUploadException(
        message:
            'Le serveur ne peut pas traiter ce CV pour le moment. R\u00e9essaie dans quelques instants.',
        statusCode: 500,
        canTryLocalFallback: true,
      );
    }
    return CvUploadException(
      message: apiError.message.isEmpty
          ? 'Le fichier semble invalide ou vide. Essaie un autre CV.'
          : apiError.message,
      statusCode: statusCode,
      code: apiError.code,
      canTryLocalFallback: statusCode == 400,
    );
  }
}
