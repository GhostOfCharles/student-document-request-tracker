import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'platform.dart';

import 'package:http_parser/http_parser.dart';

typedef Json = Map<String, dynamic>;

class ApiError implements Exception {
  final String code;
  final String message;
  final int status;
  ApiError(this.code, this.message, this.status);
  @override
  String toString() => '$message ($code)';
}

class Api {
  final http.Client client;
  String? csrf;
  static const base = String.fromEnvironment(
    'API_BASE',
    defaultValue: '/api/v1',
  );
  Api({http.Client? client}) : client = client ?? platformClient();

  Uri uri(String path) => Uri.parse('$base$path');

  Future<void> token() async {
    final result = await call('GET', '/auth/csrf');
    csrf = result['csrf_token'] as String;
  }

  Future<dynamic> call(String method, String path, [Json? body]) async {
    try {
      if (method != 'GET' && csrf == null) await token();
      final request = http.Request(method, uri(path));
      request.headers['Content-Type'] = 'application/json';
      if (method != 'GET') request.headers['X-CSRF-Token'] = csrf!;
      if (body != null) request.body = jsonEncode(body);
      final response = await http.Response.fromStream(
        await client.send(request).timeout(const Duration(seconds: 20)),
      );
      dynamic result;
      try {
        result = response.body.isEmpty
            ? <String, dynamic>{}
            : jsonDecode(response.body);
      } catch (_) {
        throw ApiError(
          'SERVER_ERROR',
          'The server returned an unreadable response.',
          response.statusCode,
        );
      }
      if (response.statusCode >= 400) {
        final fields = (result['field_errors'] as List? ?? [])
            .map((e) => '${e['field']}: ${e['message']}')
            .join('\n');
        if (result['code'] == 'CSRF_FAILED') csrf = null;
        throw ApiError(
          result['code'] ?? 'SERVER_ERROR',
          '${result['detail'] ?? 'The operation failed.'}${fields.isEmpty ? '' : '\n$fields'}',
          response.statusCode,
        );
      }
      return result;
    } on ApiError {
      rethrow;
    } catch (_) {
      throw ApiError(
        'NETWORK_ERROR',
        'Cannot reach the API. Check the connection and retry.',
        0,
      );
    }
  }

  Future<Json> upload(String name, Uint8List bytes) async {
    try {
      if (csrf == null) await token();
      final ext = name.split('.').last.toLowerCase();
      final mime = ext == 'pdf'
          ? 'application/pdf'
          : ext == 'png'
          ? 'image/png'
          : 'image/jpeg';
      final request = http.MultipartRequest('POST', uri('/files/staging'));
      request.headers['X-CSRF-Token'] = csrf!;
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: name,
          contentType: MediaType.parse(mime),
        ),
      );
      final response = await http.Response.fromStream(
        await client.send(request).timeout(const Duration(seconds: 30)),
      );
      final result = jsonDecode(response.body) as Json;
      if (response.statusCode != 201) {
        throw ApiError(result['code'], result['detail'], response.statusCode);
      }
      return result;
    } on ApiError {
      rethrow;
    } catch (_) {
      throw ApiError(
        'NETWORK_ERROR',
        'The upload failed. Your form entries are preserved; retry the upload.',
        0,
      );
    }
  }
}
