import 'dart:async';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:talentflow_flutter/core/cv/cv_local_extractor.dart';
import 'package:talentflow_flutter/core/cv/cv_job_status.dart';
import 'package:talentflow_flutter/core/cv/cv_jobs_store.dart';
import 'package:talentflow_flutter/core/cv/cv_upload_service.dart';
import 'package:talentflow_flutter/core/feedback/app_snack.dart';
import 'package:talentflow_flutter/core/network/api_error.dart';
import 'package:talentflow_flutter/core/network/graphql_api.dart';
import 'package:talentflow_flutter/core/widgets/app_primitives.dart';
import 'package:talentflow_flutter/features/cv/cv_results_page.dart';

import 'widgets/cv_page_composer_panel.dart';
import 'widgets/cv_page_data.dart';
import 'widgets/cv_page_loading_state.dart';

part 'cv_page_screen_state.dart';
part 'cv_page_screen_actions.dart';
part 'cv_page_screen_io_actions.dart';

class CvPage extends StatefulWidget {
  const CvPage({super.key, required this.token});

  final String token;

  @override
  State<CvPage> createState() => _CvPageState();
}


