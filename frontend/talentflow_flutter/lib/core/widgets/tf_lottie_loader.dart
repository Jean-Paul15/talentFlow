import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

class TfLottieLoader extends StatelessWidget {
  const TfLottieLoader({
    super.key,
    this.width = 72,
    this.height = 28,
  });

  final double width;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: height,
      child: Lottie.asset(
        'assets/animations/tf_loader_dots.json',
        repeat: true,
        fit: BoxFit.contain,
        frameRate: FrameRate.max,
      ),
    );
  }
}
