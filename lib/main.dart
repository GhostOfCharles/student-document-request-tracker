import 'package:flutter/material.dart';

import 'platform.dart';

import 'api.dart';
import 'requirements_form.dart';

void main() => runApp(const TrackerApp());
String label(dynamic value) => value
    .toString()
    .split('_')
    .map((s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}')
    .join(' ');

class TrackerApp extends StatelessWidget {
  final Api? api;
  const TrackerApp({super.key, this.api});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Student Document Request Tracker',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff255d69)),
      useMaterial3: true,
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
      cardTheme: const CardThemeData(margin: EdgeInsets.only(bottom: 12)),
    ),
    home: TrackerHome(api: api),
  );
}

class TrackerHome extends StatefulWidget {
  final Api? api;
  const TrackerHome({super.key, this.api});
  @override
  State<TrackerHome> createState() => _TrackerHomeState();
}

class _TrackerHomeState extends State<TrackerHome> {
  late final Api api;
  Json? actor;
  bool busy = true;
  String? error;
  String? success;
  String screen = 'Dashboard';
  dynamic data;
  Json? selected;
  Json? service;
  Json? formRequest;
  List history = [];
  List revisions = [];
  List requestNotes = [];
  final login = TextEditingController();
  final password = TextEditingController();
  final search = TextEditingController();
  final loginForm = GlobalKey<FormState>();
  String statusFilter = '';
  String jobsFilter = '';
  bool get staff => actor?['role'] == 'staff';

  @override
  void initState() {
    super.initState();
    api = widget.api ?? Api();
    restore();
  }

  @override
  void dispose() {
    login.dispose();
    password.dispose();
    search.dispose();
    super.dispose();
  }

