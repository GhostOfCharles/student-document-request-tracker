import 'package:http/http.dart' as http;
import 'package:http/browser_client.dart';
import 'package:web/web.dart' as web;

http.Client platformClient() => BrowserClient()..withCredentials = true;
void openEvidence(String url) {
  web.window.open(url, '_blank', 'noopener');
}
