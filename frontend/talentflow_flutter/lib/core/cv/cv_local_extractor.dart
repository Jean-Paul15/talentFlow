import 'dart:convert';
import 'dart:typed_data';

import 'package:syncfusion_flutter_pdf/pdf.dart';

import 'cv_document_classifier.dart';
import 'cv_upload_service.dart';

class CvLocalExtractor {
  CvLocalExtractor({CvDocumentClassifier? classifier})
      : _classifier = classifier ?? CvDocumentClassifier();

  final CvDocumentClassifier _classifier;

  Future<CvUploadExtractionResult?> tryExtract({
    required String fileName,
    required Uint8List bytes,
  }) async {
    final normalized = fileName.toLowerCase();

    if (_isPlainText(normalized)) {
      final text = utf8.decode(bytes, allowMalformed: true).trim();
      return _buildResult(
        fileName: fileName,
        mimeType: 'text/plain',
        bytes: bytes,
        strategy: 'device_text_extract',
        text: text,
      );
    }

    if (normalized.endsWith('.pdf')) {
      final document = PdfDocument(inputBytes: bytes);
      try {
        final text = PdfTextExtractor(document).extractText().trim();
        return _buildResult(
          fileName: fileName,
          mimeType: 'application/pdf',
          bytes: bytes,
          strategy: 'device_pdf_extract',
          text: text,
        );
      } finally {
        document.dispose();
      }
    }

    return null;
  }

  bool _isPlainText(String normalized) {
    return normalized.endsWith('.txt') ||
        normalized.endsWith('.md') ||
        normalized.endsWith('.json');
  }

  CvUploadExtractionResult _buildResult({
    required String fileName,
    required String mimeType,
    required Uint8List bytes,
    required String strategy,
    required String text,
  }) {
    final cleaned = text.trim();
    final assessment = _classifier.assess(cleaned);
    return CvUploadExtractionResult(
      fileName: fileName,
      mimeType: mimeType,
      size: bytes.length,
      strategy: strategy,
      qualityScore: _computeQualityScore(cleaned),
      pagesProcessed: mimeType == 'application/pdf' ? 1 : 0,
      ocrUsed: false,
      extractedChars: cleaned.length,
      text: cleaned,
      documentKind: assessment.documentKind,
      cvConfidence: assessment.cvConfidence,
      userMessage: assessment.userMessage,
    );
  }

  double _computeQualityScore(String text) {
    if (text.isEmpty) return 0;
    final words = text.split(RegExp(r'\s+')).where((String value) => value.isNotEmpty).length;
    final weird = RegExp(r'''[^\p{L}\p{N}\s\.,;:!?'"()%\-\/@+#]''', unicode: true)
        .allMatches(text)
        .length;
    final weirdRatio = weird / text.length;
    final lengthScore = (text.length / 1600).clamp(0, 1).toDouble();
    final wordsScore = (words / 280).clamp(0, 1).toDouble();
    final cleanScore = (1 - (weirdRatio * 10)).clamp(0, 1).toDouble();
    return double.parse(
      ((lengthScore * 0.45) + (wordsScore * 0.35) + (cleanScore * 0.2))
          .toStringAsFixed(3),
    );
  }
}
