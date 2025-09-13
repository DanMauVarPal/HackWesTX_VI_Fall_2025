import 'package:flutter/material.dart';
import 'package:hackwestx_front/home/place_holder.dart';
import 'package:hackwestx_front/home/side_menu.dart';
import 'package:hackwestx_front/main.dart';

import '../pages/dashboard.dart';

class Shell extends StatefulWidget {
  const Shell();

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  AppSection current = AppSection.dashboard;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        final isWide = c.maxWidth >= 980;

        if (isWide) {
          return Scaffold(
            body: SafeArea(
              child: Row(
                children: [
                  SideMenu(
                    current: current,
                    onChange: (s) => setState(() => current = s),
                  ),
                  // Content
                  Expanded(child: _buildContent()),
                ],
              ),
            ),
          );
        } else {
          // Mobile: slide-out drawer keeps the same menu
          return Scaffold(
            drawer: Drawer(
              backgroundColor: const Color(0xFF0E152A),
              child: SafeArea(
                child: SideMenu(
                  current: current,
                  onChange: (s) {
                    setState(() => current = s);
                    Navigator.of(context).pop(); // close drawer
                  },
                  compact: true,
                ),
              ),
            ),
            appBar: AppBar(
              title: const Text('ValuePicker AI'),
              backgroundColor: const Color(0xFF0B1220),
            ),
            body: _buildContent(),
          );
        }
      },
    );
  }

  Widget _buildContent() {
    switch (current) {
      case AppSection.dashboard:
        return const Dashboard(); // all your main page goes here
      case AppSection.stockAnalysis:
        return const PlaceholderView('Stock Analysis');
      case AppSection.newsFeed:
        return const PlaceholderView('News Feed');
      case AppSection.books:
        return const PlaceholderView('Books');
      case AppSection.valueInvesting:
        return const PlaceholderView('Value Investing (Graham & Buffett)');
      case AppSection.realTimeAnalysis:
        return const PlaceholderView('Real-time Analysis (Live Market Data)');
    }
  }
}
