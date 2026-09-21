import '../cache/cache_runtime_service.dart';
import '../cache/swr_cache_store.dart';
import '../network/graphql_api.dart';

class RecommendationHistoryEntry {
  const RecommendationHistoryEntry({
    required this.id,
    required this.createdAtIso,
    required this.cvPreview,
    required this.queryUsed,
    required this.location,
    required this.contractType,
    required this.assistantMessage,
    required this.totalResults,
    required this.llmUsed,
    required this.llmProvider,
    required this.llmModel,
    required this.llmError,
    required this.llmStatus,
    required this.assistantStructured,
    required this.atsLite,
    required this.skills,
    required this.experienceYears,
    required this.educationLevel,
    required this.jobs,
  });

  final String id;
  final String createdAtIso;
  final String cvPreview;
  final String queryUsed;
  final String location;
  final String contractType;
  final String assistantMessage;
  final int totalResults;
  final bool llmUsed;
  final String llmProvider;
  final String llmModel;
  final String llmError;
  final String llmStatus;
  final Map<String, dynamic>? assistantStructured;
  final Map<String, dynamic>? atsLite;
  final List<String> skills;
  final int? experienceYears;
  final String educationLevel;
  final List<Map<String, dynamic>> jobs;

  factory RecommendationHistoryEntry.fromGraphql(Map<String, dynamic> json) {
    final analysis =
        (json['cvAnalysis'] as Map<String, dynamic>? ?? <String, dynamic>{});
    return RecommendationHistoryEntry(
      id: (json['id'] ?? '').toString(),
      createdAtIso: (json['createdAt'] ?? '').toString(),
      cvPreview: (json['cvTextPreview'] ?? '').toString(),
      queryUsed: (json['queryUsed'] ?? '').toString(),
      location: (json['locationFilter'] ?? '').toString(),
      contractType: (json['contractTypeFilter'] ?? '').toString(),
      assistantMessage: (json['assistantMessage'] ?? '').toString(),
      totalResults: (json['totalResults'] ?? 0) as int,
      llmUsed: json['llmUsed'] == true,
      llmProvider: (json['llmProvider'] ?? '').toString(),
      llmModel: (json['llmModel'] ?? '').toString(),
      llmError: (json['llmError'] ?? '').toString(),
      llmStatus: (json['llmStatus'] ?? '').toString(),
      assistantStructured: json['assistantStructured'] as Map<String, dynamic>?,
      atsLite: json['atsLite'] as Map<String, dynamic>?,
      skills: (analysis['skills'] as List<dynamic>? ?? const <dynamic>[])
          .map((dynamic e) => e.toString())
          .where((String e) => e.isNotEmpty)
          .toList(),
      experienceYears: analysis['experienceYears'] as int?,
      educationLevel: (analysis['educationLevel'] ?? '').toString(),
      jobs: (json['jobs'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .toList(),
    );
  }
}

class RecommendationHistoryStore {
  Future<List<RecommendationHistoryEntry>> read({
    required String token,
    int limit = 25,
  }) async {
    const doc = r'''
query MyRecommendationHistory($limit: Int, $offset: Int) {
  myRecommendationHistory(limit: $limit, offset: $offset) {
    id
    cvTextPreview
    queryUsed
    locationFilter
    contractTypeFilter
    assistantMessage
    totalResults
    llmUsed
    llmProvider
    llmModel
    llmError
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
    createdAt
    cvAnalysis {
      skills
      experienceYears
      educationLevel
      rawTextPreview
    }
    jobs {
      id
      title
      company
      location
      contractType
      sourceName
      sourceUrl
      postedDate
      score
      summary
    }
  }
}
''';

    final cacheKey = 'list:$limit:0';
    final cached = await SwrCacheStore.readJson(domain: 'history', key: cacheKey);
    if (cached != null) {
      final cachedItems = (cached['entries'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(RecommendationHistoryEntry.fromGraphql)
          .toList();
      if (cachedItems.isNotEmpty) {
        return cachedItems;
      }
    }

    final data = await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'limit': limit, 'offset': 0},
      token: token,
    );

    final rawItems =
        (data['myRecommendationHistory'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    final entries = rawItems.map(RecommendationHistoryEntry.fromGraphql).toList();

    await SwrCacheStore.writeJson(
      domain: 'history',
      key: cacheKey,
      value: <String, dynamic>{
        'entries': rawItems,
        'savedAt': DateTime.now().toIso8601String(),
      },
    );

    return entries;
  }

  Future<RecommendationHistoryEntry> add({
    required String token,
    required String cvText,
    String? fileName,
    required String location,
    String? contractType,
    required Map<String, dynamic> payload,
  }) async {
    const doc = r'''
mutation SaveRecommendationHistory($input: SaveRecommendationHistoryInput!) {
  saveRecommendationHistory(input: $input) {
    id
    cvTextPreview
    queryUsed
    locationFilter
    contractTypeFilter
    assistantMessage
    totalResults
    llmUsed
    llmProvider
    llmModel
    llmError
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
    createdAt
    cvAnalysis {
      skills
      experienceYears
      educationLevel
      rawTextPreview
    }
    jobs {
      id
      title
      company
      location
      contractType
      sourceName
      sourceUrl
      postedDate
      score
      summary
    }
  }
}
''';

    final input = <String, dynamic>{
      'cvTextPreview': cvText.length > 280 ? '${cvText.substring(0, 280)}...' : cvText,
      'fileName': fileName,
      'queryUsed': (payload['queryUsed'] ?? '').toString(),
      'locationFilter': location.isEmpty ? null : location,
      'contractTypeFilter': contractType,
      'assistantMessage': (payload['assistantMessage'] ?? '').toString(),
      'llmUsed': payload['llmUsed'] == true,
      'llmProvider': (payload['llmProvider'] ?? '').toString(),
      'llmModel': (payload['llmModel'] ?? '').toString(),
      'llmError': (payload['llmError'] ?? '').toString(),
      'llmStatus': (payload['llmStatus'] ?? '').toString(),
      'totalResults': (payload['totalResults'] ?? 0) as int,
      'assistantStructured': payload['assistantStructured'],
      'atsLite': payload['atsLite'],
      'cvAnalysis': payload['cvAnalysis'],
      'jobs': (payload['jobs'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .take(10)
          .toList(),
    };

    final data = await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'input': input},
      token: token,
    );

    final entry = RecommendationHistoryEntry.fromGraphql(
      data['saveRecommendationHistory'] as Map<String, dynamic>,
    );
    await CacheRuntimeService.bumpLocal('history');
    await CacheRuntimeService.bumpLocal('recommendation');
    return entry;
  }

  Future<void> delete({required String token, required String id}) async {
    const doc = r'''
mutation DeleteRecommendationHistory($id: String!) {
  deleteRecommendationHistory(id: $id)
}
''';
    await GraphQlApi.request(
      document: doc,
      variables: <String, dynamic>{'id': id},
      token: token,
    );
    await CacheRuntimeService.bumpLocal('history');
    await CacheRuntimeService.bumpLocal('recommendation');
  }
}
