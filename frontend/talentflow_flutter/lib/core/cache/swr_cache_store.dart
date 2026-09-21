import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'cache_runtime_service.dart';

class SwrCacheStore {
  static Future<Map<String, dynamic>?> readJson({
    required String domain,
    required String key,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final cacheKey = _cacheKey(domain, key);
    final raw = prefs.getString(cacheKey);
    if (raw == null || raw.trim().isEmpty) return null;
    try {
      final parsed = jsonDecode(raw);
      if (parsed is Map<String, dynamic>) {
        return parsed;
      }
    } catch (_) {
      await prefs.remove(cacheKey);
    }
    return null;
  }

  static Future<void> writeJson({
    required String domain,
    required String key,
    required Map<String, dynamic> value,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final cacheKey = _cacheKey(domain, key);
    await prefs.setString(cacheKey, jsonEncode(value));
  }

  static String _cacheKey(String domain, String key) {
    final normalizedDomain = domain.trim().toLowerCase();
    final normalizedKey = key.trim().toLowerCase();
    final version = CacheRuntimeService.versionFor(normalizedDomain);
    return 'tf_swr_v1_${normalizedDomain}_$version::$normalizedKey';
  }
}
