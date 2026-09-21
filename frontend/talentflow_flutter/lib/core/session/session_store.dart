import 'package:shared_preferences/shared_preferences.dart';

class SessionStore {
  static const String _tokenKey = 'tf_access_token';
  static const String _refreshTokenKey = 'tf_refresh_token';
  static const String _emailKey = 'tf_user_email';
  static const String _nameKey = 'tf_user_name';

  Future<void> save({
    required String token,
    String? refreshToken,
    String? email,
    String? name,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    if (refreshToken != null && refreshToken.trim().isNotEmpty) {
      await prefs.setString(_refreshTokenKey, refreshToken);
    } else {
      await prefs.remove(_refreshTokenKey);
    }
    if (email != null) {
      await prefs.setString(_emailKey, email);
    }
    if (name != null) {
      await prefs.setString(_nameKey, name);
    }
  }

  Future<SessionData> read() async {
    final prefs = await SharedPreferences.getInstance();
    return SessionData(
      token: prefs.getString(_tokenKey),
      refreshToken: prefs.getString(_refreshTokenKey),
      email: prefs.getString(_emailKey),
      name: prefs.getString(_nameKey),
    );
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_refreshTokenKey);
    await prefs.remove(_emailKey);
    await prefs.remove(_nameKey);
  }
}

class SessionData {
  const SessionData({
    required this.token,
    required this.refreshToken,
    required this.email,
    required this.name,
  });

  final String? token;
  final String? refreshToken;
  final String? email;
  final String? name;

  bool get isAuthenticated => token != null && token!.isNotEmpty;
}
