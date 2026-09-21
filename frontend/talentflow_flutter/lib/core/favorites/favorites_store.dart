import '../cache/cache_runtime_service.dart';
import '../cache/swr_cache_store.dart';
import '../network/graphql_api.dart';

class FavoriteEntry {
  FavoriteEntry({
    required this.id,
    required this.jobId,
    required this.title,
    required this.company,
    required this.description,
    required this.location,
    required this.contractType,
    required this.salary,
    required this.sourceName,
    required this.sourceUrl,
    required this.postedDate,
    required this.score,
    required this.createdAtIso,
  });

  final String id;
  final String jobId;
  final String title;
  final String company;
  final String description;
  final String location;
  final String contractType;
  final String salary;
  final String sourceName;
  final String sourceUrl;
  final String postedDate;
  final double? score;
  final String createdAtIso;

  factory FavoriteEntry.fromMap(Map<String, dynamic> raw) {
    return FavoriteEntry(
      id: (raw['id'] ?? '').toString(),
      jobId: (raw['jobId'] ?? '').toString(),
      title: (raw['title'] ?? '').toString(),
      company: (raw['company'] ?? '').toString(),
      description: (raw['description'] ?? '').toString(),
      location: (raw['location'] ?? '').toString(),
      contractType: (raw['contractType'] ?? '').toString(),
      salary: (raw['salary'] ?? '').toString(),
      sourceName: (raw['sourceName'] ?? '').toString(),
      sourceUrl: (raw['sourceUrl'] ?? '').toString(),
      postedDate: (raw['postedDate'] ?? '').toString(),
      score: raw['score'] is num ? (raw['score'] as num).toDouble() : null,
      createdAtIso: (raw['createdAt'] ?? '').toString(),
    );
  }

  Map<String, dynamic> toMap() {
    return <String, dynamic>{
      'id': id,
      'jobId': jobId,
      'title': title,
      'company': company,
      'description': description,
      'location': location,
      'contractType': contractType,
      'salary': salary,
      'sourceName': sourceName,
      'sourceUrl': sourceUrl,
      'postedDate': postedDate,
      'score': score,
      'createdAt': createdAtIso,
    };
  }

  Map<String, dynamic> toJobMap() {
    return <String, dynamic>{
      'id': jobId,
      'jobId': jobId,
      'title': title,
      'company': company,
      'description': description,
      'location': location,
      'contractType': contractType,
      'salary': salary,
      'sourceName': sourceName,
      'sourceUrl': sourceUrl,
      'postedDate': postedDate,
      'score': score,
    };
  }
}

class FavoritesStore {
  static String _listCacheKey(int limit, int offset) => 'list:$limit:$offset';

  Future<List<FavoriteEntry>> read({
    required String token,
    int limit = 50,
    int offset = 0,
  }) async {
    const doc = r'''
query MyFavorites($limit: Int, $offset: Int) {
  myFavorites(limit: $limit, offset: $offset) {
    id
    jobId
    title
    company
    description
    location
    contractType
    salary
    sourceName
    sourceUrl
    postedDate
    score
    createdAt
  }
}
''';

    final cached = await SwrCacheStore.readJson(
      domain: 'favorites',
      key: _listCacheKey(limit, offset),
    );
    if (cached != null) {
      final list = (cached['entries'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(FavoriteEntry.fromMap)
          .toList();
      if (list.isNotEmpty) {
        return list;
      }
    }

    final data = await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'limit': limit, 'offset': offset},
      token: token,
    );
    final raw = (data['myFavorites'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final entries = raw.map(FavoriteEntry.fromMap).toList();

    await SwrCacheStore.writeJson(
      domain: 'favorites',
      key: _listCacheKey(limit, offset),
      value: <String, dynamic>{
        'entries': entries.map((e) => e.toMap()).toList(),
        'savedAt': DateTime.now().toIso8601String(),
      },
    );

    return entries;
  }

  Future<bool> isFavorite({
    required String token,
    required String jobId,
  }) async {
    const doc = r'''
query IsFavorite($jobId: String!) {
  isFavorite(jobId: $jobId)
}
''';
    final data = await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'jobId': jobId},
      token: token,
    );
    return data['isFavorite'] == true;
  }

  Future<FavoriteEntry> save({
    required String token,
    required Map<String, dynamic> job,
  }) async {
    const doc = r'''
mutation SaveFavorite($input: SaveFavoriteInput!) {
  saveFavorite(input: $input) {
    id
    jobId
    title
    company
    description
    location
    contractType
    salary
    sourceName
    sourceUrl
    postedDate
    score
    createdAt
  }
}
''';
    final input = <String, dynamic>{
      'jobId': (job['jobId'] ?? job['id'] ?? '').toString().trim(),
      'title': (job['title'] ?? '').toString(),
      'company': (job['company'] ?? '').toString(),
      'description': (job['description'] ?? job['summary'] ?? '').toString(),
      'location': (job['location'] ?? '').toString(),
      'contractType': (job['contractType'] ?? job['contract_type'] ?? '')
          .toString(),
      'salary': (job['salary'] ?? '').toString(),
      'sourceName': (job['sourceName'] ?? job['source_name'] ?? '').toString(),
      'sourceUrl': (job['sourceUrl'] ?? job['source_url'] ?? '').toString(),
      'postedDate': (job['postedDate'] ?? job['posted_date'] ?? '').toString(),
      'score': job['score'],
    };
    final data = await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'input': input},
      token: token,
    );
    await CacheRuntimeService.bumpLocal('favorites');
    return FavoriteEntry.fromMap(data['saveFavorite'] as Map<String, dynamic>);
  }

  Future<void> remove({required String token, required String jobId}) async {
    const doc = r'''
mutation RemoveFavorite($jobId: String!) {
  removeFavorite(jobId: $jobId)
}
''';
    await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'jobId': jobId},
      token: token,
    );
    await CacheRuntimeService.bumpLocal('favorites');
  }
}
