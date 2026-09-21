class CvDocumentAssessment {
  const CvDocumentAssessment({
    required this.documentKind,
    required this.cvConfidence,
    required this.userMessage,
  });

  final String documentKind;
  final double cvConfidence;
  final String userMessage;
}

class CvDocumentClassifier {
  static const List<String> _sectionMarkers = <String>[
    'curriculum vitae',
    'curriculum',
    'profil',
    'profile',
    'resume',
    'summary',
    'objective',
    'experience',
    'professional experience',
    'work history',
    'employment history',
    'formation',
    'education',
    'academic background',
    'etudes',
    'skills',
    'technical skills',
    'competences',
    'competencies',
    'projects',
    'project experience',
    'projets',
    'certifications',
    'langues',
    'languages',
    'references',
    'habilidades',
    'experiencia',
    'educacion',
  ];

  static const List<String> _experienceMarkers = <String>[
    'work experience',
    'professional experience',
    'employment history',
    'career history',
    'career summary',
    'experience professionnelle',
    'responsibilities',
    'missions',
    'achievements',
    'employment',
    'employer',
    'organization',
    'organisation',
    'company',
    'entreprise',
    'poste',
    'position',
    'stage',
    'internship',
    'freelance',
    'consulting',
    'alternance',
    'cdd',
    'cdi',
    'present',
    'current',
  ];

  static const List<String> _roleMarkers = <String>[
    'manager',
    'assistant',
    'consultant',
    'engineer',
    'ingenieur',
    'developer',
    'developpeur',
    'analyst',
    'analyste',
    'teacher',
    'enseignant',
    'accountant',
    'comptable',
    'sales',
    'commercial',
    'nurse',
    'designer',
    'technician',
    'technicien',
    'coordinator',
    'supervisor',
    'specialist',
    'officer',
  ];

  static const List<String> _educationMarkers = <String>[
    'master',
    'licence',
    'bachelor',
    'doctorat',
    'phd',
    'bts',
    'dut',
    'bac+',
    'ingenieur',
    'university',
    'universite',
    'faculty',
    'institute',
    'college',
    'degree',
    'diploma',
    'diplome',
    'certificate',
    'certificat',
    'school',
    'ecole',
    'lycee',
    'high school',
  ];

  static const List<String> _skillMarkers = <String>[
    'excel',
    'word',
    'powerpoint',
    'python',
    'java',
    'javascript',
    'typescript',
    'react',
    'flutter',
    'sql',
    'docker',
    'linux',
    'communication',
    'leadership',
    'gestion',
    'analyse',
    'salesforce',
    'accounting',
  ];

  static const List<String> _negativeMarkers = <String>[
    'lorem ipsum',
    'chapitre',
    'cours',
    'exercice',
    'facture',
    'invoice',
    'conditions generales',
    'politique de confidentialite',
    'privacy policy',
    'cookies',
    'article de blog',
    'blog article',
    'newsletter',
    'communique de presse',
    'press release',
    'formation certifiante',
    'chercheurs d emploi',
    'cliquez pour lire',
    'click to read',
    'urgent offre de formation',
    'terms of service',
  ];

  static const List<String> _academicProgramMarkers = <String>[
    'semestre',
    'ue',
    'ecue',
    'credits',
    'credit',
    'maquette pedagogique',
    'volume horaire',
    'cours magistral',
    'travaux diriges',
    'travaux pratiques',
    'syllabus',
    'prerequis',
    'pre requis',
    'objectif pedagogique',
    'objectifs pedagogiques',
    'modalites d evaluation',
    'evaluation continue',
    'programme de cours',
    'filiere',
  ];

  static const List<String> _jobPostingMarkers = <String>[
    'offre d emploi',
    'nous recrutons',
    'profil recherche',
    'postulez',
    'merci d envoyer votre cv',
    'mission principale',
    'candidature a envoyer',
  ];

