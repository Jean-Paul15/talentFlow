import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/theme/app_theme.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

import 'legal_documents.dart';

class LegalDocumentPage extends StatelessWidget {
  const LegalDocumentPage({
    super.key,
    required this.type,
  });

  final LegalDocumentType type;

  @override
  Widget build(BuildContext context) {
    final doc = legalDocumentOf(type);

    return Scaffold(
      backgroundColor: AppTheme.paper,
      appBar: AppBar(
        title: Text(doc.title),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: <Widget>[
          TfCard(
            variant: TfCardVariant.hero,
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                TfPill(
                  label: doc.lastUpdatedLabel,
                  icon: Icons.event_note_rounded,
                  color: AppTheme.goldLight,
                  foreground: AppTheme.goldDark,
                ),
                const SizedBox(height: 12),
                Text(
                  doc.title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  doc.summary,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppTheme.inkSoft,
                        height: 1.5,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          ...doc.sections.map(
            (section) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TfCard(
                variant: TfCardVariant.standard,
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      section.title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 10),
                    ...section.body.map(
                      (line) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Container(
                              width: 8,
                              height: 8,
                              margin: const EdgeInsets.only(top: 6),
                              decoration: const BoxDecoration(
                                color: AppTheme.coral,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                line,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(height: 1.55),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
