import 'package:flutter/material.dart';

class TitleBlock extends StatelessWidget {
  const TitleBlock({
    super.key,
    required this.ticker,
    required this.name,
    required this.sector,
  });

  final String ticker;
  final String name;
  final String sector;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          ticker,
          style: text.titleLarge!.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 2),
        Text(
          name,
          style: text.titleSmall!.copyWith(
            color: Colors.white.withOpacity(.85),
          ),
        ),
        const SizedBox(height: 2),
        Text(sector, style: text.bodySmall!.copyWith(color: Colors.white54)),
      ],
    );
  }
}