  static const List<String> _cityMarkers = <String>[
    'lome',
    'abidjan',
    'accra',
    'cotonou',
    'dakar',
    'lagos',
    'paris',
    'remote',
    'hybride',
    'hybrid',
  ];

  static const List<String> _candidateHintMarkers = <String>[
    'candidature',
    'application',
    'open to',
    'available for',
    'a la recherche',
    'looking for',
    'seeking',
    'profil',
    'profile',
    'about me',
    'based in',
  ];

  CvDocumentAssessment assess(String rawText) {
    final original = rawText.replaceAll('\u0000', ' ').trim();
    final normalized = _fold(original);
    final words = original.split(RegExp(r'\s+')).where((String it) => it.isNotEmpty).length;
    final lineCount = original
        .split(RegExp(r'\r?\n'))
        .map((String line) => line.trim())
        .where((String line) => line.isNotEmpty)
        .length;
    final bullets = RegExp(r'^[\s\-*]', multiLine: true).allMatches(original).length;

    final contactSignals =
        (RegExp(r'\b[\w.+-]+@[\w.-]+\.[a-z]{2,}', caseSensitive: false).hasMatch(original) ? 1 : 0) +
        (RegExp(r'(?:\+?\d[\d\s().-]{7,}\d)').hasMatch(original) ? 1 : 0) +
        (RegExp(r'(linkedin|github|portfolio|behance|website)', caseSensitive: false).hasMatch(original) ? 1 : 0) +
        (_countMarkers(normalized, _cityMarkers) > 0 ? 1 : 0);
    final sectionSignals = _countMarkers(normalized, _sectionMarkers);
    final chronologySignals = _uniqueYears(original);
    final experienceSignals = _countMarkers(normalized, _experienceMarkers);
    final roleSignals = _countMarkers(normalized, _roleMarkers);
    final educationSignals = _countMarkers(normalized, _educationMarkers);
    final candidateHintSignals = _countMarkers(normalized, _candidateHintMarkers);
    final skillSignals = _countMarkers(normalized, _skillMarkers).clamp(0, 6);
    final negativeSignals = _countMarkers(normalized, _negativeMarkers);
    final academicProgramSignals = _countMarkers(normalized, _academicProgramMarkers);
    final jobPostingSignals = _countMarkers(normalized, _jobPostingMarkers);

    var score = 0.05;
    score += (contactSignals * 0.07).clamp(0, 0.22);
    score += (sectionSignals * 0.05).clamp(0, 0.24);
    score += (chronologySignals * 0.04).clamp(0, 0.18);
    score += (experienceSignals * 0.04).clamp(0, 0.16);
    score += (educationSignals * 0.04).clamp(0, 0.12);
    score += (roleSignals * 0.03).clamp(0, 0.08);
    score += (skillSignals * 0.01).clamp(0, 0.06);

    if (words >= 180) {
      score += 0.08;
    } else if (words >= 90) {
      score += 0.05;
    } else if (words >= 45) {
      score += 0.02;
    } else {
      score -= 0.14;
    }

    if (lineCount >= 6 || bullets >= 3) {
      score += 0.05;
    }

    if (_weirdRatio(original) > 0.06) {
      score -= 0.12;
    }
    score -= (negativeSignals * 0.12).clamp(0, 0.40);
    score -= (academicProgramSignals * 0.08).clamp(0, 0.42);
    score -= (jobPostingSignals * 0.10).clamp(0, 0.35);

    if (academicProgramSignals >= 3 &&
        experienceSignals == 0 &&
        candidateHintSignals == 0 &&
        roleSignals == 0) {
      score -= 0.30;
    }

    if (jobPostingSignals >= 2 &&
        candidateHintSignals == 0 &&
        contactSignals <= 1) {
      score -= 0.30;
    }

    if (negativeSignals == 0 &&
        words >= 20 &&
        contactSignals >= 2 &&
        (roleSignals >= 1 || skillSignals >= 2)) {
      score = score < 0.45 ? 0.45 : score;
    }

    if (negativeSignals == 0 &&
        words >= 20 &&
        sectionSignals >= 1 &&
        contactSignals >= 1) {
      score = score < 0.44 ? 0.44 : score;
    }

    if (negativeSignals == 0 &&
        words >= 20 &&
        candidateHintSignals >= 1 &&
        (contactSignals >= 1 || roleSignals >= 1)) {
      score = score < 0.43 ? 0.43 : score;
    }

    if (contactSignals == 0 &&
        sectionSignals < 2 &&
        chronologySignals == 0 &&
        experienceSignals == 0) {
      score -= 0.20;
    }

    final confidence = double.parse(score.clamp(0, 1).toStringAsFixed(3));
    var documentKind = confidence >= 0.62
        ? 'cv'
        : confidence < 0.42
            ? 'non_cv'
            : 'ambiguous';
    var adjustedConfidence = confidence;

    if (documentKind == 'cv' &&
        adjustedConfidence < 0.80 &&
        contactSignals == 0 &&
        candidateHintSignals == 0 &&
        experienceSignals == 0) {
      documentKind = 'ambiguous';
      adjustedConfidence = adjustedConfidence > 0.61 ? 0.61 : adjustedConfidence;
    }

    if (documentKind == 'cv' &&
        ((academicProgramSignals >= 3 && experienceSignals == 0) ||
            (jobPostingSignals >= 2 && candidateHintSignals == 0))) {
      documentKind = 'non_cv';
      adjustedConfidence = adjustedConfidence < 0.39 ? adjustedConfidence : 0.39;
    }

    return CvDocumentAssessment(
      documentKind: documentKind,
      cvConfidence: double.parse(adjustedConfidence.toStringAsFixed(3)),
      userMessage: documentKind == 'cv'
          ? 'CV importé. Le document semble exploitable pour l’analyse.'
          : documentKind == 'ambiguous'
              ? 'Le document a été lu, mais sa structure reste atypique. Une vérification plus stricte sera appliquée avant le diagnostic.'
              : 'Ce fichier ne ressemble pas à un CV exploitable. Importe un CV avec au moins ton profil, tes expériences ou tes compétences.',
    );
  }

