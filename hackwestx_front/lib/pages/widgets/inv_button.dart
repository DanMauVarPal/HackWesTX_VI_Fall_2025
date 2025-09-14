import 'package:flutter/material.dart';

class InvButton extends StatelessWidget {
  final String asset;
  final String label;
  final VoidCallback? onTap; // <- pass the callback, don't call it
  final bool selected; // highlight the active strategy
  final bool disabled; // prevent double taps while loading
  final double size;

  const InvButton({
    super.key,
    required this.asset,
    required this.label,
    this.onTap,
    this.selected = false,
    this.disabled = false,
    this.size = 72,
  });

  @override
  Widget build(BuildContext context) {
    final baseBorder = BorderRadius.circular(14);
    final theme = Theme.of(context);
    final borderColor = selected
        ? theme.colorScheme.primary
        : Colors.white.withValues(alpha: 0.12);

    return MouseRegion(
      cursor: disabled
          ? SystemMouseCursors.forbidden
          : SystemMouseCursors.click,
      child: FocusableActionDetector(
        enabled: !disabled,
        mouseCursor: disabled
            ? SystemMouseCursors.forbidden
            : SystemMouseCursors.click,
        child: InkWell(
          // IMPORTANT: do NOT call onTap(); just pass it
          onTap: disabled ? null : onTap,
          borderRadius: baseBorder,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                curve: Curves.easeOut,
                width: size,
                height: size,
                decoration: BoxDecoration(
                  borderRadius: baseBorder,
                  border: Border.all(width: 2, color: borderColor),
                  boxShadow: selected
                      ? [
                          BoxShadow(
                            color: theme.colorScheme.primary.withValues(
                              alpha: 0.35,
                            ),
                            blurRadius: 16,
                          ),
                        ]
                      : const [],
                ),
                clipBehavior: Clip.antiAlias,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    Image.asset(asset, fit: BoxFit.cover),
                    if (disabled)
                      Container(
                        color: Colors.black.withValues(alpha: 0.35),
                        alignment: Alignment.center,
                        child: const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Text(
                label,
                textAlign: TextAlign.center,
                style: theme.textTheme.labelMedium,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
