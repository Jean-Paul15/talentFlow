class CvJobStatus {
  const CvJobStatus({
    required this.jobId,
    required this.status,
    required this.stage,
    required this.progress,
    required this.stageLabel,
    required this.etaHint,
    required this.resultReady,
    required this.updatedAt,
    this.error,
    this.historyId,
  });

  final String jobId;
  final String status;
  final String stage;
  final int progress;
  final String stageLabel;
  final String etaHint;
  final bool resultReady;
  final String updatedAt;
  final String? error;
  final String? historyId;

  factory CvJobStatus.fromMap(Map<String, dynamic> json) => CvJobStatus(
        jobId: (json['jobId'] ?? '').toString(),
        status: (json['status'] ?? '').toString(),
        stage: (json['stage'] ?? '').toString(),
        progress: int.tryParse('${json['progress'] ?? 0}') ?? 0,
        stageLabel: (json['stageLabel'] ?? '').toString(),
        etaHint: (json['etaHint'] ?? '').toString(),
        resultReady: json['resultReady'] == true,
        updatedAt: (json['updatedAt'] ?? '').toString(),
        error: json['error']?.toString(),
        historyId: json['historyId']?.toString(),
      );
}
