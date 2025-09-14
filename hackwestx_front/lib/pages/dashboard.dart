import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/recommendation_card.dart';
import 'package:hackwestx_front/pages/widgets/inv_button.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

class Dashboard extends StatefulWidget {
  const Dashboard({super.key});

  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> {
  String lastUpdated = DateFormat('MM/dd/y – HH:mm:ss').format(DateTime.now());

  // current screener + results
  String? _strategy; // 'graham' | 'klarman' | 'templeton'
  bool _loading = false;

  String? _error;
  List<Map<String, dynamic>> _rows = const [];

  // -------------------- Backend base URL --------------------
  String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000';
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000'; // Android emulator
      case TargetPlatform.iOS:
        return 'http://127.0.0.1:8000';
      default:
        return 'http://127.0.0.1:8000'; // desktop
    }
    // If you want to use your LAN IP instead, e.g.:
    // return 'http://10.161.3.108:8000';
  }

  // -------------------- Helpers --------------------
  double _toDouble(dynamic v, [double def = 0.0]) {
    if (v == null) return def;
    if (v is num) return v.toDouble();
    if (v is String && v.trim().isEmpty) return def;
    return double.tryParse('$v') ?? def;
  }

  String _cap(String? s) {
    if (s == null || s.isEmpty) return '';
    return s[0].toUpperCase() + s.substring(1);
  }

  dynamic _metric(Map<String, dynamic> row, String name) {
    final metrics = row['metrics'];
    if (metrics is List) {
      for (final m in metrics) {
        if (m is Map && m['metric'] == name) return m['value'];
      }
    }
    return null;
  }

  Future<void> _loadScreener(String strategy) async {
    setState(() {
      _loading = true;
      _error = null;
      // _strategy = strategy;
    });

    final uri = Uri.parse('$baseUrl/$strategy?limit=200&top_n=20');
    try {
      final resp = await http.get(uri).timeout(const Duration(seconds: 90));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        throw Exception('HTTP ${resp.statusCode}: ${resp.body}');
      }
      final decoded = jsonDecode(resp.body) as Map<String, dynamic>;
      final rows =
          (decoded['rows'] as List?)?.cast<Map<String, dynamic>>() ??
          const <Map<String, dynamic>>[];

      setState(() {
        _rows = rows;
        lastUpdated = DateFormat(
          'yyyy-MM-dd – HH:mm:ss',
        ).format(DateTime.now());
      });
    } catch (e) {
      setState(() {
        _error = '$e';
        _rows = const [];
      });
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to load $strategy: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  // “Run AI Analysis” just refreshes the current screener (or picks a default)
  Future<void> _runAIAnalysis() async {
    await _loadScreener(_strategy ?? 'templeton');
  }

  @override
  Widget build(BuildContext context) {
    // Build cards from backend rows
    final List<Widget> cards = _rows.map((row) {
      final investorLabel = _cap(_strategy ?? '');
      final sectorText = (row['Sector'] as String?) ?? investorLabel;

      // Pull some values that might live inside metrics[]
      final priceTo52wLow = _toDouble(_metric(row, 'PriceTo52wLow'));
      final earningsGrowth = _toDouble(_metric(row, 'EarningsGrowth%'));
      // drawdownFromHigh isn't provided by Templeton payload; leave 0.0
      final drawdownFromHigh = _toDouble(
        row['DrawdownFromHigh%'] ?? row['DrawdownFromHigh'],
      );

      return RecommendationCard(
        strategy: investorLabel,
        investor: investorLabel.isEmpty ? '—' : investorLabel,
        ticker: (row['Ticker'] as String?) ?? '',
        name: (row['Name'] as String?) ?? '',
        sector: sectorText,
        coreScore: _toDouble(row['CoreScore']),
        marketCap: _toDouble(row['MarketCap']),
        price: _toDouble(row['Price']),
        summary: '',
        // You can assemble a blurb here if desired from metrics[]
        pe: _toDouble(row['P/E']),
        pb: _toDouble(row['P/B']),
        priceTo52wLow: priceTo52wLow,
        dividendYield: _toDouble(row['DividendYield%']),
        roe: _toDouble(row['ROE%']),
        debtToEquity: _toDouble(row['DebtToEquity']),
        currentRatio: _toDouble(row['CurrentRatio']),
        earningsGrowth: earningsGrowth,
        drawdownFromHigh: drawdownFromHigh,
      );
    }).toList();

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
                  asset: 'assets/images/graham.png',
                  label: 'Benjamin Graham',
                  selected: _strategy == 'graham',
                  disabled: _loading,
                  onTap: () => _loadScreener(
                    'graham',
                  ), // <- closure, not _loadScreener('graham')
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: 'assets/images/klarman.png',
                  label: 'Seth Klarman',
                  selected: _strategy == 'klarman',
                  disabled: _loading,
                  onTap: () => _loadScreener('klarman'),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: 'assets/images/templeton.png',
                  label: 'John Templeton',
                  selected: _strategy == 'templeton',
                  disabled: _loading,
                  onTap: () => _loadScreener('templeton'),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: 'assets/images/buffett.png',
                  label: 'Warren Buffett',
                  selected: _strategy == 'buffett',
                  disabled: _loading,
                  onTap: () => _loadScreener('buffett'),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: 'assets/images/lynch.png',
                  label: 'Peter Lynch',
                  selected: _strategy == 'lynch',
                  disabled: _loading,
                  onTap: () => _loadScreener('lynch'),
                ),
              ),
              SizedBox(
                width: 110,
                child: InvButton(
                  asset: 'assets/images/soros.png',
                  label: 'George Soros',
                  selected: _strategy == 'soros',
                  disabled: _loading,
                  onTap: () => _loadScreener('soros'),
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

          if (_loading) const LinearProgressIndicator(),

          if (_error != null)
            Text(_error!, style: const TextStyle(color: Colors.red)),

          if (_rows.isNotEmpty)
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              children: cards,
            ),

          if (_rows.isEmpty && !_loading && _error == null)
            const Text(
              'No recommendations yet. Tap Graham, Klarman, or Templeton to fetch picks.',
              style: TextStyle(color: Colors.white70),
            ),
        ],
      ),
    );
  }
}
