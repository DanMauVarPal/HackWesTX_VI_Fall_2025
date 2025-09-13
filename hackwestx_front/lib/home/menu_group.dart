import 'package:flutter/material.dart';

class MenuGroup extends StatelessWidget {
  const MenuGroup({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(children: children);
  }
}
