import 'package:flutter/foundation.dart';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../app_config.dart';

class CacheVersionSnapshot {
  const CacheVersionSnapshot({
    required this.versions,
    required this.changedDomains,
    required this.syncedAt,
  });

  final Map<String, int> versions;
  final List<String> changedDomains;
  final DateTime syncedAt;

  bool get hasChanges => changedDomains.isNotEmpty;
}

class CacheRuntimeService {
  static const String _versionsKey = 'tf_cache_versions_v1';
  static const Duration _syncCooldown = Duration(seconds: 20);

  static DateTime? _lastSync;
  static Map<String, int> _current = <String, int>{
    'jobs': 0,
    'profile': 0,
    'recommendation': 0,
    'history': 0,
    'favorites': 0,
  };

  static final ValueNotifier<int> changeTick = ValueNotifier<int>(0);

  static Map<String, int> get versions => Map<String, int>.from(_current);

  static int versionFor(String domain) => _current[domain] ?? 0;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_versionsKey);
    if (raw == null || raw.trim().isEmpty) return;
    try {
      final parsed = jsonDecode(raw);
      if (parsed is Map<String, dynamic>) {
        _current = _mergeVersions(parsed);
      }
    } catch (_) {
      // Ignore corrupted cache metadata.
    }
  }

  static Future<CacheVersionSnapshot> syncWithBackend({
    bool force = false,
  }) async {
    final now = DateTime.now();
    if (!force && _lastSync != null && now.difference(_lastSync!) < _syncCooldown) {
      return CacheVersionSnapshot(
        versions: Map<String, int>.from(_current),
        changedDomains: const <String>[],
        syncedAt: now,
      );
    }

    final uri = Uri.parse('${AppConfig.apiBaseUrl}/runtime/cache-version');
    final response = await http
        .get(uri, headers: const <String, String>{'Accept': 'application/json'})
        .timeout(const Duration(seconds: 8));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'La synchronisation des données a échoué. Réessaie dans quelques instants.',
      );
    }

    final body = jsonDecode(response.body);
    if (body is! Map<String, dynamic>) {
      throw Exception(
        'La synchronisation des données est indisponible pour le moment.',
      );
    }

    final next = _mergeVersions((body['versions'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{});
    final changed = <String>[];
    for (final entry in next.entries) {
      if ((_current[entry.key] ?? 0) != entry.value) {
        changed.add(entry.key);
      }
    }

    _current = next;
    _lastSync = now;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_versionsKey, jsonEncode(_current));

    if (changed.isNotEmpty) {
      changeTick.value = changeTick.value + 1;
    }

    return CacheVersionSnapshot(
      versions: Map<String, int>.from(_current),
      changedDomains: changed,
      syncedAt: now,
    );
  }

  static Future<void> bumpLocal(String domain) async {
    final normalized = domain.trim().toLowerCase();
    if (normalized.isEmpty) return;
    _current[normalized] = DateTime.now().millisecondsSinceEpoch;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_versionsKey, jsonEncode(_current));
    changeTick.value = changeTick.value + 1;
  }

  static Map<String, int> _mergeVersions(Map<String, dynamic> source) {
    final merged = <String, int>{..._current};
    for (final domain in <String>[
      'jobs',
      'profile',
      'recommendation',
      'history',
      'favorites',
    ]) {
      final value = source[domain];
      final number = (value is num) ? value.toInt() : int.tryParse('$value');
      if (number != null && number > 0) {
        merged[domain] = number;
      }
    }
    return merged;
  }
}

