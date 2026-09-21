import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import '../../core/network/graphql_api.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_primitives.dart';

class ProfileEditPage extends StatefulWidget {
  const ProfileEditPage({
    super.key,
    required this.token,
    required this.initialName,
    required this.initialEmail,
    required this.initialPhone,
    required this.initialLocation,
    required this.initialHeadline,
    required this.initialRoles,
    required this.initialCountry,
  });

  final String token;
  final String initialName;
  final String initialEmail;
  final String initialPhone;
  final String initialLocation;
  final String initialHeadline;
  final String initialRoles;
  final String initialCountry;

  @override
  State<ProfileEditPage> createState() => _ProfileEditPageState();
}

class _ProfileEditPageState extends State<ProfileEditPage> {
  late final TextEditingController _nameCtrl = TextEditingController(
    text: widget.initialName,
  );
  late final TextEditingController _emailCtrl = TextEditingController(
    text: widget.initialEmail,
  );
  late final TextEditingController _phoneCtrl = TextEditingController(
    text: widget.initialPhone,
  );
  late final TextEditingController _locationCtrl = TextEditingController(
    text: widget.initialLocation,
  );
  late final TextEditingController _headlineCtrl = TextEditingController(
    text: widget.initialHeadline,
  );
  late final TextEditingController _rolesCtrl = TextEditingController(
    text: widget.initialRoles,
  );
  late final TextEditingController _countryCtrl = TextEditingController(
    text: widget.initialCountry,
  );

  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _locationCtrl.dispose();
    _headlineCtrl.dispose();
    _rolesCtrl.dispose();
    _countryCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      const mutation = r'''
mutation UpdateMyProfile($input: UpdateProfileInput!) {
  updateMyProfile(input: $input) {
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
      await GraphQlApi.request(
        document: mutation,
        variables: <String, dynamic>{
          'input': <String, dynamic>{
            'name': _nameCtrl.text.trim(),
            'phone': _phoneCtrl.text.trim(),
            'location': _locationCtrl.text.trim(),
            'headline': _headlineCtrl.text.trim(),
            'preferredRoles': _rolesCtrl.text
                .split(',')
                .map((String e) => e.trim())
                .where((String e) => e.isNotEmpty)
                .toList(),
            'preferredCountry': _countryCtrl.text.trim(),
          },
        },
        token: widget.token,
      );
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _saving = false;
      });
      return;
    }
    if (mounted) {
      setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Modifier le profil')),
      body: Container(
        decoration: AppTheme.appBackground,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: <Widget>[
            const TfPanel(
              child: TfCallout(
                title: 'Profil ciblage',
                message:
                    'Ces champs pilotent la qualité du matching et les suggestions de candidature.',
                icon: Icons.track_changes_outlined,
              ),
            ),
            const SizedBox(height: 14),
            TfPanel(
              child: Column(
                children: <Widget>[
                  TextField(
                    controller: _nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Nom complet',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _emailCtrl,
                    enabled: false,
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _phoneCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Téléphone',
                      prefixIcon: Icon(Icons.phone_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _locationCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Localisation',
                      prefixIcon: Icon(Icons.location_on_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _countryCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Pays préféré',
                      prefixIcon: Icon(Icons.flag_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _headlineCtrl,
                    minLines: 2,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Headline',
                      prefixIcon: Icon(Icons.title),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _rolesCtrl,
                    minLines: 2,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Rôles ciblés',
                      hintText: 'Séparés par des virgules',
                      prefixIcon: Icon(Icons.work_outline),
                    ),
                  ),
                  if ((_error ?? '').isNotEmpty) ...<Widget>[
                    const SizedBox(height: 10),
                    Text(
                      _error!,
                      style: const TextStyle(
                        color: AppTheme.danger,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _saving
                              ? null
                              : () => Navigator.of(context).pop(false),
                          child: const Text('Annuler'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _saving ? null : _save,
                          icon: _saving
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.save_outlined),
                          label: Text(
                            _saving ? 'Enregistrement...' : 'Enregistrer',
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
