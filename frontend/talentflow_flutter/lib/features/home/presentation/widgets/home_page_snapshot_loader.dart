import 'package:talentflow_flutter/core/cache/swr_cache_store.dart';
import 'package:talentflow_flutter/core/network/graphql_api.dart';

class HomePageSnapshot {
  const HomePageSnapshot({
    required this.me,
    required this.latestReco,
    required this.favoriteCount,
  });

  final Map<String, dynamic>? me;
  final Map<String, dynamic>? latestReco;
  final int favoriteCount;
}

const String _homeSnapshotQuery = r'''
query HomeSnapshot($historyLimit: Int!, $favoriteLimit: Int!) {
  me {
    id
    email
    name
    phone
    location
    headline
    preferredRoles
    preferredCountry
  }
  myRecommendationHistory(limit: $historyLimit, offset: 0) {
    id
    queryUsed
    totalResults
    createdAt
    llmStatus
    assistantStructured {
      mode
      profileSummary
      strengths
      gaps
      scoreExplanation
      offerPlaybooks {
        jobId
        title
        url
        whyFit
        cvDelta
        rewrite {
          targetTitle
          targetSummary
          experienceBullets
        }
        evidence
      }
      actions
      reasonIfNoMatch
      recommendedJobs {
        jobId
        title
        why
        url
        cvImprovement
      }
    }
    atsLite {
      overallScore
      structureScore
      alignmentScore
      evidenceScore
      readinessLabel
      summary
      matchedKeywords
      missingKeywords
      suggestions
      actionPlan
    }
  }
  myFavorites(limit: $favoriteLimit, offset: 0) {
    id
  }
}
''';

List<Map<String, dynamic>> _mapListOf(dynamic value) {
  return (value as List<dynamic>? ?? const <dynamic>[])
      .whereType<Map<String, dynamic>>()
      .toList();
}

Future<HomePageSnapshot?> loadHomePageSnapshotCached() async {
  final cached = await SwrCacheStore.readJson(domain: 'recommendation', key: 'home_snapshot');
  if (cached == null) return null;

  final me = cached['me'] as Map<String, dynamic>?;
  final latestReco = cached['latestReco'] as Map<String, dynamic>?;
  final favoriteCount = (cached['favoriteCount'] as num?)?.toInt() ?? 0;

  return HomePageSnapshot(
    me: me,
    latestReco: latestReco,
    favoriteCount: favoriteCount,
  );
}

Future<HomePageSnapshot> loadHomePageSnapshot({
  required String token,
}) async {
  final data = await GraphQlApi.request(
    document: _homeSnapshotQuery,
    variables: const <String, dynamic>{
      'historyLimit': 1,
      'favoriteLimit': 100,
    },
    token: token,
  );
  final history = _mapListOf(data['myRecommendationHistory']);
  final favorites = _mapListOf(data['myFavorites']);

  final snapshot = HomePageSnapshot(
    me: data['me'] as Map<String, dynamic>?,
    latestReco: history.isEmpty ? null : history.first,
    favoriteCount: favorites.length,
  );

  await SwrCacheStore.writeJson(
    domain: 'recommendation',
    key: 'home_snapshot',
    value: <String, dynamic>{
      'me': snapshot.me,
      'latestReco': snapshot.latestReco,
      'favoriteCount': snapshot.favoriteCount,
      'savedAt': DateTime.now().toIso8601String(),
    },
  );

  return snapshot;
}
