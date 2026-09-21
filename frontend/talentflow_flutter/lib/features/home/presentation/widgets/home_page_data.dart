List<String> preferredRolesOf(Map<String, dynamic> me) {
  return (me['preferredRoles'] as List<dynamic>? ?? const <dynamic>[])
      .map((dynamic value) => value.toString())
      .where((String value) => value.isNotEmpty)
      .toList();
}

int profileCompletenessOf(Map<String, dynamic> me) {
  final checks = <bool>[
    (me['name'] ?? '').toString().trim().isNotEmpty,
    (me['phone'] ?? '').toString().trim().isNotEmpty,
    (me['location'] ?? '').toString().trim().isNotEmpty,
    (me['headline'] ?? '').toString().trim().isNotEmpty,
    preferredRolesOf(me).isNotEmpty,
    (me['preferredCountry'] ?? '').toString().trim().isNotEmpty,
  ];
  final done = checks.where((bool value) => value).length;
  return ((done / checks.length) * 100).round();
}

List<String> watchlistQueriesOf(
  Map<String, dynamic> me,
  Map<String, dynamic>? latestReco,
) {
  final suggestions = <String>{};
  for (final role in preferredRolesOf(me).take(3)) {
    suggestions.add(role);
  }
  final query = (latestReco?['queryUsed'] ?? '').toString();
  if (query.isNotEmpty) {
    suggestions.add(query);
  }
  final location = (me['location'] ?? '').toString();
  if (location.isNotEmpty && suggestions.isNotEmpty) {
    suggestions.add('${suggestions.first} $location');
  }
  return suggestions
      .where((String value) => value.trim().isNotEmpty)
      .take(4)
      .toList();
}

List<String> actionPlanOf(
  Map<String, dynamic>? atsLite,
  Map<String, dynamic>? assistantStructured,
) {
  final actionPlan =
      (atsLite?['actionPlan'] as List<dynamic>? ?? const <dynamic>[])
          .map((dynamic value) => value.toString())
          .where((String value) => value.isNotEmpty)
          .toList();
  if (actionPlan.isNotEmpty) return actionPlan;
  return (assistantStructured?['actions'] as List<dynamic>? ??
          const <dynamic>[])
      .map((dynamic value) => value.toString())
      .where((String value) => value.isNotEmpty)
      .toList();
}

String recoDateLabelOf(Map<String, dynamic>? latestReco) {
  final recoCreatedAt = DateTime.tryParse(
    (latestReco?['createdAt'] ?? '').toString(),
  )?.toLocal();
  if (recoCreatedAt == null) return '';
  return '${recoCreatedAt.day}/${recoCreatedAt.month}/${recoCreatedAt.year}';
}
