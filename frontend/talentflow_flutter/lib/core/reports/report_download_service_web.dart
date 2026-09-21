// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:async';
import 'dart:html' as html;
import 'dart:typed_data';

import 'package:http/http.dart' as http;

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
    return _download(token: token, historyId: historyId);
  }

  Future<ReportDownloadResult> shareHistoryPdf({
    required String token,
    required String historyId,
    String text = 'Mon rapport TalentFlow',
  }) async {
    return _download(token: token, historyId: historyId);
  }

  Future<ReportDownloadResult> _download({
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

    final fileName = 'talentflow-report-$historyId.pdf';
    final bytes = Uint8List.fromList(response.bodyBytes);
    final blob = html.Blob(<Object>[bytes], 'application/pdf');
    final url = html.Url.createObjectUrlFromBlob(blob);
    final anchor = html.AnchorElement(href: url)
      ..download = fileName
      ..style.display = 'none';
    html.document.body?.append(anchor);
    anchor.click();
    anchor.remove();
    scheduleMicrotask(() => html.Url.revokeObjectUrl(url));
    return ReportDownloadResult(fileName: fileName, location: url);
  }
}
