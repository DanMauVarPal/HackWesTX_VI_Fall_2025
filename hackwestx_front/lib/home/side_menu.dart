import 'package:flutter/material.dart';
import 'package:hackwestx_front/home/menu_group.dart';
import 'package:hackwestx_front/home/nav_item.dart';
import 'package:hackwestx_front/main.dart';

class SideMenu extends StatelessWidget {
  const SideMenu({
    super.key,
    required this.current,
    required this.onChange,
    this.compact = false,
  });

  final AppSection current;
  final ValueChanged<AppSection> onChange;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final bg = const Color(0xFF0E152A);
    final border = Colors.white.withValues(alpha: .06);

    return Container(
      width: compact ? 300 : 280,
      height: double.infinity,
      decoration: BoxDecoration(
        color: bg,
        border: Border(right: BorderSide(color: border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [Color(0xFF60A5FA), Color(0xFF22D3EE)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                const Flexible(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Finance CoPilot',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Intelligent Stock Analysis',
                        style: TextStyle(fontSize: 11, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  MenuGroup(
                    children: [
                      NavItem(
                        icon: Icons.dashboard_outlined,
                        label: 'Dashboard',
                        selected: current == AppSection.dashboard,
                        onTap: () => onChange(AppSection.dashboard),
                      ),
                      NavItem(
                        icon: Icons.menu_book_outlined,
                        label: 'Books',
                        selected: current == AppSection.books,
                        onTap: () => onChange(AppSection.books),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.white.withValues(alpha: .04),
                border: Border.all(color: border),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
