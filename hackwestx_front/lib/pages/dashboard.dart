import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/panel.dart';

class Dashboard extends StatelessWidget {
  const Dashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        // subtle top gradient like your mock
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
          // ... put the rest of your dashboard widgets here ...
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
        ],
      ),
    );
  }
}
