import 'package:flutter/material.dart';

import 'platform.dart';

import 'api.dart';
import 'design_system.dart';
import 'requirements_form.dart';
import 'service_management.dart';
import 'account_pages.dart';

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
    theme: StudentTheme.data,
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
  bool rememberMe = false;
  bool showLoginPassword = false;
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
      if (actor?['must_change_password'] != true) await load();
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
          if (e is ApiError &&
              e.status == 401 &&
              e.code == 'AUTHENTICATION_REQUIRED') {
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
      'remember_me': rememberMe,
    });
    password.clear();
    await api.token();
    screen = 'Dashboard';
    if (actor?['must_change_password'] != true) await load();
  });

  Future<void> registerAccount() async {
    final created = await Navigator.of(context)
        .push<bool>(MaterialPageRoute(builder: (_) => RegisterPage(api: api)));
    if (created == true && mounted) {
      setState(() {
        error = null;
        success = 'Account created. Sign in with your student number or email.';
      });
    }
  }

  Future<void> openAccount() async {
    final result = await Navigator.of(context).push<Json>(
      MaterialPageRoute(
        builder: (_) => AccountPage(api: api, actor: actor!),
      ),
    );
    if (!mounted) return;
    if (result?['signed_out'] == true) {
      setState(() {
        actor = null;
        data = null;
        screen = 'Dashboard';
        success = 'Password changed. Sign in again.';
      });
    } else {
      await run(() async {
        actor = await api.call('GET', '/auth/me');
        await load();
      });
    }
  }

  Future<bool> confirm(
    String title,
    String content, {
    bool destructive = false,
  }) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(content),
          actions: [
            OutlinedButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Go back'),
            ),
            destructive
                ? StudentActionButton(
                    label: title.toLowerCase().contains('cancel')
                        ? 'Confirm cancellation'
                        : title.toLowerCase().contains('reject')
                        ? 'Confirm rejection'
                        : 'Confirm action',
                    kind: StudentActionKind.destructive,
                    onPressed: () => Navigator.pop(ctx, true),
                  )
                : FilledButton(
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
          OutlinedButton(
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
        data = await api.call(
          'GET',
          staff ? '/staff/services?page_size=100' : '/services',
        );
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
    final destructive = action == 'reject' || action == 'cancel';
    if (!await confirm(
      label(action.replaceAll('-', ' ')),
      'Confirm this action for ${selected!['request_number']}? Reload if another user changed the record.',
      destructive: destructive,
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
      builder: (ctx) => AlertDialog(
        title: const Text('Choose correction target'),
        content: SizedBox(
          width: StudentDialogWidth.of(ctx),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final field in fields)
                  ListTile(
                    leading: const Icon(Icons.edit_note_rounded),
                    title: Text(field['label']),
                    onTap: () =>
                        Navigator.pop(ctx, 'requirement:${field['id']}'),
                  ),
                if (detail['service']['version']['payment']['reference_required'])
                  ListTile(
                    leading: const Icon(Icons.receipt_long_outlined),
                    title: const Text('Payment reference'),
                    onTap: () => Navigator.pop(ctx, 'payment_reference'),
                  ),
                if (detail['service']['version']['payment']['receipt_required'])
                  ListTile(
                    leading: const Icon(Icons.attach_file_rounded),
                    title: const Text('Payment receipt'),
                    onTap: () => Navigator.pop(ctx, 'payment_receipt'),
                  ),
              ],
            ),
          ),
        ),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
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
        StudentEmptyState(
          title: staff ? 'No requests yet' : 'No requests yet',
          message: staff
              ? 'New document requests will appear in this queue.'
              : 'Your submitted document requests will appear here.',
        ),
      for (final item in items)
        Padding(
          padding: const EdgeInsets.only(bottom: StudentSpace.itemGap),
          child: StudentSectionCard(
            padding: const EdgeInsets.symmetric(
              horizontal: StudentSpace.medium,
              vertical: StudentSpace.tight,
            ),
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(item['request_number']),
              subtitle: Text(
                '${item['service_name'] ?? ''}\nDue ${item['due_at']}',
              ),
              isThreeLine: true,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  StudentStatusBadge(status: item['status']),
                  const SizedBox(width: StudentSpace.tight),
                  const Icon(Icons.chevron_right_rounded),
                ],
              ),
              onTap: () => openRequest(item['id']),
            ),
          ),
        ),
    ],
  );

  Widget dashboard() {
    final counts = data['counts'] as Json;
    if (!staff) {
      final cards = <Widget>[
        for (final state in [
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
          StudentStatCard(
            label: label(state),
            value: '${counts[state] ?? 0}',
            icon: switch (state) {
              'completed' => Icons.check_circle_outline,
              'rejected' || 'cancelled' => Icons.cancel_outlined,
              'needs_correction' => Icons.edit_note_rounded,
              'processing' ||
              'ready_for_release' ||
              'released' => Icons.autorenew_rounded,
              _ => Icons.pending_actions_rounded,
            },
            color: switch (state) {
              'completed' => StudentColors.green,
              'rejected' || 'cancelled' => StudentColors.red,
              'needs_correction' => StudentColors.amber,
              _ => StudentColors.primary,
            },
            tint: switch (state) {
              'completed' => StudentColors.greenTint,
              'rejected' || 'cancelled' => StudentColors.redTint,
              'needs_correction' => StudentColors.amberTint,
              _ => StudentColors.blueTint,
            },
          ),
        StudentStatCard(
          label: 'Unread notifications',
          value: '${data['unread_notifications']}',
          icon: Icons.notifications_none_rounded,
          color: StudentColors.purple,
          tint: StudentColors.purpleTint,
        ),
      ];
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const StudentPageHeader(
            title: 'Your request overview',
            subtitle: 'Track your document requests and their latest status.',
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth >= 1000
                  ? 4
                  : constraints.maxWidth >= 650
                  ? 2
                  : 1;
              const gap = StudentSpace.itemGap;
              final width =
                  (constraints.maxWidth - (columns - 1) * gap) / columns;
              return Wrap(
                spacing: gap,
                runSpacing: gap,
                children: [
                  for (final card in cards) SizedBox(width: width, child: card),
                ],
              );
            },
          ),
          const SizedBox(height: StudentSpace.sectionGap),
          StudentSectionCard(
            title: 'Recent requests',
            icon: Icons.history_rounded,
            action: TextButton(
              onPressed: () => navigate('Requests'),
              child: const Text('View all'),
            ),
            child: requestCards(data['recent_requests']),
          ),
        ],
      );
    }
    final statCards = <Widget>[
      for (final state in [
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
        StudentStatCard(
          label: label(state),
          value: '${counts[state] ?? 0}',
          icon: Icons.pending_actions_rounded,
          color: state == 'completed'
              ? StudentColors.green
              : ['rejected', 'cancelled'].contains(state)
              ? StudentColors.red
              : state == 'needs_correction'
              ? StudentColors.amber
              : StudentColors.primary,
          tint: state == 'completed'
              ? StudentColors.greenTint
              : ['rejected', 'cancelled'].contains(state)
              ? StudentColors.redTint
              : state == 'needs_correction'
              ? StudentColors.amberTint
              : StudentColors.blueTint,
        ),
      StudentStatCard(
        label: 'Unread notifications',
        value: '${data['unread_notifications']}',
        icon: Icons.notifications_none_rounded,
      ),
      StudentStatCard(
        label: 'Permanent automation failures',
        value: '${data['failed_automation_jobs']}',
        icon: Icons.warning_amber_rounded,
        color: StudentColors.red,
        tint: StudentColors.redTint,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const StudentPageHeader(
          title: 'Registrar overview',
          subtitle: 'Request counts and recent activity.',
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 1100
                ? 4
                : constraints.maxWidth >= 640
                ? 2
                : 1;
            final width =
                (constraints.maxWidth - (columns - 1) * StudentSpace.itemGap) /
                columns;
            return Wrap(
              spacing: StudentSpace.itemGap,
              runSpacing: StudentSpace.itemGap,
              children: [
                for (final card in statCards)
                  SizedBox(width: width, child: card),
              ],
            );
          },
        ),
        const SizedBox(height: StudentSpace.sectionGap),
        StudentSectionCard(
          title: 'Recent requests',
          icon: Icons.history_rounded,
          action: TextButton(
            onPressed: () => navigate('Requests'),
            child: const Text('View queue'),
          ),
          child: requestCards(data['recent_requests']),
        ),
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
          width: StudentDialogWidth.of(ctx),
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
                      ? 'Payment evidence: ${v['payment']['currency']} ${v['payment']['amount']}'
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
          OutlinedButton(
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

  Widget services() {
    if (!staff) {
      final items = data['items'] as List;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const StudentPageHeader(
            title: 'Document services',
            subtitle: 'Choose a service to review its requirements and submit a request.',
          ),
          if (items.isEmpty)
            const StudentSectionCard(
              child: StudentEmptyState(
                title: 'No services available',
                message: 'Published document services will appear here.',
              ),
            ),
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: StudentSpace.itemGap),
              child: StudentSectionCard(
                child: Row(
                  children: [
                    Container(
                      width: StudentSize.serviceIcon,
                      height: StudentSize.serviceIcon,
                      decoration: BoxDecoration(
                        color: StudentColors.blueTint,
                        borderRadius: BorderRadius.circular(
                          StudentRadius.control,
                        ),
                      ),
                      child: const Icon(
                        Icons.description_outlined,
                        color: StudentColors.primary,
                      ),
                    ),
                    const SizedBox(width: StudentSpace.compact),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item['name'],
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: StudentSpace.micro + 1),
                          Text(
                            item['description'] ?? '',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: StudentSpace.tight + 1),
                          Wrap(
                            spacing: 8,
                            runSpacing: 6,
                            children: [
                              StudentStatusBadge(
                                status: item['payment_required']
                                    ? 'payment_evidence'
                                    : 'no_payment',
                              ),
                              Text(
                                '${item['processing_days']} processing days',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: StudentSpace.itemGap),
                    IconButton(
                      tooltip: 'View ${item['name']} requirements',
                      onPressed: () => serviceDetails(item['id']),
                      icon: const Icon(Icons.arrow_forward_rounded),
                      color: StudentColors.primary,
                    ),
                  ],
                ),
              ),
            ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const StudentPageHeader(
          title: 'Published document services',
          subtitle: 'Read-only catalog of active service versions.',
        ),
        StudentSectionCard(
          title: 'Service catalog',
          icon: Icons.folder_open_outlined,
          child: data['items'].isEmpty
              ? const StudentEmptyState(
                  title: 'No active services',
                  message: 'No published document services are available.',
                )
              : Column(
                  children: [
                    for (final item in data['items'])
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.description_outlined),
                        title: Text(item['name']),
                        subtitle: Text(
                          '${item['description']}\n${item['processing_days']} days ? ${item['payment_required'] ? 'Payment evidence' : 'No payment'}',
                        ),
                        isThreeLine: true,
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => serviceDetails(item['id']),
                      ),
                  ],
                ),
        ),
      ],
    );
  }

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
          Text('Payment reference: ${revision['payment']['reference']}'),
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
        if (!staff) ...[
          Text(
            'Current revision ${req['current_revision_number']}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Pinned service version ${version['version_number']} • due ${req['due_at']}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ] else ...[
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
        ],
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
              StudentActionButton(
                loading: busy,
                label: 'Begin review',
                onPressed: () => workflow('begin-review'),
              ),
            if (staff && state == 'under_review') ...[
              if (version['payment']['required'])
                for (final outcome in [
                  'verified',
                  'needs_correction',
                  'rejected',
                ])
                  StudentActionButton(
                    loading: busy,
                    kind: outcome == 'rejected'
                        ? StudentActionKind.destructive
                        : outcome == 'needs_correction'
                        ? StudentActionKind.secondary
                        : StudentActionKind.primary,
                    label: 'Payment: ${label(outcome)}',
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
                  ),
              StudentActionButton(
                loading: busy,
                label: 'Approve requirements',
                onPressed: () => workflow(
                  'approve',
                  extras: {'confirm_requirements_valid': true},
                ),
              ),
              StudentActionButton(
                kind: StudentActionKind.secondary,
                label: 'Request correction',
                onPressed: correctionDialog,
              ),
              StudentActionButton(
                kind: StudentActionKind.destructive,
                label: 'Reject request',
                onPressed: () async {
                  final reason = await prompt('Reject request');
                  if (reason != null) {
                    await workflow('reject', extras: {'reason': reason});
                  }
                },
              ),
            ],
            if (staff && state == 'processing')
              StudentActionButton(
                loading: busy,
                label: 'Mark ready for release',
                onPressed: () => workflow(
                  'ready-for-release',
                  extras: {'confirm_prepared': true},
                ),
              ),
            if (staff && state == 'ready_for_release')
              StudentActionButton(
                loading: busy,
                label: 'Confirm actual handover',
                onPressed: () =>
                    workflow('release', extras: {'confirm_handover': true}),
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
                        width: StudentDialogWidth.of(ctx),
                        child: SingleChildScrollView(
                          child: revisionContent(old, version),
                        ),
                      ),
                      actions: [
                        OutlinedButton(
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
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      StudentPageHeader(
        title: 'Staff notifications',
        subtitle: 'Request updates and operational alerts.',
        trailing: StudentActionButton(
          label: 'Mark all read',
          kind: StudentActionKind.secondary,
          loading: busy,
          onPressed: data['items'].isEmpty
              ? null
              : () => run(() async {
                  await api.call('POST', '/notifications/read-all');
                  await load();
                }),
          icon: Icons.done_all_rounded,
        ),
      ),
      StudentSectionCard(
        title: 'Recent updates',
        icon: Icons.notifications_none_rounded,
        child: data['items'].isEmpty
            ? const StudentEmptyState(
                title: 'No notifications',
                message:
                    'The dedicated worker delivers queued request updates.',
              )
            : Column(
                children: [
                  for (final n in data['items'])
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: CircleAvatar(
                        backgroundColor: n['read_at'] == null
                            ? StudentColors.blueTint
                            : StudentColors.background,
                        child: Icon(
                          n['read_at'] == null
                              ? Icons.mark_email_unread_outlined
                              : Icons.mark_email_read_outlined,
                          color: n['read_at'] == null
                              ? StudentColors.primary
                              : StudentColors.muted,
                        ),
                      ),
                      title: Text(n['title']),
                      subtitle: Text('${n['message']}\n${n['created_at']}'),
                      isThreeLine: true,
                      onTap: () => run(() async {
                        await api.call(
                          'PATCH',
                          '/notifications/${n['id']}/read',
                        );
                        if (n['request_id'] != null) {
                          screen = 'Detail';
                          await fetchDetail(n['request_id']);
                        } else {
                          await load();
                        }
                      }),
                    ),
                ],
              ),
      ),
    ],
  );

  Widget studentNotifications() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      StudentPageHeader(
        title: 'Notifications',
        subtitle: 'Updates about your requests and document services.',
        trailing: TextButton.icon(
          onPressed: data['items'].isEmpty
              ? null
              : () => run(() async {
                  await api.call('POST', '/notifications/read-all');
                  await load();
                }),
          icon: const Icon(Icons.done_all_rounded),
          label: const Text('Mark all read'),
        ),
      ),
      StudentSectionCard(
        title: 'Recent updates',
        icon: Icons.notifications_none_rounded,
        child: data['items'].isEmpty
            ? const StudentEmptyState(
                title: 'You are all caught up',
                message: 'New request updates will appear here.',
                icon: Icons.notifications_none_rounded,
              )
            : Column(
                children: [
                  for (final n in data['items'])
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: CircleAvatar(
                        backgroundColor: n['read_at'] == null
                            ? StudentColors.blueTint
                            : StudentColors.background,
                        child: Icon(
                          n['read_at'] == null
                              ? Icons.mark_email_unread_outlined
                              : Icons.mark_email_read_outlined,
                          color: n['read_at'] == null
                              ? StudentColors.primary
                              : StudentColors.muted,
                        ),
                      ),
                      title: Text(
                        n['title'],
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      subtitle: Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text('${n['message']}\n${n['created_at']}'),
                      ),
                      isThreeLine: true,
                      onTap: () => run(() async {
                        await api.call(
                          'PATCH',
                          '/notifications/${n['id']}/read',
                        );
                        if (n['request_id'] != null) {
                          screen = 'Detail';
                          await fetchDetail(n['request_id']);
                        } else if (n['service_id'] != null) {
                          screen = 'Services';
                          await load();
                        } else {
                          await load();
                        }
                      }),
                    ),
                ],
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
          width: StudentDialogWidth.of(ctx),
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
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          if (job['status'] == 'failed_permanently') ...[
            if (job['job_type'] == 'notification' && job['max_attempts'] < 9)
              OutlinedButton(
                onPressed: () => Navigator.pop(ctx, 'retry'),
                child: const Text('Retry safely'),
              ),
            StudentActionButton(
              kind: StudentActionKind.destructive,
              label: 'Record manual handling',
              onPressed: () => Navigator.pop(ctx, 'resolve'),
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
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const StudentPageHeader(
        title: 'Automation monitoring',
        subtitle:
            'Durable schedule runs, queued work, alerts and recovery actions.',
      ),
      StudentSectionCard(
        title: 'Daily pending summary',
        icon: Icons.summarize_outlined,
        action: StudentActionButton(
          label: 'Regenerate current local date',
          kind: StudentActionKind.secondary,
          loading: busy,
          icon: Icons.refresh_rounded,
          onPressed: busy
              ? null
              : () => run(() async {
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
        ),
        child: data['summary'] == null
            ? const StudentEmptyState(
                title: 'Summary not generated',
                message: 'No stored snapshot is available for today.',
                icon: Icons.summarize_outlined,
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Asia/Manila date ${data['summary']['summary_date']} ? generated ${data['summary']['generated_at']}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  Wrap(
                    spacing: StudentSpace.tight,
                    runSpacing: StudentSpace.tight,
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
                        Chip(
                          label: Text('${label(key)}: ${data['summary'][key]}'),
                        ),
                    ],
                  ),
                ],
              ),
      ),
      const SizedBox(height: StudentSpace.sectionGap),
      StudentSectionCard(
        title: 'Open alerts',
        icon: Icons.notifications_active_outlined,
        child: data['alerts'].isEmpty
            ? const StudentEmptyState(
                title: 'No open alerts',
                message: 'Aging and stalled requests will appear here.',
              )
            : Column(
                children: [
                  for (final alert in data['alerts'])
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: StudentStatusBadge(status: alert['alert_type']),
                      title: Text('Request ${alert['request_id']}'),
                      subtitle: Text('Triggered ${alert['triggered_at']}'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => openRequest(alert['request_id']),
                    ),
                ],
              ),
      ),
      const SizedBox(height: StudentSpace.sectionGap),
      StudentSectionCard(
        title: 'Durable jobs',
        icon: Icons.work_history_outlined,
        child: Column(
          children: [
            StudentFilterBar(
              children: [
                DropdownButtonFormField<String>(
                  initialValue: jobsFilter,
                  decoration: const InputDecoration(labelText: 'Job status'),
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
                        child: Text(
                          status.isEmpty ? 'All job states' : label(status),
                        ),
                      ),
                  ],
                  onChanged: busy
                      ? null
                      : (value) {
                          jobsFilter = value!;
                          run(load);
                        },
                ),
              ],
            ),
            const SizedBox(height: StudentSpace.itemGap),
            if (data['jobs'].isEmpty)
              const StudentEmptyState(
                title: 'No matching jobs',
                message: 'Durable automation jobs will be listed here.',
                icon: Icons.work_history_outlined,
              )
            else
              for (final job in data['jobs'])
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('Job ${job['id']} ? ${job['job_type']}'),
                  subtitle: Text(
                    'Attempts ${job['attempt_count']}/${job['max_attempts']} ? ${job['last_error_code'] ?? 'No failure recorded'}',
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      StudentStatusBadge(status: job['status']),
                      const SizedBox(width: StudentSpace.tight),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                  onTap: () => jobDialog(job['id']),
                ),
          ],
        ),
      ),
      const SizedBox(height: StudentSpace.sectionGap),
      StudentSectionCard(
        title: 'Schedule runs',
        icon: Icons.schedule_rounded,
        child: data['runs'].isEmpty
            ? const StudentEmptyState(
                title: 'No schedule runs yet',
                message: 'Completed worker runs will appear here.',
                icon: Icons.schedule_rounded,
              )
            : Column(
                children: [
                  for (final item in data['runs'])
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(item['job_name']),
                      subtitle: Text(
                        '${item['started_at']} ? scanned ${item['records_scanned']} ? tasks ${item['tasks_created']} ? ${item['error_code'] ?? ''}',
                      ),
                      trailing: StudentStatusBadge(status: item['status']),
                    ),
                ],
              ),
      ),
      const SizedBox(height: StudentSpace.sectionGap),
      StudentSectionCard(
        title: 'Sanitized activity log',
        icon: Icons.receipt_long_outlined,
        child: data['audits'].isEmpty
            ? const StudentEmptyState(
                title: 'No activity recorded',
                message:
                    'Sanitized staff automation activity will appear here.',
                icon: Icons.receipt_long_outlined,
              )
            : Column(
                children: [
                  for (final entry in data['audits'])
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${entry['action']} ? ${entry['result']}'),
                      subtitle: Text(
                        '${entry['created_at']} ? ${entry['target_type']} ${entry['target_id'] ?? ''}',
                      ),
                    ),
                ],
              ),
      ),
    ],
  );

  Widget content() {
    if (screen == 'Form') {
      if (!staff) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            StudentPageHeader(
              title: service!['version']['name'],
              subtitle: formRequest == null
                  ? 'Complete the service requirements below.'
                  : 'Review the requested changes and resubmit your correction.',
            ),
            StudentSectionCard(
              icon: formRequest == null
                  ? Icons.add_task_rounded
                  : Icons.edit_note_rounded,
              child: RequirementsForm(
                key: ValueKey('${service!['id']}-${formRequest?['id']}'),
                api: api,
                service: service!,
                request: formRequest,
                onSubmitted: (result) {
                  success =
                      'Submission confirmed: ${result['request_number']} • revision ${result['revision_number']}';
                  openRequest(result['id']);
                },
              ),
            ),
          ],
        );
      }
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
      return staff
          ? const Text('Use Retry to load this view.')
          : const SizedBox.shrink();
    }
    switch (screen) {
      case 'Services':
        return staff
            ? ServiceManagement(
                api: api,
                actor: actor!,
                listing: data,
                onRefresh: () => run(load),
              )
            : services();
      case 'Detail':
        if (staff) {
          return selected == null
              ? const StudentEmptyState(
                  title: 'Request unavailable',
                  message: 'Return to the request queue and select a request.',
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    StudentPageHeader(
                      title: selected!['request_number'],
                      subtitle:
                          '${selected!['service']['version']['name']} • registrar review',
                      trailing: StudentStatusBadge(status: selected!['status']),
                    ),
                    StudentSectionCard(
                      title: 'Request review',
                      icon: Icons.fact_check_outlined,
                      child: detail(),
                    ),
                  ],
                );
        }
        if (selected == null) {
          return const StudentEmptyState(
            title: 'Request unavailable',
            message: 'Return to My requests and select a request to view it.',
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            StudentPageHeader(
              title: selected!['request_number'],
              subtitle:
                  '${selected!['service']['version']['name']} • request details',
              trailing: StudentStatusBadge(status: selected!['status']),
            ),
            StudentSectionCard(
              title: 'Request details',
              icon: Icons.description_outlined,
              child: detail(),
            ),
          ],
        );
      case 'Requests':
        if (!staff) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const StudentPageHeader(
                title: 'My requests',
                subtitle: 'Find a request by its tracking number or filter by status.',
              ),
              StudentSectionCard(
                title: 'Request history',
                icon: Icons.receipt_long_outlined,
                child: Column(
                  children: [
                    TextField(
                      controller: search,
                      decoration: InputDecoration(
                        labelText: 'Tracking number',
                        suffixIcon: IconButton(
                          tooltip: 'Search requests',
                          onPressed: () => run(load),
                          icon: const Icon(Icons.search_rounded),
                        ),
                      ),
                      onSubmitted: (_) => run(load),
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    DropdownButtonFormField<String>(
                      initialValue: statusFilter,
                      decoration: const InputDecoration(labelText: 'Status'),
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
                            child: Text(
                              state.isEmpty ? 'All statuses' : label(state),
                            ),
                          ),
                      ],
                      onChanged: (value) {
                        statusFilter = value!;
                        run(load);
                      },
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    requestCards(data['items']),
                  ],
                ),
              ),
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const StudentPageHeader(
              title: 'Registrar request queue',
              subtitle: 'Search and filter requests awaiting registrar action.',
            ),
            StudentSectionCard(
              title: 'Request queue',
              icon: Icons.inbox_outlined,
              child: Column(
                children: [
                  StudentFilterBar(
                    children: [
                      TextField(
                        controller: search,
                        decoration: InputDecoration(
                          labelText: 'Tracking number',
                          prefixIcon: const Icon(Icons.search_rounded),
                          suffixIcon: IconButton(
                            tooltip: 'Search requests',
                            onPressed: busy ? null : () => run(load),
                            icon: const Icon(Icons.search_rounded),
                          ),
                        ),
                        onSubmitted: (_) => run(load),
                      ),
                      DropdownButtonFormField<String>(
                        initialValue: statusFilter,
                        decoration: const InputDecoration(labelText: 'Status'),
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
                              child: Text(
                                state.isEmpty ? 'All statuses' : label(state),
                              ),
                            ),
                        ],
                        onChanged: busy
                            ? null
                            : (value) {
                                statusFilter = value!;
                                run(load);
                              },
                      ),
                    ],
                  ),
                  const SizedBox(height: StudentSpace.sectionGap),
                  requestCards(data['items']),
                ],
              ),
            ),
          ],
        );
      case 'Notifications':
        return staff ? notifications() : studentNotifications();
      case 'Automation':
        return automation();
      default:
        return dashboard();
    }
  }

  Future<void> searchStudentRequests(String query) async {
    search.text = query;
    if (screen == 'Requests') {
      await run(load);
    } else {
      await navigate('Requests');
    }
  }

  Future<void> signOut() async {
    if (busy ||
        !await confirm('Sign out?', 'Leave this development session?')) {
      return;
    }
    await run(() async {
      await api.call('POST', '/auth/logout');
      actor = null;
      data = null;
      selected = null;
      screen = 'Dashboard';
      api.csrf = null;
    });
  }

  Widget studentWorkspace() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (success != null)
        Container(
          margin: const EdgeInsets.only(bottom: StudentSpace.sectionGap),
          padding: const EdgeInsets.all(StudentSpace.compact),
          decoration: BoxDecoration(
            color: StudentColors.greenTint,
            borderRadius: BorderRadius.circular(StudentRadius.control),
          ),
          child: Semantics(
            liveRegion: true,
            child: Text(
              success!,
              style: const TextStyle(
                color: StudentColors.green,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      if (error != null && !busy)
        Padding(
          padding: const EdgeInsets.only(bottom: StudentSpace.sectionGap),
          child: StudentErrorState(message: error!, onRetry: () => run(load)),
        ),
      if (busy && data == null && screen != 'Form')
        const StudentLoadingState()
      else
        content(),
    ],
  );

  Widget staffWorkspace() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (success != null)
        StudentSectionCard(
          padding: const EdgeInsets.all(StudentSpace.medium),
          child: Semantics(
            liveRegion: true,
            child: Text(
              success!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: StudentColors.green,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      if (error != null && !busy)
        Padding(
          padding: const EdgeInsets.only(bottom: StudentSpace.sectionGap),
          child: StudentErrorState(message: error!, onRetry: () => run(load)),
        ),
      if (busy && data == null && screen != 'Detail')
        const StudentLoadingState()
      else
        content(),
    ],
  );

  @override
  Widget build(BuildContext context) {
    if (actor?['must_change_password'] == true) {
      return AccountPage(
        api: api,
        actor: actor!,
        forcePasswordChange: true,
        onSignOut: signOut,
        onSignedOut: () => setState(() {
          actor = null;
          data = null;
          screen = 'Dashboard';
          success = 'Password changed. Sign in again.';
        }),
      );
    }
    if (actor == null) {
      return Theme(
        data: StudentTheme.data,
        child: Scaffold(
          backgroundColor: StudentColors.background,
          body: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(StudentSpace.page - 4),
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: StudentSize.loginCardWidth,
                ),
                child: StudentSectionCard(
                  padding: const EdgeInsets.all(StudentSpace.loginCard),
                  child: Form(
                    key: loginForm,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Center(
                          child: Container(
                            width: StudentSize.loginLogo,
                            height: StudentSize.loginLogo,
                            decoration: BoxDecoration(
                              color: StudentColors.primary,
                              borderRadius: BorderRadius.circular(
                                StudentRadius.loginLogo,
                              ),
                            ),
                            child: const Icon(
                              Icons.school_rounded,
                              size: StudentSize.loginLogo / 2,
                              color: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(height: StudentSpace.sectionGap),
                        Text(
                          'Student Document Request Tracker',
                          textAlign: TextAlign.center,
                          style: StudentTheme.data.textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 7),
                        const Text(
                          'Development environment • test accounts',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: StudentColors.muted),
                        ),
                        const SizedBox(height: StudentSpace.page),
                        TextFormField(
                          controller: login,
                          decoration: const InputDecoration(
                            labelText: 'Email or student number',
                            prefixIcon: Icon(Icons.person_outline_rounded),
                          ),
                          autofillHints: const [AutofillHints.username],
                          validator: (v) => (v ?? '').trim().isEmpty
                              ? 'Enter your login.'
                              : null,
                        ),
                        const SizedBox(height: StudentSpace.compact + 1),
                        TextFormField(
                          controller: password,
                          obscureText: !showLoginPassword,
                          decoration: InputDecoration(
                            labelText: 'Password',
                            prefixIcon: const Icon(Icons.lock_outline_rounded),
                            suffixIcon: IconButton(
                              tooltip: showLoginPassword
                                  ? 'Hide password'
                                  : 'Show password',
                              onPressed: () => setState(
                                () => showLoginPassword = !showLoginPassword,
                              ),
                              icon: Icon(
                                showLoginPassword
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                              ),
                            ),
                          ),
                          autofillHints: const [AutofillHints.password],
                          onFieldSubmitted: (_) {
                            if (!busy) signIn();
                          },
                          validator: (v) =>
                              (v ?? '').isEmpty ? 'Enter your password.' : null,
                        ),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Remember me'),
                          value: rememberMe,
                          onChanged: busy
                              ? null
                              : (value) =>
                                    setState(() => rememberMe = value ?? false),
                        ),
                        if (error != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Semantics(
                              liveRegion: true,
                              child: Text(
                                error!,
                                style: const TextStyle(
                                  color: StudentColors.red,
                                ),
                              ),
                            ),
                          ),
                        if (success != null)
                          Padding(
                            padding: const EdgeInsets.only(
                              top: StudentSpace.itemGap,
                            ),
                            child: Text(
                              success!,
                              style: const TextStyle(
                                color: StudentColors.green,
                              ),
                            ),
                          ),
                        const SizedBox(height: StudentSpace.sectionGap),
                        if (busy) const LinearProgressIndicator(),
                        FilledButton(
                          onPressed: busy ? null : signIn,
                          child: const Text('Sign in'),
                        ),
                        TextButton(
                          onPressed: busy ? null : registerAccount,
                          child: const Text('Create student account'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }
    if (!staff) {
      final active = screen == 'Detail' || screen == 'Form'
          ? 'Requests'
          : screen;
      final unread = data is Json
          ? (data['unread_notifications'] as int? ?? 0)
          : 0;
      return StudentAppShell(
        selected: active,
        userName: actor!['full_name'],
        unreadCount: unread,
        busy: busy,
        searchController: search,
        onSearch: searchStudentRequests,
        onNavigate: (destination) {
          if (!busy) navigate(destination);
        },
        onRefresh: () {
          if (!busy) run(load);
        },
        onSignOut: signOut,
        onProfile: openAccount,
        child: studentWorkspace(),
      );
    }
    final selected = screen == 'Detail' || screen == 'Form'
        ? 'Requests'
        : screen;
    return StudentAppShell(
      selected: selected,
      userName: actor!['full_name'],
      unreadCount: data is Json
          ? (data['unread_notifications'] as int? ?? 0)
          : 0,
      busy: busy,
      searchController: search,
      onSearch: searchStudentRequests,
      onNavigate: (destination) {
        if (!busy) navigate(destination);
      },
      onRefresh: () {
        if (!busy) run(load);
      },
      onSignOut: signOut,
      onProfile: openAccount,
      brandName: 'Registrar Desk',
      menuLabel: 'STAFF MENU',
      searchHint: 'Search by tracking number...',
      navigationItems: const [
        ('Dashboard', Icons.grid_view_rounded),
        ('Services', Icons.folder_open_outlined),
        ('Requests', Icons.description_outlined),
        ('Notifications', Icons.notifications_none_rounded),
        ('Automation', Icons.auto_awesome_outlined),
      ],
      child: staffWorkspace(),
    );
  }
}
