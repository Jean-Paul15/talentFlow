import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:talentflow_flutter/features/auth/auth_page.dart';

void main() {
  testWidgets('AuthPage renders login form', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.pumpWidget(
      MaterialApp(
        home: AuthPage(
          onAuthenticated:
              ({
                required token,
                required email,
                required name,
                refreshToken,
              }) async {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(AuthPage), findsOneWidget);
  });
}
