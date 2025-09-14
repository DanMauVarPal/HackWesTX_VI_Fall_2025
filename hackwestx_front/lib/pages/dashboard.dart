import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/panel.dart';
import 'package:http/http.dart' as http;

class Dashboard extends StatelessWidget {
  const Dashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF0B1220), Color(0xFF0B1220)],
        ),
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
        children: [
          Row(
            children: [
              Text(
                'Value Investment Dashboard',
                style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              FilledButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.bolt),
                label: const Text('Run AI Analysis'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Panel(
            child: Text(
              'Place your “Strong Buy Signals / Total Positions / Potential Upside” cards here.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 16),
          Panel(
            child: Text(
              'Latest AI Recommendations list/grid goes here…',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 7,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            children: [
              // Replace the first few placeholder buttons with these:
              FilledButton.icon(
                label: const Text("Templeton"),
                onPressed: () => fetchAndShow(context, "templeton"),
              ),
              FilledButton.icon(
                label: const Text("Klarman"),
                onPressed: () => fetchAndShow(context, "klarman"),
              ),
              FilledButton.icon(
                label: const Text("Graham"),
                onPressed: () => fetchAndShow(context, "graham"),
              ),

            ],
          ),
        ],
      ),
    );
  }
}

Future<void> fetchAndShow(BuildContext context, String func) async {
  final url = Uri.parse("http://10.161.3.108:8000/$func");
  final response = await http.get(url);

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);

    if (context.mounted) {
      showDialog(
        context: context,
        builder: (context) {
          return AlertDialog(
            title: const Text("API Response"),
            content: Text(data.toString()),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text("Close"),
              ),
            ],
          );
        },
      );
    }
  } else {
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Error: ${response.statusCode}")));
    }
  }
}
