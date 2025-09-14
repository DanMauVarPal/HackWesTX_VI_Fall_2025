import 'package:flutter/material.dart';

class PriceColumn extends StatelessWidget {
  const PriceColumn({
    super.key,
    required this.label,
    required this.price,
    required this.highlight,
  });

  final String label;
  final double price;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: text.bodySmall!.copyWith(color: Colors.white60)),
        const SizedBox(height: 6),
        Text(
          '\$${price.toStringAsFixed(2)}',
          style: (highlight
              ? text.titleMedium!.copyWith(
                  color: const Color(0xFF34D399),
                  fontWeight: FontWeight.w800,
                )
              : text.titleMedium!.copyWith(fontWeight: FontWeight.w800)),
        ),
      ],
    );
  }
}
