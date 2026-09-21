import 'package:flutter/material.dart';

import 'cv_page_result_job_card.dart';

class CvResultJobsPanel extends StatelessWidget {
  const CvResultJobsPanel({
    super.key,
    required this.token,
    required this.jobs,
    required this.assistantStructured,
    required this.onOpenUrl,
  });

  final String token;
  final List<Map<String, dynamic>> jobs;
  final Map<String, dynamic>? assistantStructured;
  final Future<void> Function(String?) onOpenUrl;

  @override
  Widget build(BuildContext context) {
    if (jobs.isEmpty) return const SizedBox.shrink();

    final recommendedMeta =
        (assistantStructured?['recommendedJobs'] as List<dynamic>? ??
                const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final jobMetaById = <String, Map<String, dynamic>>{
      for (final Map<String, dynamic> item in recommendedMeta)
        (item['jobId'] ?? '').toString(): item,
    };
    final jobMetaByUrl = <String, Map<String, dynamic>>{
      for (final Map<String, dynamic> item in recommendedMeta)
        (item['url'] ?? '').toString(): item,
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const SizedBox(height: 14),
        ...jobs.asMap().entries.map((entry) {
          final index = entry.key;
          final job = entry.value;
          final id = (job['id'] ?? '').toString();
          final url = (job['sourceUrl'] ?? '').toString();
          final meta =
              jobMetaById[id] ?? jobMetaByUrl[url] ?? const <String, dynamic>{};
          return CvResultJobCard(
            index: index,
            token: token,
            job: job,
            why: (meta['why'] ?? '').toString(),
            cvImprovement: (meta['cvImprovement'] ?? '').toString(),
            onOpenUrl: onOpenUrl,
          );
        }),
      ],
    );
  }
}
