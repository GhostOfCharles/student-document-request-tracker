import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:student_document_request_tracker/api.dart';
import 'package:student_document_request_tracker/main.dart';
import 'package:student_document_request_tracker/requirements_form.dart';

Json service() => {
  'id': 1,
  'version': {
    'id': 1,
    'name': 'Synthetic Certificate',
    'version_number': 1,
    'processing_days': 3,
    'eligibility_instructions': 'Test only',
    'payment': {'required': false, 'receipt_required': false},
    'requirements': [
      {
        'id': 1,
        'label': 'Purpose',
        'field_type': 'text',
        'required': true,
        'min_length': 3,
        'max_length': 200,
      },
      {
        'id': 2,
        'label': 'Category',
        'field_type': 'select',
        'required': true,
        'options': [
          {'id': 5, 'label': 'Scholarship'},
        ],
      },
      {
        'id': 3,
        'label': 'Synthetic confirmation',
        'field_type': 'checkbox',
        'required': true,
      },
      {'id': 4, 'label': 'Evidence', 'field_type': 'file', 'required': false},
    ],
  },
};

void main() {
  testWidgets('Login labels, invalid input and narrow layout', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = Api(
      client: MockClient(
        (r) async => http.Response(
          jsonEncode({'code': 'AUTHENTICATION_REQUIRED', 'detail': 'Sign in'}),
          401,
        ),
      ),
    );
    await tester.pumpWidget(TrackerApp(api: api));
    await tester.pumpAndSettle();
    expect(find.text('Email or student number'), findsOneWidget);
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Enter your login.'), findsOneWidget);
    expect(find.text('Enter your password.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Dynamic fields and required server-configured validation', (
    tester,
  ) async {
    final api = Api(client: MockClient((r) async => http.Response('{}', 200)));
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: RequirementsForm(
              api: api,
              service: service(),
              onSubmitted: (_) {},
            ),
          ),
        ),
      ),
    );
    expect(find.text('Purpose *'), findsOneWidget);
    expect(find.text('Category *'), findsOneWidget);
    expect(find.text('Upload Evidence'), findsOneWidget);
    await tester.ensureVisible(find.text('Submit request'));
    await tester.tap(find.text('Submit request'));
    await tester.pumpAndSettle();
    expect(find.text('This field is required.'), findsOneWidget);
    expect(find.text('Select an option.'), findsOneWidget);
    expect(find.text('This confirmation is required.'), findsOneWidget);
  });

  testWidgets('Correction form disables unchanged requirements', (
    tester,
  ) async {
    final req = {
      'id': 1,
      'row_version': 3,
      'open_correction_round': {
        'id': 1,
        'general_instructions': 'Fix purpose',
        'items': [
          {
            'target_kind': 'requirement',
            'requirement_id': 1,
            'instruction': 'Fix purpose',
          },
        ],
      },
      'latest_revision': {
        'answers': [
          {'requirement_id': 1, 'text_value': 'Old purpose'},
          {'requirement_id': 2, 'selected_option_id': 5},
          {'requirement_id': 3, 'boolean_value': true},
        ],
        'attachments': [],
        'payment': {'reference': null, 'receipt': null},
      },
    };
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: RequirementsForm(
              api: Api(
                client: MockClient((r) async => http.Response('{}', 200)),
              ),
              service: service(),
              request: req,
              onSubmitted: (_) {},
            ),
          ),
        ),
      ),
    );
    expect(
      tester.widget<TextFormField>(find.byType(TextFormField).first).enabled,
      isTrue,
    );
    expect(
      tester
          .widget<DropdownButtonFormField<int>>(
            find.byType(DropdownButtonFormField<int>),
          )
          .onChanged,
      isNull,
    );
    expect(find.textContaining('Fix purpose'), findsOneWidget);
  });

  test('API returns safe network and validation errors', () async {
    final api = Api(
      client: MockClient(
        (r) async => http.Response(
          jsonEncode({
            'code': 'VALIDATION_FAILED',
            'detail': 'Missing evidence',
            'field_errors': [
              {'field': 'requirement_4', 'message': 'Required'},
            ],
          }),
          422,
        ),
      ),
    );
    expect(
      () => api.call('GET', '/requests'),
      throwsA(
        isA<ApiError>().having((e) => e.code, 'code', 'VALIDATION_FAILED'),
      ),
    );
    final offline = Api(
      client: MockClient((r) async => throw Exception('socket')),
    );
    expect(
      () => offline.call('GET', '/dashboard'),
      throwsA(isA<ApiError>().having((e) => e.code, 'code', 'NETWORK_ERROR')),
    );
  });
}
