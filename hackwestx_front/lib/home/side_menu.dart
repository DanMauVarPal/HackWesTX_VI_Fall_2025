import 'package:flutter/material.dart';
import 'package:hackwestx_front/home/menu_group.dart';
import 'package:hackwestx_front/home/nav_item.dart';
import 'package:hackwestx_front/main.dart';

class SideMenu extends StatelessWidget {
  const SideMenu({
    required this.current,
    required this.onChange,
    this.compact = false,
  });

  final AppSection current;
  final ValueChanged<AppSection> onChange;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final bg = const Color(0xFF0E152A); // sidebar bg
    final border = Colors.white.withValues(alpha: .06);
    final headingStyle = Theme.of(context).textTheme.labelSmall!.copyWith(
      color: Colors.white.withOpacity(.55),
      letterSpacing: 1.1,
    );

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
          // Logo / brand
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
                        'ValuePicker AI',
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
                        icon: Icons.show_chart,
                        label: 'Stock Analysis',
                        selected: current == AppSection.stockAnalysis,
                        onTap: () => onChange(AppSection.stockAnalysis),
                      ),
                      NavItem(
                        icon: Icons.article_outlined,
                        label: 'News Feed',
                        selected: current == AppSection.newsFeed,
                        onTap: () => onChange(AppSection.newsFeed),
                      ),
                      NavItem(
                        icon: Icons.menu_book_outlined,
                        label: 'Books',
                        selected: current == AppSection.books,
                        onTap: () => onChange(AppSection.books),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8.0),
                    child: Text('AI FEATURES', style: headingStyle),
                  ),
                  const SizedBox(height: 8),
                  MenuGroup(
                    children: [
                      NavItem(
                        icon: Icons.lightbulb_outline,
                        label: 'Value Investing',
                        caption: 'Graham & Buffett Logic',
                        selected: current == AppSection.valueInvesting,
                        onTap: () => onChange(AppSection.valueInvesting),
                      ),
                      NavItem(
                        icon: Icons.bolt_outlined,
                        label: 'Real-time Analysis',
                        caption: 'Live Market Data',
                        selected: current == AppSection.realTimeAnalysis,
                        onTap: () => onChange(AppSection.realTimeAnalysis),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          // Bottom status card
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.white.withOpacity(.04),
                border: Border.all(color: border),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.auto_awesome,
                    size: 18,
                    color: Colors.white70,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'AI Assistant',
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF22D3EE).withOpacity(.15),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(
                        color: const Color(0xFF22D3EE).withOpacity(.6),
                      ),
                    ),
                    child: const Text(
                      'Analyzing 24/7',
                      style: TextStyle(fontSize: 11, color: Color(0xFF67E8F9)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
