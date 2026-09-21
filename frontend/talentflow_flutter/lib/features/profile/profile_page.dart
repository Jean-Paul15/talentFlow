import 'package:flutter/material.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

import '../../core/cache/cache_runtime_service.dart';
import '../../core/cache/swr_cache_store.dart';
import '../../core/feedback/app_snack.dart';
import '../../core/network/graphql_api.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';
import '../legal/legal_document_page.dart';
import '../legal/legal_documents.dart';
import 'profile_edit_page.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({
    super.key,
    required this.token,
    required this.fallbackEmail,
    required this.onOpenOnboarding,
  });

  final String token;
  final String fallbackEmail;
  final VoidCallback onOpenOnboarding;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _loading = true;
  Map<String, dynamic> _me = <String, dynamic>{};

  @override
  void initState() {
    super.initState();
    CacheRuntimeService.changeTick.addListener(_onCacheVersionChanged);
    _load();
  }

  @override
  void dispose() {
    CacheRuntimeService.changeTick.removeListener(_onCacheVersionChanged);
    super.dispose();
  }

  void _onCacheVersionChanged() {
    if (!mounted) return;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
    });

    final cached = await SwrCacheStore.readJson(domain: 'profile', key: 'me');
    if (cached != null && mounted) {
      final me = (cached['me'] as Map<String, dynamic>? ?? <String, dynamic>{});
      setState(() {
        _me = me;
        _loading = false;
      });
    }

    try {
      const query = r'''
query Me {
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
}
''';
      final data = await GraphQlApi.request(
        document: query,
        token: widget.token,
      );
      final me = (data['me'] as Map<String, dynamic>? ?? <String, dynamic>{});
      if (!mounted) return;
      setState(() {
        _me = me;
        _loading = false;
      });
      await SwrCacheStore.writeJson(
        domain: 'profile',
        key: 'me',
        value: <String, dynamic>{
          'me': me,
          'savedAt': DateTime.now().toIso8601String(),
        },
      );
    } catch (e) {
      if (!mounted) return;
      final message = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _loading = false;
      });
      AppSnack.show(context, message: message, type: AppSnackType.error);
    }
  }

  Future<void> _openEdit() async {
    final updated = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => ProfileEditPage(
          token: widget.token,
          initialName: (_me['name'] ?? '').toString(),
          initialEmail: (_me['email'] ?? widget.fallbackEmail).toString(),
          initialPhone: (_me['phone'] ?? '').toString(),
          initialLocation: (_me['location'] ?? '').toString(),
          initialHeadline: (_me['headline'] ?? '').toString(),
          initialRoles:
              ((_me['preferredRoles'] as List<dynamic>? ?? const <dynamic>[])
                  .map((e) => e.toString())
                  .where((e) => e.isNotEmpty)
                  .join(', ')),
          initialCountry: (_me['preferredCountry'] ?? '').toString(),
        ),
      ),
    );
    if (updated == true) await _load();
  }

  Future<void> _openLegal(LegalDocumentType type) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => LegalDocumentPage(type: type)),
    );
  }

  int _completeness() {
    final checks = <bool>[
      (_me['name'] ?? '').toString().trim().isNotEmpty,
      (_me['phone'] ?? '').toString().trim().isNotEmpty,
      (_me['location'] ?? '').toString().trim().isNotEmpty,
      (_me['headline'] ?? '').toString().trim().isNotEmpty,
      ((_me['preferredRoles'] as List<dynamic>? ?? const <dynamic>[])
          .isNotEmpty),
      (_me['preferredCountry'] ?? '').toString().trim().isNotEmpty,
    ];
    return ((checks.where((v) => v).length / checks.length) * 100).round();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.gold),
      );
    }

    final name = (_me['name'] ?? '').toString().trim();
    final email = (_me['email'] ?? widget.fallbackEmail).toString();
    final headline = (_me['headline'] ?? '').toString();
    final location = (_me['location'] ?? '').toString();
    final country = (_me['preferredCountry'] ?? '').toString();
    final phone = (_me['phone'] ?? '').toString();
    final roles = (_me['preferredRoles'] as List<dynamic>? ?? const <dynamic>[])
        .map((e) => e.toString())
        .where((e) => e.isNotEmpty)
        .toList();
    final completeness = _completeness();

    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.gold,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 4),
            child: Row(
              children: <Widget>[
                Text(
                  'Profil',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                SizedBox(
                  height: 36,
                  child: FilledButton.icon(
                    onPressed: _openEdit,
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      textStyle: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    icon: const Icon(
                      PhosphorIconsRegular.pencilSimple,
                      size: 14,
                    ),
                    label: const Text('Modifier'),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          TfReveal(
            delay: const Duration(milliseconds: 40),
            child: TfCard(
              variant: TfCardVariant.glass,
              padding: const EdgeInsets.all(16),
              child: Row(
                children: <Widget>[
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      color: AppTheme.mist,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      (name.isNotEmpty ? name[0] : email[0]).toUpperCase(),
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: AppTheme.goldDark,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          name.isEmpty ? 'Profil à compléter' : name,
                          style: Theme.of(context).textTheme.titleSmall
                              ?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          headline.isEmpty
                              ? 'Ajoute un titre pour ton positionnement.'
                              : headline,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: AppTheme.inkSoft, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TfReveal(
            delay: const Duration(milliseconds: 90),
            child: TfCard(
              variant: TfCardVariant.glass,
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      TfProgressRing(
                        value: completeness,
                        label: 'Completude',
                        size: 64,
                        strokeWidth: 4,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              completeness == 100
                                  ? 'Profil complet'
                                  : 'À renforcer',
                              style: Theme.of(context).textTheme.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              completeness == 100
                                  ? 'Ton profil est prêt pour candidater.'
                                  : 'Complète les champs manquants.',
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(color: AppTheme.inkSoft),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TfReveal(
            delay: const Duration(milliseconds: 140),
            child: TfCard(
              variant: TfCardVariant.glass,
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(
                        PhosphorIconsBold.identificationCard,
                        size: 14,
                        color: AppTheme.inkSoft,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Informations',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _InfoRow(
                    icon: PhosphorIconsRegular.envelope,
                    label: 'Email',
                    value: email,
                  ),
                  _InfoRow(
                    icon: PhosphorIconsRegular.phone,
                    label: 'Téléphone',
                    value: phone,
                  ),
                  _InfoRow(
                    icon: PhosphorIconsRegular.mapPin,
                    label: 'Localisation',
                    value: location,
                  ),
                  _InfoRow(
                    icon: PhosphorIconsRegular.globe,
                    label: 'Pays cible',
                    value: country,
                  ),
                  _InfoRow(
                    icon: PhosphorIconsRegular.briefcase,
                    label: 'Roles cibles',
                    value: roles.join(', '),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TfReveal(
            delay: const Duration(milliseconds: 170),
            child: TfCard(
              variant: TfCardVariant.glass,
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(
                        legalDocumentIcon(LegalDocumentType.termsOfUse),
                        size: 16,
                        color: AppTheme.inkSoft,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Cadre légal',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TfActionTile(
                    icon: legalDocumentIcon(LegalDocumentType.termsOfUse),
                    title: legalDocumentButtonLabel(
                      LegalDocumentType.termsOfUse,
                    ),
                    subtitle: 'Consulte les règles d’usage du service.',
                    onTap: () => _openLegal(LegalDocumentType.termsOfUse),
                    accent: AppTheme.goldDark,
                  ),
                  const SizedBox(height: 10),
                  TfActionTile(
                    icon: legalDocumentIcon(LegalDocumentType.privacyPolicy),
                    title: legalDocumentButtonLabel(
                      LegalDocumentType.privacyPolicy,
                    ),
                    subtitle: 'Comprends comment les données sont utilisées.',
                    onTap: () => _openLegal(LegalDocumentType.privacyPolicy),
                    accent: AppTheme.teal,
                  ),
                  const SizedBox(height: 10),
                  TfActionTile(
                    icon: PhosphorIconsRegular.sparkle,
                    title: 'Revoir l’onboarding',
                    subtitle: 'Relance la présentation rapide de TalentFlow.',
                    onTap: widget.onOpenOnboarding,
                    accent: AppTheme.coral,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 16, color: AppTheme.inkMuted),
          const SizedBox(width: 10),
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: AppTheme.inkSoft,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? '-' : value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
