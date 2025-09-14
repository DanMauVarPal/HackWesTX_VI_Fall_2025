import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/recommendation_card.dart';
import 'package:hackwestx_front/pages/widgets/icon_button.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

class Dashboard extends StatefulWidget {
  const Dashboard({super.key});

  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> {
  String lastUpdated = DateFormat('MM/dd/y – HH:mm:ss').format(DateTime.now());
  bool _loading = false;

  Future<void> _onInvestorPressed(String func) async {
    if (!mounted) return;
    setState(() => _loading = true);
    try {
      await fetchAndShow(context, func);

      if (mounted) {
        lastUpdated = DateFormat('MM/dd/y – HH:mm:ss').format(DateTime.now());
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final page = Container(
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
          Text(
            'Value Investment Dashboard',
            style: Theme.of(
              context,
            ).textTheme.headlineLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/buffett.png',
                  label: 'Warren Buffett',
                  onTap: () => _onInvestorPressed("buffett"),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/graham.png',
                  label: 'Benjamin Graham',
                  onTap: () => _onInvestorPressed("graham"),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/klarman.png',
                  label: 'Seth Klarman',
                  onTap: () => _onInvestorPressed("klarman"),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/templeton.png',
                  label: 'John Templeton',
                  onTap: () => _onInvestorPressed("templeton"),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/lynch.png',
                  label: 'Peter Lynch',
                  onTap: () => _onInvestorPressed("lynch"),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: '../images/soros.png',
                  label: 'George Soros',
                  onTap: () => _onInvestorPressed("soros"),
                ),
              ),
            ],
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
            crossAxisCount: 2,
            shrinkWrap: true,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            children: [
              RecommendationCard(
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Buffet',
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
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Graham',
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
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Templeton',
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
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Klarman',
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
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Lynch',
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
                investor: 'Buffett',
                ticker: 'XOM',
                name: 'Exxon Mobil Corporation',
                sector: 'Soros',
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

    return Stack(
      children: [
        page,
        if (_loading)
          Positioned.fill(
            child: AbsorbPointer(
              child: Container(
                color: Colors.black.withOpacity(0.35),
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF101826),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: .1),
                      ),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2.6),
                        ),
                        SizedBox(width: 12),
                        Text('Loading…'),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
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
