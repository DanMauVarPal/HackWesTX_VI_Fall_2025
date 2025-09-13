import 'package:flutter/material.dart';

class PlaceholderView extends StatelessWidget {
  const PlaceholderView(this.title);
  final String title;
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(title, style: Theme.of(context).textTheme.headlineMedium),
    );
    // Replace with your real screens as you build them.
  }
}
