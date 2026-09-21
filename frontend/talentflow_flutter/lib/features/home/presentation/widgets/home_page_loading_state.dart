import 'package:flutter/material.dart';

import 'package:talentflow_flutter/core/widgets/app_primitives.dart';

class HomeLoadingState extends StatelessWidget {
  const HomeLoadingState({super.key});

  @override
  Widget build(BuildContext context) {
    return TfPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const <Widget>[
          TfSkeletonBlock(width: 220, height: 20),
          SizedBox(height: 12),
          TfSkeletonBlock(height: 16),
          SizedBox(height: 10),
          TfSkeletonBlock(height: 16),
          SizedBox(height: 10),
          TfSkeletonBlock(height: 16, width: 280),
        ],
      ),
    );
  }
}