  Future<void> restore() async {
    try {
      actor = await api.call('GET', '/auth/me');
      await load();
    } catch (e) {
      if (e is ApiError && e.status != 401) error = e.toString();
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> run(Future<void> Function() action) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) {
        setState(() {
          error = e.toString();
          if (e is ApiError && e.status == 401) {
            actor = null;
            screen = 'Dashboard';
            data = null;
            error = 'Your session expired. Sign in again.';
          }
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> signIn() => run(() async {
    if (!loginForm.currentState!.validate()) return;
    actor = await api.call('POST', '/auth/login', {
      'login': login.text.trim(),
      'password': password.text,
      'remember_me': false,
    });
    password.clear();
    await api.token();
    screen = 'Dashboard';
    await load();
  });

  Future<bool> confirm(String title, String content) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(content),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Go back'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Confirm'),
            ),
          ],
        ),
      ) ??
      false;

  Future<String?> prompt(
    String title, {
    String hint = 'Reason or instructions',
  }) async {
    final controller = TextEditingController();
    final form = GlobalKey<FormState>();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Form(
          key: form,
          child: TextFormField(
            controller: controller,
            autofocus: true,
            maxLength: 2000,
            minLines: 2,
            maxLines: 5,
            decoration: InputDecoration(labelText: hint),
            validator: (v) =>
                (v ?? '').trim().isEmpty ? 'This field is required.' : null,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Go back'),
          ),
          FilledButton(
            onPressed: () {
              if (form.currentState!.validate()) {
                Navigator.pop(ctx, controller.text.trim());
              }
            },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  Future<void> load() async {
    switch (screen) {
      case 'Dashboard':
        data = await api.call('GET', '/dashboard');
      case 'Services':
        data = await api.call('GET', '/services');
      case 'Requests':
        data = await api.call(
          'GET',
          '/requests?page_size=100&q=${Uri.encodeQueryComponent(search.text)}${statusFilter.isEmpty ? '' : '&status=$statusFilter'}',
        );
      case 'Notifications':
        data = await api.call('GET', '/notifications?page_size=100');
      case 'Automation':
        final jobs = await api.call(
          'GET',
          '/staff/automation/jobs?page_size=100${jobsFilter.isEmpty ? '' : '&status=$jobsFilter'}',
        );
        final alerts = await api.call('GET', '/staff/alerts?page_size=100');
        final runs = await api.call(
          'GET',
          '/staff/automation/runs?page_size=20',
        );
        final audits = await api.call('GET', '/staff/audit-logs?page_size=20');
        Json? summary;
        try {
          summary = await api.call('GET', '/staff/reports/daily');
        } on ApiError catch (e) {
          if (e.code != 'SUMMARY_NOT_GENERATED') rethrow;
        }
        data = {
          'jobs': jobs['items'],
          'alerts': alerts['items'],
          'runs': runs['items'],
          'audits': audits['items'],
          'summary': summary,
        };
      case 'Detail':
        await fetchDetail(selected!['id']);
      case 'Form':
        break;
    }
  }

  Future<void> navigate(String next) async {
    if (screen == 'Form' &&
        !await confirm(
          'Leave form?',
          'Unsaved entries will be lost. Staged files expire automatically.',
        )) {
      return;
    }
    await run(() async {
      screen = next;
      data = null;
      success = null;
      await load();
    });
  }

  Future<void> fetchDetail(int id) async {
    selected = await api.call('GET', '/requests/$id');
    history = (await api.call(
      'GET',
      '/requests/$id/history?page_size=100',
    ))['items'];
    revisions = (await api.call(
      'GET',
      '/requests/$id/revisions?page_size=100',
    ))['items'];
    requestNotes = (await api.call(
      'GET',
      '/requests/$id/notes?page_size=100',
    ))['items'];
  }

  Future<void> openRequest(int id) => run(() async {
    screen = 'Detail';
    await fetchDetail(id);
  });

  Future<void> workflow(String action, {Json extras = const {}}) async {
    if (busy) return;
    if (!await confirm(
      label(action.replaceAll('-', ' ')),
      'Confirm this action for ${selected!['request_number']}? Reload if another user changed the record.',
    )) {
      return;
    }
    success = null;
    await run(() async {
      final prefix = action == 'acknowledge' || action == 'cancel'
          ? ''
          : '/staff';
      await api.call('POST', '$prefix/requests/${selected!['id']}/$action', {
        'expected_row_version': selected!['row_version'],
        ...extras,
      });
      success = 'Action saved.';
      await fetchDetail(selected!['id']);
    });
  }

  Future<void> correctionDialog() async {
    final detail = selected!;
    final fields = detail['service']['version']['requirements'] as List;
    final target = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Choose correction target'),
        children: [
          for (final field in fields)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, 'requirement:${field['id']}'),
              child: Text(field['label']),
            ),
          if (detail['service']['version']['payment']['reference_required'])
            SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, 'payment_reference'),
              child: const Text('Payment reference'),
            ),
          if (detail['service']['version']['payment']['receipt_required'])
            SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, 'payment_receipt'),
              child: const Text('Payment receipt'),
            ),
        ],
      ),
    );
    if (target == null) return;
    final reason = await prompt('Correction instructions');
    if (reason == null) return;
    await workflow(
      'corrections',
      extras: {
        'general_instructions': reason,
        'items': [
          {
            'target_kind': target.startsWith('requirement:')
                ? 'requirement'
                : target,
            if (target.startsWith('requirement:'))
              'requirement_id': int.parse(target.split(':')[1]),
            'instruction': reason,
          },
        ],
      },
    );
  }

  Widget requestCards(List items) => Column(
    children: [
      if (items.isEmpty)
        const Padding(
          padding: EdgeInsets.all(24),
          child: Text('No requests yet.'),
        ),
      for (final item in items)
        Card(
          child: ListTile(
            title: Text(item['request_number']),
            subtitle: Text(
              '${item['service_name'] ?? ''}\n${label(item['status'])} • due ${item['due_at']}',
            ),
            isThreeLine: true,
            trailing: const Icon(Icons.chevron_right),
            onTap: () => openRequest(item['id']),
          ),
        ),
    ],
  );

  Widget dashboard() {
    final counts = data['counts'] as Json;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          staff ? 'Registrar overview' : 'Your request overview',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const Text('Week 13 development prototype • synthetic records only'),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final entry in counts.entries)
              Chip(label: Text('${label(entry.key)}: ${entry.value}')),
            Chip(
              label: Text(
                'Unread notifications: ${data['unread_notifications']}',
              ),
            ),
            if (staff)
              Chip(
                label: Text(
                  'Permanent failures: ${data['failed_automation_jobs']}',
                ),
              ),
          ],
        ),
        const SizedBox(height: 24),
        Text('Recent requests', style: Theme.of(context).textTheme.titleLarge),
        requestCards(data['recent_requests']),
      ],
    );
  }

  Future<void> serviceDetails(int id) => run(() async {
    final config = await api.call('GET', '/services/$id') as Json;
    if (!mounted) return;
    final v = config['version'];
    final start = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(v['name']),
        content: SizedBox(
          width: 500,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(v['description'] ?? ''),
                Text(v['eligibility_instructions'] ?? ''),
                Text(
                  'Version ${v['version_number']} • ${v['processing_days']} calendar days',
                ),
                Text(
                  v['payment']['required']
                      ? 'Fictional evidence: ${v['payment']['currency']} ${v['payment']['amount']}'
                      : 'No payment required',
                ),
                for (final field in v['requirements'])
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '${field['label']} • ${field['field_type']} • ${field['required'] ? 'required' : 'optional'}${field['help_text'] == null ? '' : '\n${field['help_text']}'}',
                    ),
                  ),
                if (v['payment']['required'])
                  Text(v['payment']['instructions']),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Close'),
          ),
          if (!staff)
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Create request'),
            ),
        ],
      ),
    );
    if (start == true) {
      service = config;
      formRequest = null;
      screen = 'Form';
      success = null;
    }
  });

  Widget services() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Published document services',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const SizedBox(height: 16),
      if (data['items'].isEmpty) const Text('No active published services.'),
      for (final item in data['items'])
        Card(
          child: ListTile(
            title: Text(item['name']),
            subtitle: Text(
              '${item['description']}\n${item['processing_days']} days • ${item['payment_required'] ? 'Fictional payment evidence' : 'No payment'}',
            ),
            isThreeLine: true,
            trailing: const Icon(Icons.chevron_right),
            onTap: () => serviceDetails(item['id']),
          ),
        ),
    ],
  );
  Widget fileButton(Json? file) => file == null
      ? const SizedBox.shrink()
      : TextButton.icon(
          onPressed: () =>
              openEvidence(api.uri('/files/${file['id']}').toString()),
          icon: const Icon(Icons.download),
          label: Text(
            '${file['original_filename']} (${file['size_bytes']} bytes)',
          ),
        );

  Widget revisionContent(Json revision, Json version) {
    String answerLabel(Json answer) {
      final field = (version['requirements'] as List).firstWhere(
        (f) => f['id'] == answer['requirement_id'],
      );
      dynamic value =
          answer['text_value'] ??
          answer['date_value'] ??
          answer['boolean_value'];
      value ??= (field['options'] as List).firstWhere(
        (o) => o['id'] == answer['selected_option_id'],
      )['label'];
      return '${field['label']}: $value';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final answer in revision['answers'])
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(answerLabel(answer)),
          ),
        for (final attachment in revision['attachments'])
          fileButton(attachment['file']),
        if (version['payment']['required']) ...[
          Text(
            'Fictional payment reference: ${revision['payment']['reference']}',
          ),
          fileButton(revision['payment']['receipt']),
        ],
      ],
    );
  }

  Widget detail() {
    final req = selected!;
    final state = req['status'];
    final version = req['service']['version'] as Json;
    final revision = req['latest_revision'] as Json;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          req['request_number'],
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        Text(
          '${version['name']} • pinned version ${version['version_number']}',
        ),
        Text(
          '${label(state)} • revision ${req['current_revision_number']} • row version ${req['row_version']}',
        ),
        Text('Due ${req['due_at']}'),
        if (staff)
          Text(
            'Student: ${req['student']['full_name']} (${req['student']['student_number']})',
          ),
        const Divider(height: 32),
        revisionContent(revision, version),
        if (version['payment']['required'])
          Text('Payment outcome: ${req['payment_outcome'] ?? 'Not reviewed'}'),
        if (req['open_correction_round'] != null) ...[
          const Divider(),
          Text(
            'Correction required: ${req['open_correction_round']['general_instructions']}',
          ),
          for (final item in req['open_correction_round']['items'])
            Text('• ${item['instruction']}'),
        ],
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (staff && state == 'submitted')
              FilledButton(
                onPressed: () => workflow('begin-review'),
                child: const Text('Begin review'),
              ),
            if (staff && state == 'under_review') ...[
              if (version['payment']['required'])
                for (final outcome in [
                  'verified',
                  'needs_correction',
                  'rejected',
                ])
                  OutlinedButton(
                    onPressed: () async {
                      String? note;
                      if (outcome != 'verified') {
                        note = await prompt('Payment ${label(outcome)}');
                        if (note == null) return;
                      }
                      await workflow(
                        'payment-reviews',
                        extras: {
                          'revision_id': revision['id'],
                          'outcome': outcome,
                          'review_note': ?note,
                        },
                      );
                    },
                    child: Text('Payment: ${label(outcome)}'),
                  ),
              FilledButton(
                onPressed: () => workflow(
                  'approve',
                  extras: {'confirm_requirements_valid': true},
                ),
                child: const Text('Approve requirements'),
              ),
              OutlinedButton(
                onPressed: correctionDialog,
                child: const Text('Request correction'),
              ),
              OutlinedButton(
                onPressed: () async {
                  final reason = await prompt('Reject request');
                  if (reason != null) {
                    await workflow('reject', extras: {'reason': reason});
                  }
                },
                child: const Text('Reject request'),
              ),
            ],
            if (staff && state == 'processing')
              FilledButton(
                onPressed: () => workflow(
                  'ready-for-release',
                  extras: {'confirm_prepared': true},
                ),
                child: const Text('Mark ready for release'),
              ),
            if (staff && state == 'ready_for_release')
              FilledButton(
                onPressed: () =>
                    workflow('release', extras: {'confirm_handover': true}),
                child: const Text('Confirm actual handover'),
              ),
            if (!staff && state == 'released')
              FilledButton(
                onPressed: () =>
                    workflow('acknowledge', extras: {'confirm_received': true}),
                child: const Text('Acknowledge receipt'),
              ),
            if (!staff && state == 'needs_correction')
              FilledButton(
                onPressed: () {
                  setState(() {
                    service = req['service'];
                    formRequest = req;
                    screen = 'Form';
                    success = null;
                  });
                },
                child: const Text('Correct and resubmit'),
              ),
            if (!staff && ['submitted', 'under_review'].contains(state))
              OutlinedButton(
                onPressed: () async {
                  final reason = await prompt('Cancel request');
                  if (reason != null) {
                    await workflow('cancel', extras: {'reason': reason});
                  }
                },
                child: const Text('Cancel request'),
              ),
          ],
        ),
        const Divider(height: 32),
        Text('Request notes', style: Theme.of(context).textTheme.titleLarge),
        for (final note in requestNotes)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(note['note_body']),
            subtitle: Text('${note['visibility']} • ${note['created_at']}'),
          ),
        if (staff)
          Wrap(
            children: [
              for (final visibility in ['student_visible', 'staff_only'])
                TextButton(
                  onPressed: () async {
                    final body = await prompt(
                      'Add ${label(visibility)} note',
                      hint: 'Note',
                    );
                    if (body == null) return;
                    await run(() async {
                      await api.call(
                        'POST',
                        '/staff/requests/${req['id']}/notes',
                        {'visibility': visibility, 'note_body': body},
                      );
                      await fetchDetail(req['id']);
                    });
                  },
                  child: Text('Add ${label(visibility)} note'),
                ),
            ],
          ),
        const Divider(height: 32),
        Text(
          'Immutable revision history',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        Wrap(
          children: [
            for (final rev in revisions)
              TextButton(
                onPressed: () => run(() async {
                  final old = await api.call(
                    'GET',
                    '/requests/${req['id']}/revisions/${rev['revision_number']}',
                  );
                  if (!mounted) return;
                  await showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: Text('Revision ${rev['revision_number']}'),
                      content: SizedBox(
                        width: 600,
                        child: SingleChildScrollView(
                          child: revisionContent(old, version),
                        ),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text('Close'),
                        ),
                      ],
                    ),
                  );
                }),
                child: Text('View revision ${rev['revision_number']}'),
              ),
          ],
        ),
        Text('Status timeline', style: Theme.of(context).textTheme.titleLarge),
        for (final event in history)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.history),
            title: Text(label(event['new_status'])),
            subtitle: Text(
              '${event['created_at']} • ${event['change_source']}\n${event['public_remarks'] ?? ''}',
            ),
          ),
      ],
    );
  }

  Widget notifications() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text('Notifications', style: Theme.of(context).textTheme.headlineSmall),
      TextButton(
        onPressed: () => run(() async {
          await api.call('POST', '/notifications/read-all');
          await load();
        }),
        child: const Text('Mark all read'),
      ),
      if (data['items'].isEmpty)
        const Text(
          'No notifications yet. The dedicated worker delivers queued events.',
        ),
      for (final n in data['items'])
        Card(
          child: ListTile(
            leading: Icon(
              n['read_at'] == null
                  ? Icons.mark_email_unread
                  : Icons.mark_email_read,
            ),
            title: Text(n['title']),
            subtitle: Text('${n['message']}\n${n['created_at']}'),
            isThreeLine: true,
            onTap: () => run(() async {
              await api.call('PATCH', '/notifications/${n['id']}/read');
              if (n['request_id'] != null) {
                screen = 'Detail';
                await fetchDetail(n['request_id']);
              } else {
                await load();
              }
            }),
          ),
        ),
    ],
  );

  Future<void> jobDialog(int id) => run(() async {
    final job = await api.call('GET', '/staff/automation/jobs/$id');
    if (!mounted) return;
    final action = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Job $id • ${label(job['status'])}'),
        content: SizedBox(
          width: 600,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Attempts ${job['attempt_count']}/${job['max_attempts']} • next ${job['next_attempt_at']}',
                ),
                Text(job['last_error_code'] ?? 'No failure'),
                if (job['resolution_note'] != null)
                  Text('Manual handling: ${job['resolution_note']}'),
                for (final attempt in job['attempts'])
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      'Attempt ${attempt['attempt_number']}: ${attempt['outcome']}',
                    ),
                    subtitle: Text(
                      '${attempt['started_at']} → ${attempt['finished_at']}\n${attempt['error_code'] ?? ''}',
                    ),
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          if (job['status'] == 'failed_permanently') ...[
            if (job['job_type'] == 'notification' && job['max_attempts'] < 9)
              TextButton(
                onPressed: () => Navigator.pop(ctx, 'retry'),
                child: const Text('Retry safely'),
              ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, 'resolve'),
              child: const Text('Record manual handling'),
            ),
          ],
        ],
      ),
    );
    if (action != null) {
      final note = await prompt(
        action == 'retry' ? 'Reason for retry' : 'Manual resolution note',
      );
      if (note != null) {
        await api.call('POST', '/staff/automation/jobs/$id/$action', {
          action == 'retry' ? 'reason' : 'resolution_note': note,
        });
        success = 'Recovery action recorded.';
        await load();
      }
    }
  });

  Widget automation() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Automation monitoring',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const Text(
        'Permanent failures are queried directly. Manual handling does not claim delivery succeeded.',
      ),
      const SizedBox(height: 16),
      Text(
        'Daily pending summary',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      if (data['summary'] == null)
        const Text('SUMMARY_NOT_GENERATED: no stored snapshot for today.')
      else ...[
        Text(
          'Asia/Manila date ${data['summary']['summary_date']} • generated ${data['summary']['generated_at']}',
        ),
        Wrap(
          spacing: 8,
          children: [
            for (final key in [
              'submitted_count',
              'under_review_count',
              'needs_correction_count',
              'processing_count',
              'ready_for_release_count',
              'released_count',
              'pending_total',
              'completed_today_count',
              'rejected_today_count',
              'cancelled_today_count',
              'aging_count',
              'escalated_count',
            ])
              Chip(label: Text('${label(key)}: ${data['summary'][key]}')),
          ],
        ),
      ],
      OutlinedButton(
        onPressed: () => run(() async {
          final now = DateTime.now()
              .toUtc()
              .add(const Duration(hours: 8))
              .toIso8601String()
              .substring(0, 10);
          await api.call('POST', '/staff/reports/daily/regenerate', {
            'date': now,
          });
          await load();
        }),
        child: const Text('Regenerate current local date'),
      ),
      const Divider(),
      Text('Open alerts', style: Theme.of(context).textTheme.titleLarge),
      if (data['alerts'].isEmpty) const Text('No open alerts.'),
      for (final alert in data['alerts'])
        ListTile(
          title: Text(
            '${label(alert['alert_type'])} • request ${alert['request_id']}',
          ),
          subtitle: Text(alert['triggered_at']),
          onTap: () => openRequest(alert['request_id']),
        ),
      const Divider(),
      Text('Durable jobs', style: Theme.of(context).textTheme.titleLarge),
      DropdownButton<String>(
        value: jobsFilter,
        isExpanded: true,
        items: [
          for (final status in [
            '',
            'pending',
            'running',
            'succeeded',
            'failed_permanently',
            'resolved_manually',
          ])
            DropdownMenuItem(
              value: status,
              child: Text(status.isEmpty ? 'All job states' : label(status)),
            ),
        ],
        onChanged: (value) {
          jobsFilter = value!;
          run(load);
        },
      ),
      if (data['jobs'].isEmpty) const Text('No matching jobs.'),
      for (final job in data['jobs'])
        Card(
          child: ListTile(
            title: Text('Job ${job['id']}: ${label(job['status'])}'),
            subtitle: Text(
              '${job['job_type']} • attempts ${job['attempt_count']}/${job['max_attempts']}\n${job['last_error_code'] ?? ''}',
            ),
            onTap: () => jobDialog(job['id']),
          ),
        ),
      const Divider(),
      Text('Schedule runs', style: Theme.of(context).textTheme.titleLarge),
      for (final r in data['runs'])
        ListTile(
          title: Text('${r['job_name']}: ${r['status']}'),
          subtitle: Text(
            '${r['started_at']} • scanned ${r['records_scanned']} • tasks ${r['tasks_created']} ${r['error_code'] ?? ''}',
          ),
        ),
      const Divider(),
      Text(
        'Sanitized activity log',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      for (final entry in data['audits'])
        ListTile(
          title: Text('${entry['action']} • ${entry['result']}'),
          subtitle: Text(
            '${entry['created_at']} • ${entry['target_type']} ${entry['target_id'] ?? ''}',
          ),
        ),
    ],
  );

  Widget content() {
    if (screen == 'Form') {
      return RequirementsForm(
        key: ValueKey('${service!['id']}-${formRequest?['id']}'),
        api: api,
        service: service!,
        request: formRequest,
        onSubmitted: (result) {
          success =
              'Submission confirmed: ${result['request_number']} • revision ${result['revision_number']}';
          openRequest(result['id']);
        },
      );
    }
    if (data == null && screen != 'Detail') {
      return const Text('Use Retry to load this view.');
    }
    switch (screen) {
      case 'Services':
        return services();
      case 'Detail':
        return selected == null ? const Text('Request unavailable.') : detail();
      case 'Requests':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              staff ? 'Registrar request queue' : 'My requests',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: search,
              decoration: InputDecoration(
                labelText: 'Tracking number',
                suffixIcon: IconButton(
                  onPressed: () => run(load),
                  icon: const Icon(Icons.search),
                ),
              ),
              onSubmitted: (_) => run(load),
            ),
            DropdownButton<String>(
              value: statusFilter,
              isExpanded: true,
              items: [
                for (final state in [
                  '',
                  'submitted',
                  'under_review',
                  'needs_correction',
                  'processing',
                  'ready_for_release',
                  'released',
                  'completed',
                  'rejected',
                  'cancelled',
                ])
                  DropdownMenuItem(
                    value: state,
                    child: Text(state.isEmpty ? 'All statuses' : label(state)),
                  ),
              ],
              onChanged: (value) {
                statusFilter = value!;
                run(load);
              },
            ),
            requestCards(data['items']),
          ],
        );
      case 'Notifications':
        return notifications();
      case 'Automation':
        return automation();
      default:
        return dashboard();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (actor == null) {
      return Scaffold(
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: loginForm,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.school_outlined, size: 52),
                    const SizedBox(height: 16),
                    Text(
                      'Student Document Request Tracker',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const Text('Week 13 • synthetic development accounts'),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: login,
                      decoration: const InputDecoration(
                        labelText: 'Email or student number',
                      ),
                      autofillHints: const [AutofillHints.username],
                      validator: (v) =>
                          (v ?? '').trim().isEmpty ? 'Enter your login.' : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: password,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Password'),
                      autofillHints: const [AutofillHints.password],
                      onFieldSubmitted: (_) {
                        if (!busy) signIn();
                      },
                      validator: (v) =>
                          (v ?? '').isEmpty ? 'Enter your password.' : null,
                    ),
                    if (error != null)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    const SizedBox(height: 16),
                    if (busy) const LinearProgressIndicator(),
                    FilledButton(
                      onPressed: busy ? null : signIn,
                      child: const Text('Sign in'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }
    final destinations = [
      'Dashboard',
      'Services',
      'Requests',
      'Notifications',
      if (staff) 'Automation',
    ];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Document requests'),
        actions: [
          IconButton(
            tooltip: 'Refresh current view',
            onPressed: busy ? null : () => run(load),
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: busy
                ? null
                : () async {
                    if (await confirm(
                      'Sign out?',
                      'Leave this development session?',
                    )) {
                      await run(() async {
                        await api.call('POST', '/auth/logout');
                        actor = null;
                        data = null;
                        selected = null;
                        screen = 'Dashboard';
                        api.csrf = null;
                      });
                    }
                  },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Column(
        children: [
          Material(
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${actor!['full_name']} • ${label(actor!['role'])}'),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      for (final destination in destinations)
                        TextButton(
                          onPressed: busy ? null : () => navigate(destination),
                          child: Text(
                            destination,
                            style: TextStyle(
                              fontWeight: screen == destination
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (busy) const LinearProgressIndicator(),
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.all(
                MediaQuery.sizeOf(context).width < 600 ? 16 : 32,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1000),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (success != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: Semantics(
                            liveRegion: true,
                            child: Text(
                              success!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ),
                      if (error != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Semantics(
                                liveRegion: true,
                                child: Text(
                                  error!,
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                ),
                              ),
                              TextButton(
                                onPressed: busy ? null : () => run(load),
                                child: const Text(
                                  'Retry / reload current state',
                                ),
                              ),
                            ],
                          ),
                        ),
                      if (!busy || data != null || screen == 'Form') content(),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
