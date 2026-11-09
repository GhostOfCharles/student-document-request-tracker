import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:student_document_request_tracker/api.dart';
import 'package:student_document_request_tracker/requirements_form.dart';

void main() {
  testWidgets('Preview displays configured payment fields and blocks uploads', (
    tester,
  ) async {
    final service = <String, dynamic>{
      'id': 1,
      'version': {
        'id': 1,
        'name': 'Example document',
        'version_number': 1,
        'processing_days': 3,
        'eligibility_instructions': 'Example only',
        'payment': {
          'required': true,
          'amount': '50.00',
          'currency': 'PHP',
          'instructions': 'Example only',
          'reference_required': true,
          'receipt_required': false,
        },
        'requirements': [
          {
            'id': 9,
            'label': 'Supporting document',
            'field_type': 'file',
            'required': false,
            'allowed_mime_types': ['application/pdf'],
            'max_file_size_bytes': 1048576,
          },
        ],
      },
    };
    final api = Api(client: MockClient((_) async => http.Response('{}', 200)));
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: RequirementsForm(
              api: api,
              service: service,
              preview: true,
              onSubmitted: (_) => fail('Preview must not submit.'),
            ),
          ),
        ),
      ),
    );
    expect(find.text('Payment reference'), findsOneWidget);
    expect(find.text('Upload payment receipt'), findsNothing);
    expect(find.text('Submit request'), findsNothing);
    expect(
      tester
          .widget<OutlinedButton>(
            find.widgetWithText(OutlinedButton, 'Upload Supporting document'),
          )
          .onPressed,
      isNull,
    );
    expect(
      find.text('Preview only. Uploading and submission are disabled.'),
      findsOneWidget,
    );
  });
}
