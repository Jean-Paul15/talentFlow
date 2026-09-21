import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color ink = Color(0xFF111111);
  static const Color inkSoft = Color(0xFF6B7280);
  static const Color inkMuted = Color(0xFF9CA3AF);
  static const Color paper = Color(0xFFFFFFFF);
  static const Color mist = Color(0xFFF8FAFC);
  static const Color card = Color(0xFFFBFCFE);
  static const Color cardBorder = Color(0xFFE8EDF3);
  static const Color darkSurface = Color(0xFF1F2937);
  static const Color darkSoft = Color(0xFF374151);

  static const Color gold = Color(0xFFD4A853);
  static const Color goldDark = Color(0xFFB8893A);
  static const Color goldLight = Color(0xFFF0D48A);
  static const Color teal = Color(0xFF0D9488);
  static const Color tealDeep = Color(0xFF0F766E);
  static const Color coral = Color(0xFFE8734A);
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFEAB308);
  static const Color danger = Color(0xFFDC2626);

  static const LinearGradient ctaGradient = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: <Color>[goldLight, gold],
  );

  static const double radiusS = 8;
  static const double radiusM = 12;
  static const double radiusL = 14;

  static ThemeData get light {
    final base = ThemeData.light(useMaterial3: true);
    final text = GoogleFonts.manropeTextTheme(base.textTheme).copyWith(
      bodyLarge: GoogleFonts.manrope(
        fontSize: 15,
        fontWeight: FontWeight.w400,
        height: 1.55,
        color: ink,
      ),
      bodyMedium: GoogleFonts.manrope(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.5,
        color: ink,
      ),
      bodySmall: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.45,
        color: inkSoft,
      ),
      labelSmall: GoogleFonts.manrope(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: inkSoft,
        letterSpacing: 0.6,
      ),
      labelMedium: GoogleFonts.manrope(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: ink,
        letterSpacing: 0.2,
      ),
      titleSmall: GoogleFonts.manrope(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      titleMedium: GoogleFonts.manrope(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      titleLarge: GoogleFonts.manrope(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      headlineSmall: GoogleFonts.manrope(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      headlineMedium: GoogleFonts.manrope(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      headlineLarge: GoogleFonts.manrope(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: ink,
      ),
      displaySmall: GoogleFonts.manrope(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: ink,
      ),
    );

    return base.copyWith(
      scaffoldBackgroundColor: paper,
      colorScheme: const ColorScheme.light(
        primary: gold,
        secondary: teal,
        surface: card,
        onSurface: ink,
        onPrimary: Colors.white,
        outline: cardBorder,
      ),
      textTheme: text,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusL),
          side: const BorderSide(color: cardBorder),
        ),
        margin: EdgeInsets.zero,
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: mist,
        side: const BorderSide(color: cardBorder),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusS),
        ),
        labelStyle: GoogleFonts.manrope(
          color: ink,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        labelStyle: const TextStyle(color: inkSoft),
        hintStyle: const TextStyle(color: inkMuted),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 12,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusM),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusM),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusM),
          borderSide: const BorderSide(color: gold, width: 1.4),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusM),
          borderSide: const BorderSide(color: danger),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: goldLight,
          foregroundColor: darkSurface,
          minimumSize: const Size(0, 44),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusM),
          ),
          textStyle: GoogleFonts.manrope(
            fontWeight: FontWeight.w800,
            fontSize: 14,
            letterSpacing: 0.1,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ink,
          minimumSize: const Size(0, 44),
          side: const BorderSide(color: cardBorder),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusM),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: paper,
        surfaceTintColor: Colors.transparent,
        indicatorColor: Colors.transparent,
        labelTextStyle: WidgetStatePropertyAll(
          GoogleFonts.manrope(
            fontWeight: FontWeight.w700,
            fontSize: 11,
            color: ink,
            letterSpacing: 0.4,
          ),
        ),
        elevation: 0,
      ),
      dividerTheme: const DividerThemeData(
        color: cardBorder,
        thickness: 1,
        space: 1,
      ),
    );
  }

  static BoxDecoration get appBackground => const BoxDecoration(color: Colors.white);

  static List<BoxShadow> get softShadow => const <BoxShadow>[
    BoxShadow(color: Color(0x070F172A), blurRadius: 9, offset: Offset(0, 2)),
  ];

  static List<BoxShadow> get elevatedShadow => const <BoxShadow>[
    BoxShadow(color: Color(0x0D1E293B), blurRadius: 18, offset: Offset(0, 5)),
  ];

  static bool reducedMotion(BuildContext context) {
    final media = MediaQuery.maybeOf(context);
    return (media?.disableAnimations ?? false) ||
        (media?.accessibleNavigation ?? false);
  }
}

