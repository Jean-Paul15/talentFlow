import 'package:flutter/foundation.dart';

/// Broadcasts auth-expired signals across networking layers.
/// The app shell listens once and performs a clean logout.
class AuthSessionEvents {
  static final ValueNotifier<int> unauthorizedTick = ValueNotifier<int>(0);

  static void notifyUnauthorized() {
    unauthorizedTick.value = unauthorizedTick.value + 1;
  }
}