  int _countMarkers(String text, List<String> markers) {
    return markers.where((String marker) => text.contains(_fold(marker))).length;
  }

  int _uniqueYears(String text) {
    final matches = RegExp(r'\b(?:19\d{2}|20\d{2})\b')
        .allMatches(text)
        .map((Match m) => m.group(0)!)
        .toSet();
    return matches.length.clamp(0, 4);
  }

  double _weirdRatio(String text) {
    if (text.isEmpty) return 1;
    final weird = RegExp(r'''[^A-Za-z0-9À-ÿ\s\.,;:!?'"()%\-\/@+#]''')
        .allMatches(text)
        .length;
    return weird / text.length;
  }

  String _fold(String text) {
    final normalized = text
        .toLowerCase()
        .replaceAll('à', 'a')
        .replaceAll('á', 'a')
        .replaceAll('â', 'a')
        .replaceAll('ä', 'a')
        .replaceAll('ç', 'c')
        .replaceAll('è', 'e')
        .replaceAll('é', 'e')
        .replaceAll('ê', 'e')
        .replaceAll('ë', 'e')
        .replaceAll('ì', 'i')
        .replaceAll('í', 'i')
        .replaceAll('î', 'i')
        .replaceAll('ï', 'i')
        .replaceAll('ñ', 'n')
        .replaceAll('ò', 'o')
        .replaceAll('ó', 'o')
        .replaceAll('ô', 'o')
        .replaceAll('ö', 'o')
        .replaceAll('ù', 'u')
        .replaceAll('ú', 'u')
        .replaceAll('û', 'u')
        .replaceAll('ü', 'u')
        .replaceAll('ý', 'y')
        .replaceAll('ÿ', 'y');
    return normalized.replaceAll(RegExp(r'\s+'), ' ').trim();
  }
}
