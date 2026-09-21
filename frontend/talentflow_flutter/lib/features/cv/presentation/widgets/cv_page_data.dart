List<String> stringList(Map<String, dynamic>? source, String key) {
  return (source?[key] as List<dynamic>? ?? const <dynamic>[])
      .map((dynamic value) => value.toString())
      .where((String value) => value.isNotEmpty)
      .toList();
}

Map<String, dynamic>? assistantStructuredOf(Map<String, dynamic>? payload) {
  final value = payload?['assistantStructured'];
  return value is Map<String, dynamic> ? value : null;
}

Map<String, dynamic>? atsLiteOf(Map<String, dynamic>? payload) {
  final value = payload?['atsLite'];
  return value is Map<String, dynamic> ? value : null;
}

List<Map<String, dynamic>> cvJobsFromPayload(Map<String, dynamic>? payload) {
  return (payload?['jobs'] as List<dynamic>? ?? const <dynamic>[])
      .whereType<Map<String, dynamic>>()
      .toList();
}

String llmLabelForPayload(Map<String, dynamic>? payload) {
  if (payload == null) return 'Aucune synthèse';
  final status = (payload['llmStatus'] ?? '').toString();
  if (payload['llmUsed'] == true) {
    return status == 'used_cached'
        ? 'Assistant intelligent (cache)'
        : 'Assistant intelligent';
  }
  return status == 'provider_error'
      ? 'Diagnostic de secours'
      : 'Synthèse structurée';
}

List<Map<String, dynamic>> displayJobsForPayload(
  List<Map<String, dynamic>> jobs,
  Map<String, dynamic>? assistantStructured,
) {
  if (assistantStructured == null) return jobs;
  if ((assistantStructured['mode'] ?? '').toString() == 'no_match') {
    return const <Map<String, dynamic>>[];
  }
  final recommended =
      (assistantStructured['recommendedJobs'] as List<dynamic>? ??
              const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .toList();
  if (recommended.isEmpty) return jobs;

  final byId = <String, Map<String, dynamic>>{
    for (final Map<String, dynamic> job in jobs)
      (job['id'] ?? '').toString(): job,
  };
  final byUrl = <String, Map<String, dynamic>>{
    for (final Map<String, dynamic> job in jobs)
      (job['sourceUrl'] ?? '').toString(): job,
  };
  final out = <Map<String, dynamic>>[];
  for (final reco in recommended) {
    final matched =
        byId[(reco['jobId'] ?? '').toString()] ??
        byUrl[(reco['url'] ?? '').toString()];
    if (matched != null) out.add(matched);
  }
  return out.isNotEmpty ? out : jobs;
}
