import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/home.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: DefaultTextStyle(
        style: TextStyle(color: Colors.black),
        child: MyHome(),
      ),
    );
  }
}
