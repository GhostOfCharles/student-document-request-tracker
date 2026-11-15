import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:student_document_request_tracker/api.dart';
import 'package:student_document_request_tracker/design_system.dart';
import 'package:student_document_request_tracker/main.dart';

void main() {
  for (final width in [320.0, 390.0, 768.0, 1440.0]) {
    testWidgets('Dashboard preserves all counts at width $width', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = Api(
        client: MockClient((request) async {
          final body = request.url.path.endsWith('/auth/me')
              ? {'role': 'student', 'full_name': 'Test Student'}
              : {
                  'counts': {
                    'submitted': 2,
                    'needs_correction': 1,
                    'ready_for_release': 3,
                    'completed': 4,
                    'rejected': 5,
                  },
                  'recent_requests': [],
                  'unread_notifications': 1,
                };
          return http.Response(jsonEncode(body), 200);
        }),
      );
      await tester.pumpWidget(TrackerApp(api: api));
      await tester.pumpAndSettle();
      expect(find.byType(StudentStatCard), findsNWidgets(4));
      expect(find.text('6'), findsOneWidget);
      expect(find.text('All request statuses'), findsOneWidget);
      expect(find.byType(StudentStatusBadge), findsNWidgets(9));
    });
  }

  testWidgets('Skeleton rests when reduced motion is requested', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: const Scaffold(
            body: SingleChildScrollView(
              child: StudentLoadingState(dashboard: true),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(StudentSkeleton), findsWidgets);
    expect(tester.binding.transientCallbackCount, 0);
  });

  testWidgets('Busy action keeps its label and blocks duplicate presses', (
    tester,
  ) async {
    var calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: StudentTheme.data,
        home: Scaffold(
          body: StudentActionButton(
            loading: true,
            label: 'Submit request',
            onPressed: () => calls++,
          ),
        ),
      ),
    );
    await tester.tap(find.text('Submit request'));
    expect(calls, 0);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
