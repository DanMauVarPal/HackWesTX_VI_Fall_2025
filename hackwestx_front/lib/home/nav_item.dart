import 'package:flutter/material.dart';

class NavItem extends StatelessWidget {
  const NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.caption,
  });

  final IconData icon;
  final String label;
  final String? caption;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final base = Colors.white.withOpacity(.78);
    final sub = Colors.white.withOpacity(.55);
    final selBg = const Color(0xFF1B2440);
    final border = Colors.white.withOpacity(.06);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            color: selected ? selBg : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            border: selected ? Border.all(color: border) : null,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            children: [
              Icon(icon, size: 20, color: selected ? Colors.white : base),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontWeight: selected
                            ? FontWeight.w700
                            : FontWeight.w500,
                        color: selected ? Colors.white : base,
                        fontSize: 14,
                      ),
                    ),
                    if (caption != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        caption!,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: sub),
                      ),
                    ],
                  ],
                ),
              ),
              if (selected)
                const Icon(
                  Icons.chevron_right,
                  color: Colors.white70,
                  size: 18,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
