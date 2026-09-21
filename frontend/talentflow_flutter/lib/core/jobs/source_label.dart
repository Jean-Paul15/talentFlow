String sourceLabel(String? rawSource) {
  final source = (rawSource ?? '').trim().toLowerCase();
  if (source.isEmpty) return '';
  final normalized = source
      .replaceAll(' ', '_')
      .replaceAll('-', '_')
      .replaceAll('__', '_');

  const known = <String, String>{
    'anpe_togo': 'ANPE Togo',
    'emploi_tg': 'Emploi.tg',
    'emploitogo_com': 'EmploiTogo',
    'emploitogo_info': 'EmploiTogo Info',
    'arbeitnow_api': 'Arbeitnow',
    'jsearch_api': 'Partenaire international',
    'hackernews_api': 'Hacker News Jobs',
    'remotive_api': 'Remotive',
    'remoteok_api': 'RemoteOK',
    'adzuna': 'Adzuna',
    'adzuna_za': 'Adzuna',
    'wiijob': 'WiiJob',
    'miabejob': 'MiabeJob',
    'glassdoor': 'Glassdoor',
    'monster': 'Monster',
    'deep_crawler': 'Web sourcing',
  };

  final direct = known[normalized] ?? known[source];
  if (direct != null) return direct;

  if (normalized.contains('jsearch') ||
      normalized.contains('crawler') ||
      normalized.contains('scraper') ||
      normalized.contains('api_') ||
      normalized.endsWith('_api')) {
    return 'Partenaire emploi';
  }

  final cleaned = normalized
      .replaceAll('_api', '')
      .replaceAll('_', ' ')
      .replaceAll('-', ' ')
      .trim();
  if (cleaned.isEmpty) return '';
  return cleaned
      .split(' ')
      .where((token) => token.isNotEmpty)
      .map((token) => '${token[0].toUpperCase()}${token.substring(1)}')
      .join(' ');
}
