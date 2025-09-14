import 'package:flutter/material.dart';
import 'package:hackwestx_front/pages/widgets/metrics.dart';
import 'package:hackwestx_front/pages/widgets/pill.dart';
import 'package:hackwestx_front/pages/widgets/price.dart';
import 'package:hackwestx_front/pages/widgets/titleBox.dart';

class RecommendationCard extends StatelessWidget {
  const RecommendationCard({
    super.key,
    required this.investor,
    required this.ticker,
    required this.name,
    required this.sector,
    required this.coreScore,
    required this.marketCap,
    required this.summary,

    this.pe,
    this.pb,
    this.priceTo52wLow,
    this.dividendYield,
    this.roe,
    this.debtToEquity,
    this.currentRatio,
    this.earningsGrowth,
    this.drawdownFromHigh,
  });

  final String investor;
  final String ticker;
  final String name;
  final String sector;
  final double coreScore;
  final double marketCap;
  final double? pe;
  final double? pb;
  final double? priceTo52wLow;
  final double? dividendYield;
  final double? roe;
  final double? debtToEquity;
  final double? currentRatio;
  final double? earningsGrowth;
  final double? drawdownFromHigh;
  final String summary;

  Color get _cardBg => const Color(0xFF0F1629);

  Color get _border => const Color(0x10FFFFFF);

  Color get _accent => const Color(0xFF22D3EE);

  Color get _muted => Colors.white.withValues(alpha: .65);

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;

    final tiles = <Widget>[
      if (pe != null && !(investor == 'klarman' || investor == 'soros'))
        Metrics(title: 'P/E Ratio', value: pe!.toStringAsFixed(2)),

      if (pb != null &&
          !(investor == 'buffett' ||
              investor == 'lynch' ||
              investor == 'soros'))
        Metrics(title: 'P/B Ratio', value: pb!.toStringAsFixed(2)),

      if (priceTo52wLow != null &&
          !(investor == 'buffett' ||
              investor == 'klarman' ||
              investor == 'lynch' ||
              investor == 'soros'))
        Metrics(
          title: 'Price to 52w Low',
          value: priceTo52wLow!.toStringAsFixed(2),
        ),

      if (dividendYield != null &&
          !(investor == 'klarman' ||
              investor == 'lynch' ||
              investor == 'soros'))
        Metrics(
          title: 'Dividend Yield %',
          value: dividendYield!.toStringAsFixed(2),
        ),

      if (roe != null && !(investor == 'klarman' || investor == 'soros'))
        Metrics(title: 'ROE%', value: roe!.toStringAsFixed(2)),

      if (debtToEquity != null &&
          !(investor == 'klarman' || investor == 'soros'))
        Metrics(
          title: 'Debt to Equity',
          value: debtToEquity!.toStringAsFixed(2),
        ),

      if (currentRatio != null &&
          !(investor == 'buffett' ||
              investor == 'templeton' ||
              investor == 'lynch' ||
              investor == 'soros'))
        Metrics(
          title: 'Current Ratio',
          value: currentRatio!.toStringAsFixed(2),
        ),

      if (investor == 'templeton' && earningsGrowth != null)
        Metrics(
          title: 'Earnings Growth',
          value: earningsGrowth!.toStringAsFixed(2),
        ),

      if (investor == 'soros' && drawdownFromHigh != null)
        Metrics(
          title: 'Drawdown From High',
          value: drawdownFromHigh!.toStringAsFixed(2),
        ),
    ];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _border),
      ),
      child: LayoutBuilder(
        builder: (context, cons) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TitleBlock(ticker: ticker, name: name, sector: sector),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  spacing: 10,
                  children: [
                    Pill(text: "Buy", color: _accent),
                    Row(
                      children: [
                        const Icon(
                          Icons.shield_outlined,
                          size: 16,
                          color: Colors.white70,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '${coreScore.toStringAsFixed(2)}% match',
                          style: text.bodySmall!.copyWith(color: _muted),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),

            const SizedBox(height: 14),

            Column(
              children: [
                PriceColumn(label: 'Price', price: marketCap, highlight: false),
                const SizedBox(height: 10),
                PriceColumn(
                  label: 'Market Cap',
                  price: marketCap,
                  highlight: true,
                ),
              ],
            ),

            const SizedBox(height: 14),

            _metricsWrap(cons, tiles),

            const SizedBox(height: 16),
            Divider(color: Colors.white.withValues(alpha: .08), height: 1),
            const SizedBox(height: 12),

            Text(
              summary,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: text.bodyMedium!.copyWith(
                color: Colors.white.withValues(alpha: .9),
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricsWrap(BoxConstraints cons, List<Widget> metricTiles) {
    if (metricTiles.isEmpty) return const SizedBox.shrink();

    const gap = 12.0;
    final full = cons.maxWidth;
    final half = (full - gap) / 2;

    List<Widget> sized = [];
    for (final tile in metricTiles) {
      final needsFull = full < 560;
      sized.add(SizedBox(width: needsFull ? full : half, child: tile));
    }

    return Wrap(spacing: gap, runSpacing: gap, children: sized);
  }
}
