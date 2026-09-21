import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../app_config.dart';
import '../network/api_error.dart';
import '../session/auth_session_events.dart';
import 'cv_job_status.dart';

class CvJobsStore {
  static const _activeJobKey = 'tf_active_cv_job_id_v1';

  Future<CvJobStatus> createTextJob({
    required String token,
    required String cvText,
    String? fileName,
    String? location,
    String? contractType,
    int topK = 5,
  }) async {
    final payload = await _post('/cv-jobs/text', token, {
      'cvText': cvText,
      'fileName': fileName,
      'location': location,
      'contractType': contractType,
      'topK': topK,
    });
    final job = CvJobStatus.fromMap(payload);
    await saveActiveJobId(job.jobId);
    return job;
  }

  Future<CvJobStatus> createUploadJob({
    required String token,
    required String fileName,
    required Uint8List bytes,
    String? location,
    String? contractType,
    int topK = 5,
  }) async {
    try {
      final uri = Uri.parse('${AppConfig.apiBaseUrl}/cv-jobs/upload');
      final req = http.MultipartRequest('POST', uri)
        ..headers['Authorization'] = 'Bearer $token';
      req.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: fileName),
      );
      req.fields['topK'] = '$topK';
      if ((location ?? '').trim().isNotEmpty) {
        req.fields['location'] = location!.trim();
      }
      if ((contractType ?? '').trim().isNotEmpty) {
        req.fields['contractType'] = contractType!.trim();
      }
      final response = await req.send().timeout(const Duration(seconds: 45));
      final body = await response.stream.bytesToString();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception(_normalizeHttpError(response.statusCode, body));
      }
      final job = CvJobStatus.fromMap(jsonDecode(body) as Map<String, dynamic>);
      await saveActiveJobId(job.jobId);
      return job;
    } catch (error) {
      throw Exception(_normalizeException(error));
    }
  }

  Future<CvJobStatus> getJob({
    required String token,
    required String jobId,
  }) async {
    final payload = await _get('/cv-jobs/$jobId', token);
    return CvJobStatus.fromMap(payload);
  }

  Future<void> saveActiveJobId(String? jobId) async {
    final prefs = await SharedPreferences.getInstance();
    if (jobId == null || jobId.trim().isEmpty) {
      await prefs.remove(_activeJobKey);
      return;
    }
    await prefs.setString(_activeJobKey, jobId.trim());
  }

  Future<String?> loadActiveJobId() async {
    final prefs = await SharedPreferences.getInstance();
    final id = prefs.getString(_activeJobKey);
    return (id == null || id.trim().isEmpty) ? null : id.trim();
  }

  Future<Map<String, dynamic>> _get(String path, String token) async {
    try {
      final response = await http
          .get(
            Uri.parse('${AppConfig.apiBaseUrl}$path'),
            headers: <String, String>{
              'Authorization': 'Bearer $token',
              'Accept': 'application/json',
            },
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception(_normalizeHttpError(response.statusCode, response.body));
      }
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (error) {
      throw Exception(_normalizeException(error));
    }
  }

  Future<Map<String, dynamic>> _post(
    String path,
    String token,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse('${AppConfig.apiBaseUrl}$path'),
            headers: <String, String>{
              'Authorization': 'Bearer $token',
              'Content-Type': 'application/json',
            },
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception(_normalizeHttpError(response.statusCode, response.body));
      }
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (error) {
      throw Exception(_normalizeException(error));
    }
  }

  String _normalizeHttpError(int statusCode, String body) {
    if (statusCode == 401 || statusCode == 403) {
      AuthSessionEvents.notifyUnauthorized();
      return 'Session expirée. Reconnecte-toi pour continuer.';
    }

    final apiError = ApiErrorParser.fromHttp(
      statusCode,
      body,
      defaultMessage: 'La demande n’a pas abouti.',
    );
    if (statusCode == 422 && apiError.code == 'NOT_A_CV') {
      return apiError.message;
    }
    if (statusCode >= 500) {
      return 'Le serveur ne peut pas terminer cette analyse pour le moment. Réessaie dans quelques instants.';
    }
    return apiError.message;
  }

  String _normalizeException(Object error) {
    return ApiErrorParser.normalizeNetworkException(
      error,
      timeoutMessage:
          'Le serveur met trop de temps à répondre. Réessaie dans quelques instants.',
      offlineMessage:
          'Connexion au serveur impossible. Vérifie ta connexion puis réessaie.',
      fallbackMessage:
          'Une erreur technique empêche l’analyse pour le moment.',
    );
  }
}

