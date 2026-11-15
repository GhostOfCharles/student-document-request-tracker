import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'design_system.dart';

/// A bounded catalog presentation. Only the selected card exposes its actions.
class ServiceFocusCarousel extends StatefulWidget {
  final List<int> serviceIds;
  final IndexedWidgetBuilder itemBuilder;
  final String Function(int) labelBuilder;
  final bool enabled;

  const ServiceFocusCarousel({
    super.key,
    required this.serviceIds,
    required this.itemBuilder,
    required this.labelBuilder,
    this.enabled = true,
  });

  @override
  State<ServiceFocusCarousel> createState() => _ServiceFocusCarouselState();
}

class _ServiceFocusCarouselState extends State<ServiceFocusCarousel>
    with SingleTickerProviderStateMixin {
  final focus = FocusNode(debugLabel: 'Service focus carousel');
  late final AnimationController position = AnimationController.unbounded(
    vsync: this,
  );
  int selected = 0;
  double wheelDelta = 0;
  DateTime lastStep = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    position.addStatusListener((status) {
      if (mounted && !position.isAnimating) setState(() {});
    });
  }

  @override
  void didUpdateWidget(covariant ServiceFocusCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldId = oldWidget.serviceIds.isEmpty
        ? null
        : oldWidget.serviceIds[selected.clamp(
            0,
            oldWidget.serviceIds.length - 1,
          )];
    final found = oldId == null ? -1 : widget.serviceIds.indexOf(oldId);
    final next = found < 0 ? 0 : found;
    if (next != selected || found < 0) {
      selected = next;
      position.value = next.toDouble();
    }
  }

  @override
  void dispose() {
    focus.dispose();
    position.dispose();
    super.dispose();
  }

  void select(int index) {
    if (!widget.enabled || widget.serviceIds.isEmpty || position.isAnimating) {
      return;
    }
    final next = index.clamp(0, widget.serviceIds.length - 1);
    if (next == selected) return;
    setState(() => selected = next);
    position.animateTo(
      next.toDouble(),
      duration: MediaQuery.disableAnimationsOf(context)
          ? Duration.zero
          : const Duration(milliseconds: 280),
      curve: Curves.easeInOutCubic,
    );
  }

  void onSignal(PointerSignalEvent event) {
    if (event is! PointerScrollEvent || event.scrollDelta.dy == 0) return;
    GestureBinding.instance.pointerSignalResolver.register(event, (resolved) {
      // Claim even boundary events so the outer page never scrolls accidentally.
      final delta = (resolved as PointerScrollEvent).scrollDelta.dy;
      final now = DateTime.now();
      if (position.isAnimating ||
          now.difference(lastStep).inMilliseconds < 340) {
        wheelDelta = 0;
        return;
      }
      if (wheelDelta.sign != delta.sign) wheelDelta = 0;
      wheelDelta += delta;
      if (wheelDelta.abs() < 30) return;
      select(selected + (wheelDelta > 0 ? 1 : -1));
      wheelDelta = 0;
      lastStep = now;
    });
  }

  KeyEventResult onKey(FocusNode node, KeyEvent event) {
    final down = event.logicalKey == LogicalKeyboardKey.arrowDown;
    final up = event.logicalKey == LogicalKeyboardKey.arrowUp;
    if (!down && !up) return KeyEventResult.ignored;
    if (event is KeyDownEvent || event is KeyRepeatEvent) {
      select(selected + (down ? 1 : -1));
    }
    return KeyEventResult.handled;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.serviceIds.isEmpty) return const SizedBox.shrink();
    final height = (MediaQuery.sizeOf(context).height * .62).clamp(
      420.0,
      560.0,
    );
    return Focus(
      focusNode: focus,
      onKeyEvent: onKey,
      onFocusChange: (_) => setState(() {}),
      child: Column(
        children: [
          Semantics(
            container: true,
            explicitChildNodes: true,
            label: 'Document service focus carousel',
            child: TapRegion(
              onTapOutside: (_) {
                if (focus.hasFocus) focus.unfocus();
              },
              child: Listener(
                onPointerSignal: onSignal,
                onPointerDown: (_) => focus.requestFocus(),
                behavior: HitTestBehavior.opaque,
                child: AnimatedContainer(
                  key: const ValueKey('service-carousel-viewport'),
                  duration: StudentMotion.duration(context),
                  height: height,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: StudentColors.background,
                    borderRadius: BorderRadius.circular(StudentRadius.card),
                    border: Border.all(
                      color: focus.hasFocus
                          ? StudentColors.primary
                          : StudentColors.border,
                      width: focus.hasFocus ? 2 : 1,
                    ),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final cardHeight = height * .55;
                      final cardWidth = math.min(
                        680.0,
                        (constraints.maxWidth - 32) / 1.08,
                      );
                      return AnimatedBuilder(
                        animation: position,
                        builder: (context, _) {
                          final visible =
                              List.generate(widget.serviceIds.length, (i) => i)
                                  .where(
                                    (i) => (i - position.value).abs() <= 2.5,
                                  )
                                  .toList()
                                ..sort(
                                  (a, b) => (b - position.value)
                                      .abs()
                                      .compareTo((a - position.value).abs()),
                                );
                          return Stack(
                            children: [
                              for (final index in visible)
                                _card(
                                  context,
                                  index,
                                  cardWidth,
                                  cardHeight,
                                  constraints.maxWidth,
                                  height,
                                ),
                            ],
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: StudentSpace.itemGap),
          Semantics(
            liveRegion: true,
            child: Text(
              '${selected + 1} of ${widget.serviceIds.length} - ${widget.labelBuilder(selected)}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          if (widget.serviceIds.length > 1)
            Text(
              'Scroll here or focus this area and use Up / Down. Click a nearby card to select it.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
    );
  }

  Widget _card(
    BuildContext context,
    int index,
    double width,
    double height,
    double viewportWidth,
    double viewportHeight,
  ) {
    final offset = index - position.value;
    final distance = offset.abs();
    final scale = widget.serviceIds.length == 1
        ? 1.0
        : distance <= 1
        ? 1.08 - .16 * distance
        : .92 - .07 * (distance - 1).clamp(0, 1);
    final recess = distance.clamp(0.0, 1.0);
    final active = index == selected && !position.isAnimating;
    final transform = Matrix4.identity()
      ..setEntry(3, 2, .0007)
      ..rotateX(offset.clamp(-2.0, 2.0) * -.07)
      ..scaleByDouble(scale, scale, 1, 1);
    return Positioned(
      key: ValueKey('service-card-${widget.serviceIds[index]}'),
      left: (viewportWidth - width) / 2,
      top: (viewportHeight - height) / 2 + offset * height * .4,
      width: width,
      height: height,
      child: Transform(
        alignment: Alignment.center,
        transform: transform,
        child: Opacity(
          opacity: 1 - .45 * recess,
          child: ColorFiltered(
            colorFilter: ColorFilter.matrix([
              1 - .15 * recess,
              0,
              0,
              0,
              0,
              0,
              1 - .15 * recess,
              0,
              0,
              0,
              0,
              0,
              1 - .15 * recess,
              0,
              0,
              0,
              0,
              0,
              1,
              0,
            ]),
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(StudentRadius.card),
                boxShadow: [
                  BoxShadow(
                    color: StudentColors.text.withValues(
                      alpha: .2 * (1 - recess),
                    ),
                    blurRadius: 28,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  ExcludeFocus(
                    excluding: !active,
                    child: ExcludeSemantics(
                      excluding: !active,
                      child: IgnorePointer(
                        ignoring: !active,
                        child: _ScrollableCard(
                          child: widget.itemBuilder(context, index),
                        ),
                      ),
                    ),
                  ),
                  if (!active)
                    Positioned.fill(
                      child: Semantics(
                        button: true,
                        label: 'Focus ${widget.labelBuilder(index)}',
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: () {
                            focus.requestFocus();
                            select(index);
                          },
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ScrollableCard extends StatefulWidget {
  final Widget child;
  const _ScrollableCard({required this.child});
  @override
  State<_ScrollableCard> createState() => _ScrollableCardState();
}

class _ScrollableCardState extends State<_ScrollableCard> {
  final scroll = ScrollController();
  @override
  void dispose() {
    scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Material(
    color: StudentColors.surface,
    borderRadius: BorderRadius.circular(StudentRadius.card),
    clipBehavior: Clip.antiAlias,
    child: LayoutBuilder(
      builder: (context, constraints) => Scrollbar(
        controller: scroll,
        thumbVisibility: true,
        interactive: true,
        child: SingleChildScrollView(
          controller: scroll,
          primary: false,
          physics: const NeverScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: widget.child,
          ),
        ),
      ),
    ),
  );
}
