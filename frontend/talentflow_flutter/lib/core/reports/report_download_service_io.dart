import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:open_filex/open_filex.dart';
import 'package:share_plus/share_plus.dart';

import '../app_config.dart';
import '../network/api_error.dart';

class ReportDownloadResult {
  const ReportDownloadResult({required this.fileName, required this.location});

  final String fileName;
  final String location;
}

class ReportDownloadService {
  Future<ReportDownloadResult> downloadHistoryPdf({
    required String token,
    required String historyId,
  }) async {
    final result = await _fetchAndStore(token: token, historyId: historyId);
    final openResult = await OpenFilex.open(
      result.location,
      type: 'application/pdf',
    );
    if (openResult.type != ResultType.done) {
      throw Exception(
        openResult.message.isEmpty
            ? 'Impossible d’ouvrir le PDF sur cet appareil.'
            : openResult.message,
      );
    }
    return result;
  }

  Future<ReportDownloadResult> shareHistoryPdf({
    required String token,
    required String historyId,
    String text = 'Mon rapport TalentFlow',
  }) async {
    final result = await _fetchAndStore(token: token, historyId: historyId);
    await SharePlus.instance.share(
      ShareParams(
        text: text,
        files: <XFile>[XFile(result.location, mimeType: 'application/pdf')],
      ),
    );
    return result;
  }

  Future<ReportDownloadResult> _fetchAndStore({
    required String token,
    required String historyId,
  }) async {
    final uri = Uri.parse(
      '${AppConfig.apiBaseUrl}/reports/history/${Uri.encodeComponent(historyId)}.pdf',
    );
    final response = await http
        .get(
          uri,
          headers: <String, String>{
            'Accept': 'application/pdf',
            'Authorization': 'Bearer $token',
          },
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final apiError = ApiErrorParser.fromHttp(
        response.statusCode,
        response.body,
        defaultMessage:
            'Le rapport PDF est indisponible pour le moment. Réessaie dans quelques instants.',
      );
      throw Exception(apiError.message);
    }

    final dir = await Directory.systemTemp.createTemp('talentflow_report_');
    final fileName = 'talentflow-report-$historyId.pdf';
    final file = File('${dir.path}${Platform.pathSeparator}$fileName');
    await file.writeAsBytes(response.bodyBytes, flush: true);
    return ReportDownloadResult(fileName: fileName, location: file.path);
  }
}
