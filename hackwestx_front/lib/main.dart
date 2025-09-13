import 'package:flutter/material.dart';
import 'package:hackwestx_front/home/shell.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF22D3EE),
      brightness: Brightness.dark,
    );

    return MaterialApp(
      title: 'HackWestX',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: scheme,
        scaffoldBackgroundColor: const Color(0xFF0B1220),
        textTheme: ThemeData.dark().textTheme.apply(
          bodyColor: Colors.white.withValues(alpha: .92),
          displayColor: Colors.white,
        ),
      ),
      home: Shell(),
    );
  }
}

enum AppSection {
  dashboard,
  stockAnalysis,
  newsFeed,
  books,
  valueInvesting,
  realTimeAnalysis,
}
