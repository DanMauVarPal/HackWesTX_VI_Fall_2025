import 'package:flutter/material.dart';

class InvButton extends StatelessWidget {
  const InvButton({
    super.key,
    required this.asset,
    required this.label,
    required this.onTap,
    this.iconSize = 70,
  });

  final String asset;
  final String label;
  final VoidCallback onTap;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: iconSize,
            height: iconSize,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: .06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: .12)),
            ),
            clipBehavior: Clip.antiAlias,
            child: Image.asset(asset, fit: BoxFit.contain),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: t.labelMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
