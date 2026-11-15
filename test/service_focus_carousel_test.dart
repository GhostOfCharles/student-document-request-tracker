import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:student_document_request_tracker/design_system.dart';
import 'package:student_document_request_tracker/service_focus_carousel.dart';

Widget catalog({
  List<int> ids = const [10, 20, 30, 40],
  ScrollController? scroll,
  VoidCallback? onAction,
}) => MaterialApp(
  theme: StudentTheme.data,
  home: Scaffold(
    body: SingleChildScrollView(
      controller: scroll,
      child: Column(
        children: [
          const TextField(
            decoration: InputDecoration(labelText: 'Outside search'),
          ),
          ServiceFocusCarousel(
            serviceIds: ids,
            labelBuilder: (i) => 'Service ${ids[i]}',
            itemBuilder: (context, i) => Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Text('Service ${ids[i]}'),
                  FilledButton(
                    onPressed: onAction ?? () {},
                    child: Text('Edit ${ids[i]}'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 1000),
        ],
      ),
    ),
  ),
);

void main() {
  testWidgets('Wheel advances one card without scrolling its parent', (
    tester,
  ) async {
    final scroll = ScrollController();
    addTearDown(scroll.dispose);
    await tester.pumpWidget(catalog(scroll: scroll));
    final box = find.byKey(const ValueKey('service-carousel-viewport'));
    final point = tester.getCenter(box);
    await tester.sendEventToBinding(
      PointerScrollEvent(position: point, scrollDelta: const Offset(0, 120)),
    );
    await tester.pumpAndSettle();
    expect(find.text('2 of 4 - Service 20'), findsOneWidget);
    expect(scroll.offset, 0);
    await tester.sendEventToBinding(
      const PointerScrollEvent(
        position: Offset(10, 590),
        scrollDelta: Offset(0, 150),
      ),
    );
    await tester.pumpAndSettle();
    expect(scroll.offset, greaterThan(0));
  });

  testWidgets('Arrows act only within carousel focus and stop at boundaries', (
    tester,
  ) async {
    await tester.pumpWidget(catalog());
    await tester.tap(find.byType(TextField));
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pumpAndSettle();
    expect(find.text('1 of 4 - Service 10'), findsOneWidget);
    final box = tester.getRect(
      find.byKey(const ValueKey('service-carousel-viewport')),
    );
    await tester.tapAt(box.topLeft + const Offset(5, 5));
    for (var i = 0; i < 6; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();
    }
    expect(find.text('4 of 4 - Service 40'), findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
    await tester.pumpAndSettle();
    expect(find.text('3 of 4 - Service 30'), findsOneWidget);
  });

  testWidgets(
    'Outside blank tap clears focus until the carousel is tapped again',
    (tester) async {
      await tester.pumpWidget(catalog());
      final viewport = find.byKey(const ValueKey('service-carousel-viewport'));
      final rect = tester.getRect(viewport);
      Color borderColor() =>
          ((tester.widget<AnimatedContainer>(viewport).decoration
                          as BoxDecoration)
                      .border
                  as Border)
              .top
              .color;
      await tester.tapAt(rect.topLeft + const Offset(5, 5));
      await tester.pumpAndSettle();
      expect(borderColor(), StudentColors.primary);
      await tester.tapAt(Offset(10, rect.bottom + 20));
      await tester.pumpAndSettle();
      expect(borderColor(), StudentColors.border);
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();
      expect(find.text('1 of 4 - Service 10'), findsOneWidget);
      await tester.sendEventToBinding(
        PointerScrollEvent(
          position: rect.center,
          scrollDelta: const Offset(0, 120),
        ),
      );
      await tester.pumpAndSettle();
      expect(borderColor(), StudentColors.border);
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();
      expect(find.text('2 of 4 - Service 20'), findsOneWidget);
      await tester.tapAt(rect.topLeft + const Offset(5, 5));
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();
      expect(borderColor(), StudentColors.primary);
      expect(find.text('3 of 4 - Service 30'), findsOneWidget);
    },
  );

  testWidgets('Recessed card selects without triggering its controls', (
    tester,
  ) async {
    var calls = 0;
    await tester.pumpWidget(catalog(onAction: () => calls++));
    final rect = tester.getRect(
      find.byKey(const ValueKey('service-carousel-viewport')),
    );
    await tester.tapAt(Offset(rect.center.dx, rect.bottom - 25));
    await tester.pumpAndSettle();
    expect(find.text('2 of 4 - Service 20'), findsOneWidget);
    expect(calls, 0);
    await tester.tap(find.text('Edit 20'));
    await tester.pumpAndSettle();
    expect(calls, 1);
  });

  testWidgets(
    'Filtering preserves service identity and handles empty results',
    (tester) async {
      await tester.pumpWidget(catalog());
      final rect = tester.getRect(
        find.byKey(const ValueKey('service-carousel-viewport')),
      );
      await tester.tapAt(rect.topLeft + const Offset(5, 5));
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();
      await tester.pumpWidget(catalog(ids: [20, 40]));
      await tester.pumpAndSettle();
      expect(find.text('1 of 2 - Service 20'), findsOneWidget);
      await tester.pumpWidget(catalog(ids: [40]));
      await tester.pumpAndSettle();
      expect(find.text('1 of 1 - Service 40'), findsOneWidget);
      await tester.pumpWidget(catalog(ids: []));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('service-carousel-viewport')),
        findsNothing,
      );
    },
  );
}
