import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/panel.dart';
import 'package:hackwestx_front/pages/recommendation_card.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

class Dashboard extends StatefulWidget {
  const Dashboard({super.key});

  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> {
  String lastUpdated = DateFormat('MM/dd/y – HH:mm:ss').format(DateTime.now());

  Future<void> _runAIAnalysis() async {
    await fetchAndShow(context, "analyze"); // your API call
    if (!mounted) return;
    setState(() {
      lastUpdated = DateFormat('yyyy-MM-dd – HH:mm:ss').format(DateTime.now());
    });
  }

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
                onPressed: _runAIAnalysis, // ✅ updates when clicked
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
          Row(
            children: [
              Text(
                "Latest AI Recommended Stocks",
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              Text(
                "Updated: $lastUpdated",
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 7,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            children: [
              RecommendationCard(
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
              RecommendationCard(
                investor: 'Graham',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
              RecommendationCard(
                investor: 'Templeton',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
              RecommendationCard(
                investor: 'Klarman',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
              RecommendationCard(
                investor: 'Lynch',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
              RecommendationCard(
                investor: 'Soros',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Energy',
                coreScore: 62.9,
                marketCap: 478166122496.0,
                summary: '',
                pe: 15.931819,
                pb: 1.820927,
                priceTo52wLow: 1.1468302658486706,
                dividendYield: 3.53,
                roe: 11.831000399999999,
                debtToEquity: 14.442,
                currentRatio: 1.249,
                earningsGrowth: -23.599999999999998,
                drawdownFromHigh: 11.223682127592216,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

Future<void> fetchAndShow(BuildContext context, String func) async {
  final url = Uri.parse("http://10.0.2.2:8000/$func");
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
