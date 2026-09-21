import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class CvLoadingState extends StatelessWidget {
  const CvLoadingState({super.key});

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const <Widget>[
          TfSkeletonBlock(width: 240, height: 20),
          SizedBox(height: 16),
          TfSkeletonBlock(height: 16),
          SizedBox(height: 10),
          TfSkeletonBlock(height: 16),
          SizedBox(height: 10),
          TfSkeletonBlock(width: 180, height: 16),
          SizedBox(height: 18),
          TfSkeletonBlock(height: 110, radius: 24),
          SizedBox(height: 16),
          TfSkeletonBlock(height: 90, radius: 24),
        ],
      ),
    );
  }
}
