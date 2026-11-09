import 'package:flutter/material.dart';

import 'api.dart';
import 'design_system.dart';
import 'requirements_form.dart';

class ServiceManagement extends StatefulWidget {
  final Api api;
  final Json actor;
  final Json listing;
  final Future<void> Function() onRefresh;
  const ServiceManagement({
    super.key,
    required this.api,
    required this.actor,
    required this.listing,
    required this.onRefresh,
  });
  @override
  State<ServiceManagement> createState() => _ServiceManagementState();
}

class _ServiceManagementState extends State<ServiceManagement> {
  bool busy = false;
  String? error;
  final search = TextEditingController();
  String filter = 'all';
  Json? filtered;
  bool get manager => widget.actor['can_manage_services'] == true;

  String versionSummary(Json version) {
    final count = (version['requirements'] as List).length;
    final days = version['processing_days'];
    final payment = version['payment']['required']
        ? 'Payment evidence'
        : 'No payment';
    return '$count requirements • $days days • $payment';
  }

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant ServiceManagement oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.listing, widget.listing)) {
      filtered = null;
      filter = 'all';
      search.clear();
    }
  }

  Future<void> findServices() async {
    final query = Uri.encodeQueryComponent(search.text.trim());
    final result = await widget.api.call(
      'GET',
      '/staff/services?page_size=100&availability=$filter&q=$query',
    ) as Json;
    if (mounted) setState(() => filtered = result);
  }

  Future<void> run(Future<void> Function() action) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> editor([Json? item]) => run(() async {
    Json? draft;
    if (item != null) {
      final id = item['id'];
      draft = await widget.api.call(
        item['has_draft'] ? 'GET' : 'POST',
        '/staff/services/$id/draft',
      ) as Json;
    }
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => ServiceDraftEditor(api: widget.api, draft: draft),
      ),
    );
    await widget.onRefresh();
  });

  Future<void> availability(Json item) => run(() async {
    final active = item['is_active'] != true;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          active ? 'Make service available?' : 'Make service unavailable?',
        ),
        content: Text(
          active
              ? 'Students can submit new requests using the current published version.'
              : 'New requests will be unavailable. Existing requests keep their original version.',
        ),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Go back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await widget.api.call(
      'PATCH',
      '/staff/services/${item['id']}/availability',
      {
        'is_active': active,
        'expected_current_version_id': item['current_version_id'],
      },
    );
    await widget.onRefresh();
  });

  Future<void> history(Json item) => run(() async {
    final result =
        await widget.api.call('GET', '/staff/services/${item['id']}') as Json;
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(item['service_code']),
        content: SizedBox(
          width: StudentDialogWidth.of(ctx),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if ((result['published_versions'] as List).isEmpty)
                  const Text('No published versions yet.'),
                for (final version in result['published_versions'])
                  Padding(
                    padding: const EdgeInsets.only(bottom: StudentSpace.medium),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${version['name']} • version ${version['version_number']}',
                          style: Theme.of(ctx).textTheme.titleMedium,
                        ),
                        Text(version['description'] ?? ''),
                        for (final field in version['requirements'])
                          Text(
                            '• ${field['label']} ${field['required'] ? '(required)' : '(optional)'}',
                          ),
                      ],
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
        ],
      ),
    );
  });

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      StudentPageHeader(
        title: 'Document services',
        subtitle: 'Published services, availability and version history.',
        trailing: manager
            ? FilledButton.icon(
                onPressed: busy ? null : () => editor(),
                icon: const Icon(Icons.add),
                label: const Text('New service'),
              )
            : null,
      ),
      if (error != null)
        StudentErrorState(message: error!, onRetry: () => widget.onRefresh()),
      if (busy) const LinearProgressIndicator(),
      StudentSectionCard(
        title: 'Service catalog',
        icon: Icons.folder_open_outlined,
        child: Column(
          children: [
            StudentFilterBar(
              children: [
                TextField(
                  controller: search,
                  decoration: InputDecoration(
                    labelText: 'Search document services',
                    suffixIcon: IconButton(
                      tooltip: 'Search services',
                      onPressed: busy ? null : () => run(findServices),
                      icon: const Icon(Icons.search),
                    ),
                  ),
                  onSubmitted: (_) => run(findServices),
                ),
                DropdownButtonFormField<String>(
                  initialValue: filter,
                  decoration: const InputDecoration(labelText: 'Availability'),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('All services')),
                    DropdownMenuItem(value: 'active', child: Text('Available')),
                    DropdownMenuItem(
                      value: 'inactive',
                      child: Text('Unavailable'),
                    ),
                  ],
                  onChanged: busy
                      ? null
                      : (value) {
                          setState(() => filter = value ?? 'all');
                          run(findServices);
                        },
                ),
              ],
            ),
            const SizedBox(height: StudentSpace.itemGap),
            if (((filtered ?? widget.listing)['items'] as List).isEmpty)
              const StudentEmptyState(
                title: 'No matching services',
                message: 'Try another search or availability filter.',
              )
            else
              for (final item in (filtered ?? widget.listing)['items'])
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(StudentSpace.medium),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item['current_version']?['name'] ??
                              (item['draft_name']?.isNotEmpty == true
                                  ? item['draft_name']
                                  : item['service_code']),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (item['current_version'] != null) ...[
                          Text(item['current_version']['description'] ?? ''),
                          Text(versionSummary(item['current_version'])),
                        ],
                        Text(
                          item['service_code'] +
                              (item['is_active']
                                  ? ' • Available'
                                  : ' • Unavailable') +
                              (item['has_draft'] ? ' • Draft in progress' : ''),
                        ),
                        const SizedBox(height: StudentSpace.tight),
                        Wrap(
                          spacing: StudentSpace.tight,
                          runSpacing: StudentSpace.tight,
                          children: [
                            OutlinedButton(
                              onPressed: busy ? null : () => history(item),
                              child: const Text('View versions'),
                            ),
                            if (manager)
                              OutlinedButton(
                                onPressed: busy ? null : () => editor(item),
                                child: Text(
                                  item['has_draft']
                                      ? 'Edit draft'
                                      : 'Create draft',
                                ),
                              ),
                            if (manager && item['current_version_id'] != null)
                              OutlinedButton(
                                onPressed: busy
                                    ? null
                                    : () => availability(item),
                                child: Text(
                                  item['is_active']
                                      ? 'Make unavailable'
                                      : 'Make available',
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        ),
      ),
    ],
  );
}

class ServiceDraftEditor extends StatefulWidget {
  final Api api;
  final Json? draft;
  const ServiceDraftEditor({super.key, required this.api, this.draft});
  @override
  State<ServiceDraftEditor> createState() => _ServiceDraftEditorState();
}

class _ServiceDraftEditorState extends State<ServiceDraftEditor> {
  final formKey = GlobalKey<FormState>();
  late Json config;
  Json? draft;
  String serviceCode = '';
  bool busy = false;
  bool dirty = false;
  String? error;
  String? message;
  List<Json> get fields => (config['requirements'] as List).cast<Json>();
  Json get payment => config['payment'] as Json;

  @override
  void initState() {
    super.initState();
    draft = widget.draft;
    config = draft == null
        ? {
            'name': '',
            'description': '',
            'category': '',
            'eligibility_instructions': '',
            'processing_days': 3,
            'payment': {
              'required': false,
              'amount': null,
              'currency': 'PHP',
              'instructions': null,
              'reference_required': false,
              'receipt_required': false,
            },
            'requirements': <Json>[],
          }
        : toInput(draft!['version']);
  }

  Json toInput(Json version) => {
    for (final key in [
      'name',
      'description',
      'category',
      'eligibility_instructions',
      'processing_days',
    ])
      key: version[key],
    'payment': Map<String, dynamic>.from(version['payment']),
    'requirements': [
      for (final field in version['requirements'])
        {
          for (final key in [
            'id',
            'field_key',
            'label',
            'help_text',
            'field_type',
            'required',
            'min_length',
            'max_length',
            'allowed_mime_types',
            'max_file_size_bytes',
          ])
            key: field[key],
          'options': [
            for (final option in field['options'])
              Map<String, dynamic>.from(option),
          ],
        },
    ],
  };

  Future<void> save() async {
    if (!formKey.currentState!.validate()) return;
    final usedKeys = fields
        .map((field) => field['field_key'] as String)
        .where((key) => key.isNotEmpty)
        .toSet();
    for (final field in fields) {
      if ((field['field_key'] as String).isNotEmpty) continue;
      var base = (field['label'] as String)
          .toLowerCase()
          .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
          .replaceAll(RegExp(r'^_+|_+$'), '');
      if (base.isEmpty || !RegExp(r'^[a-z]').hasMatch(base)) {
        base = 'field_$base';
      }
      if (base.length > 70) base = base.substring(0, 70);
      var key = base;
      var suffix = 2;
      while (usedKeys.contains(key)) {
        key = [base, suffix].join('_');
        suffix++;
      }
      field['field_key'] = key;
      usedKeys.add(key);
    }
    setState(() {
      busy = true;
      error = null;
      message = null;
    });
    try {
      final result = draft == null
          ? await widget.api.call('POST', '/staff/services', {
              'service_code': serviceCode.trim().toUpperCase(),
              'configuration': config,
            })
          : await widget.api.call(
              'PUT',
              '/staff/services/${draft!['id']}/draft',
              {
                'expected_row_version': draft!['version']['row_version'],
                'configuration': config,
              },
            );
      if (!mounted) return;
      setState(() {
        draft = result;
        config = toInput(result['version']);
        dirty = false;
        message = 'Draft saved. Preview it before publishing.';
      });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> preview() async {
    if (draft == null) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          appBar: AppBar(title: const Text('Student form preview')),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(StudentSpace.page),
            child: StudentSectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(draft!['version']['description'] ?? ''),
                  const SizedBox(height: StudentSpace.itemGap),
                  RequirementsForm(
                    api: widget.api,
                    service: draft!,
                    preview: true,
                    onSubmitted: (_) {},
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> publish() async {
    if (draft == null) return;
    final activate = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Publish this version?'),
        content: const Text(
          'Published requirements cannot be edited. Students can use the new version after the service is available.',
        ),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Go back'),
          ),
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Publish only'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Publish and make available'),
          ),
        ],
      ),
    );
    if (activate == null) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.api.call('POST', '/staff/services/${draft!['id']}/publish', {
        'expected_row_version': draft!['version']['row_version'],
        'activate': activate,
      });
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Json newField() => {
    'field_key': '',
    'label': '',
    'help_text': null,
    'field_type': 'text',
    'required': true,
    'min_length': null,
    'max_length': 200,
    'allowed_mime_types': null,
    'max_file_size_bytes': null,
    'options': <Json>[],
  };
  void changeType(Json field, String type) {
    setState(() {
      dirty = true;
      field['field_type'] = type;
      field['min_length'] = null;
      field['max_length'] = type == 'text' ? 200 : null;
      field['allowed_mime_types'] = type == 'file'
          ? <String>['application/pdf', 'image/jpeg', 'image/png']
          : null;
      field['max_file_size_bytes'] = type == 'file' ? 5242880 : null;
      field['options'] = <Json>[];
    });
  }

  Widget requirement(Json field, int index) => Card(
    key: ObjectKey(field),
    child: Padding(
      padding: const EdgeInsets.all(StudentSpace.medium),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Requirement ${index + 1}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              IconButton(
                tooltip: 'Move up',
                onPressed: index == 0
                    ? null
                    : () => setState(() {
                        fields.removeAt(index);
                        fields.insert(index - 1, field);
                        dirty = true;
                      }),
                icon: const Icon(Icons.arrow_upward),
              ),
              IconButton(
                tooltip: 'Move down',
                onPressed: index == fields.length - 1
                    ? null
                    : () => setState(() {
                        fields.removeAt(index);
                        fields.insert(index + 1, field);
                        dirty = true;
                      }),
                icon: const Icon(Icons.arrow_downward),
              ),
              IconButton(
                tooltip: 'Remove requirement',
                onPressed: () => setState(() {
                  fields.removeAt(index);
                  dirty = true;
                }),
                icon: const Icon(Icons.delete_outline),
              ),
            ],
          ),
          TextFormField(
            initialValue: field['field_key'],
            decoration: const InputDecoration(
              labelText: 'Field key (optional)',
              helperText: 'Generated from the label if left blank.',
            ),
            onChanged: (v) => field['field_key'] = v.trim(),
            validator: (v) =>
                (v ?? '').isEmpty || RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(v!)
                ? null
                : 'Use lowercase letters, numbers and underscores.',
          ),
          const SizedBox(height: StudentSpace.itemGap),
          TextFormField(
            initialValue: field['label'],
            decoration: const InputDecoration(labelText: 'Requirement label'),
            onChanged: (v) => field['label'] = v.trim(),
            validator: (v) =>
                (v ?? '').trim().isEmpty ? 'Enter a label.' : null,
          ),
          const SizedBox(height: StudentSpace.itemGap),
          TextFormField(
            initialValue: field['help_text'] ?? '',
            decoration: const InputDecoration(
              labelText: 'Instructions (optional)',
            ),
            minLines: 2,
            maxLines: 3,
            onChanged: (v) =>
                field['help_text'] = v.trim().isEmpty ? null : v.trim(),
          ),
          const SizedBox(height: StudentSpace.itemGap),
          DropdownButtonFormField<String>(
            initialValue: field['field_type'],
            decoration: const InputDecoration(labelText: 'Answer type'),
            items: const [
              DropdownMenuItem(value: 'text', child: Text('Text')),
              DropdownMenuItem(value: 'select', child: Text('Select one')),
              DropdownMenuItem(value: 'date', child: Text('Date')),
              DropdownMenuItem(value: 'checkbox', child: Text('Checkbox')),
              DropdownMenuItem(value: 'file', child: Text('File upload')),
            ],
            onChanged: (v) {
              if (v != null) changeType(field, v);
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Required'),
            value: field['required'],
            onChanged: (v) => setState(() {
              field['required'] = v;
              dirty = true;
            }),
          ),
          if (field['field_type'] == 'text') ...[
            TextFormField(
              key: ValueKey('minimum-${identityHashCode(field)}'),
              initialValue: field['min_length']?.toString() ?? '',
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Minimum characters (optional)',
              ),
              onChanged: (v) => field['min_length'] = v.trim().isEmpty
                  ? null
                  : int.tryParse(v),
              validator: (v) {
                if ((v ?? '').trim().isEmpty) return null;
                final n = int.tryParse(v!);
                return n == null || n < 0 || n > 1000
                    ? 'Enter 0 to 1000.'
                    : null;
              },
            ),
            const SizedBox(height: StudentSpace.itemGap),
            TextFormField(
              key: ValueKey('max-${identityHashCode(field)}'),
              initialValue: (field['max_length'] ?? 1000).toString(),
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Maximum characters (1–1000)',
              ),
              onChanged: (v) => field['max_length'] = int.tryParse(v),
              validator: (v) {
                final n = int.tryParse(v ?? '');
                return n == null ||
                        n < 1 ||
                        n > 1000 ||
                        n < (field['min_length'] ?? 0)
                    ? 'Enter 1 to 1000, at least the minimum.'
                    : null;
              },
            ),
          ],
          if (field['field_type'] == 'select')
            TextFormField(
              key: ValueKey('options-${identityHashCode(field)}'),
              initialValue: (field['options'] as List)
                  .map((o) => o['label'])
                  .join('\n'),
              minLines: 2,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Choices, one per line',
              ),
              onChanged: (v) {
                final choices = v
                    .split('\n')
                    .map((s) => s.trim())
                    .where((s) => s.isNotEmpty)
                    .toList();
                field['options'] = [
                  for (var i = 0; i < choices.length; i++)
                    {'value': 'option_${i + 1}', 'label': choices[i]},
                ];
              },
              validator: (v) {
                final n = (v ?? '')
                    .split('\n')
                    .where((s) => s.trim().isNotEmpty)
                    .length;
                return n < 1 || n > 30 ? 'Enter 1 to 30 choices.' : null;
              },
            ),
          if (field['field_type'] == 'file') ...[
            const Text('Allowed file types (maximum 5 MiB each)'),
            Wrap(
              spacing: StudentSpace.tight,
              children: [
                for (final entry in const [
                  ('PDF', 'application/pdf'),
                  ('JPG', 'image/jpeg'),
                  ('PNG', 'image/png'),
                ])
                  FilterChip(
                    label: Text(entry.$1),
                    selected: (field['allowed_mime_types'] as List).contains(
                      entry.$2,
                    ),
                    onSelected: (selected) => setState(() {
                      dirty = true;
                      final types = field['allowed_mime_types'] as List;
                      if (selected) {
                        types.add(entry.$2);
                      } else {
                        types.remove(entry.$2);
                      }
                    }),
                  ),
              ],
            ),
            TextFormField(
              key: ValueKey('file-size-${identityHashCode(field)}'),
              initialValue: field['max_file_size_bytes'].toString(),
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Maximum file size in bytes (up to 5242880)',
              ),
              onChanged: (v) => field['max_file_size_bytes'] = int.tryParse(v),
              validator: (v) {
                final n = int.tryParse(v ?? '');
                return n == null || n < 1 || n > 5242880
                    ? 'Enter 1 to 5242880 bytes.'
                    : null;
              },
            ),
          ],
        ],
      ),
    ),
  );

  Future<void> leaveDraft() async {
    if (busy) return;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Leave this draft?'),
        content: const Text('Unsaved changes will be lost.'),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Keep editing'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Leave draft'),
          ),
        ],
      ),
    );
    if (leave == true && mounted) {
      setState(() => dirty = false);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) Navigator.of(context).pop();
      });
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !dirty && !busy,
    onPopInvokedWithResult: (didPop, _) {
      if (!didPop && dirty) leaveDraft();
    },
    child: Scaffold(
      appBar: AppBar(
        title: Text(
          draft == null ? 'New document service' : 'Edit service draft',
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(StudentSpace.page),
            child: StudentSectionCard(
              child: Form(
                key: formKey,
                onChanged: () {
                  if (!dirty) setState(() => dirty = true);
                },
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Draft service rules must be reviewed with the registrar before publication.',
                    ),
                    const SizedBox(height: StudentSpace.sectionGap),
                    if (draft == null) ...[
                      TextFormField(
                        key: const ValueKey('service-code'),
                        decoration: const InputDecoration(
                          labelText:
                              'Service code (letters, numbers, underscores)',
                        ),
                        onChanged: (v) => serviceCode = v,
                        validator: (v) =>
                            RegExp(r'^[A-Z0-9_]{3,50}$')
                                .hasMatch((v ?? '').toUpperCase())
                            ? null
                            : 'Enter 3 to 50 letters, numbers or underscores.',
                      ),
                      const SizedBox(height: StudentSpace.itemGap),
                    ],
                    TextFormField(
                      key: const ValueKey('service-name'),
                      initialValue: config['name'],
                      decoration: const InputDecoration(
                        labelText: 'Document name',
                      ),
                      onChanged: (v) => config['name'] = v.trim(),
                      validator: (v) => (v ?? '').trim().length < 3
                          ? 'Enter at least 3 characters.'
                          : null,
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    TextFormField(
                      initialValue: config['description'] ?? '',
                      decoration: const InputDecoration(
                        labelText: 'Description',
                      ),
                      minLines: 2,
                      maxLines: 3,
                      onChanged: (v) => config['description'] = v.trim(),
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    TextFormField(
                      initialValue: config['category'] ?? '',
                      decoration: const InputDecoration(labelText: 'Category'),
                      onChanged: (v) => config['category'] = v.trim(),
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    TextFormField(
                      initialValue: config['eligibility_instructions'] ?? '',
                      decoration: const InputDecoration(
                        labelText: 'Eligibility and instructions',
                      ),
                      minLines: 2,
                      maxLines: 3,
                      onChanged: (v) =>
                          config['eligibility_instructions'] = v.trim(),
                    ),
                    const SizedBox(height: StudentSpace.itemGap),
                    TextFormField(
                      initialValue: config['processing_days'].toString(),
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Estimated processing days (1–30)',
                      ),
                      onChanged: (v) =>
                          config['processing_days'] = int.tryParse(v),
                      validator: (v) {
                        final n = int.tryParse(v ?? '');
                        return n == null || n < 1 || n > 30
                            ? 'Enter 1 to 30 days.'
                            : null;
                      },
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Payment evidence required'),
                      value: payment['required'],
                      onChanged: (v) => setState(() {
                        dirty = true;
                        payment['required'] = v;
                        if (!v) {
                          payment['amount'] = null;
                          payment['instructions'] = null;
                          payment['reference_required'] = false;
                          payment['receipt_required'] = false;
                        }
                      }),
                    ),
                    if (payment['required']) ...[
                      TextFormField(
                        initialValue: payment['amount']?.toString() ?? '',
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Amount in PHP',
                        ),
                        onChanged: (v) => payment['amount'] = v,
                        validator: (v) => (double.tryParse(v ?? '') ?? 0) <= 0
                            ? 'Enter a positive amount.'
                            : null,
                      ),
                      const SizedBox(height: StudentSpace.itemGap),
                      TextFormField(
                        initialValue: payment['instructions'] ?? '',
                        decoration: const InputDecoration(
                          labelText: 'Payment instructions',
                        ),
                        minLines: 2,
                        maxLines: 3,
                        onChanged: (v) => payment['instructions'] = v.trim(),
                        validator: (v) => (v ?? '').trim().isEmpty
                            ? 'Enter payment instructions.'
                            : null,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Require payment reference'),
                        value: payment['reference_required'],
                        onChanged: (v) => setState(() {
                          payment['reference_required'] = v;
                          dirty = true;
                        }),
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Require receipt upload'),
                        value: payment['receipt_required'],
                        onChanged: (v) => setState(() {
                          payment['receipt_required'] = v;
                          dirty = true;
                        }),
                      ),
                    ],
                    const SizedBox(height: StudentSpace.sectionGap),
                    Text(
                      'Requirements',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    for (var i = 0; i < fields.length; i++)
                      requirement(fields[i], i),
                    OutlinedButton.icon(
                      onPressed: fields.length >= 20
                          ? null
                          : () => setState(() {
                              fields.add(newField());
                              dirty = true;
                            }),
                      icon: const Icon(Icons.add),
                      label: const Text('Add requirement'),
                    ),
                    if (error != null)
                      Text(
                        error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    if (message != null) Text(message!),
                    if (dirty && draft != null)
                      const Text(
                        'Save changes before previewing or publishing.',
                      ),
                    if (busy) const LinearProgressIndicator(),
                    const SizedBox(height: StudentSpace.sectionGap),
                    Wrap(
                      spacing: StudentSpace.tight,
                      runSpacing: StudentSpace.tight,
                      children: [
                        FilledButton(
                          onPressed: busy ? null : save,
                          child: const Text('Save draft'),
                        ),
                        if (draft != null)
                          OutlinedButton(
                            onPressed: busy || dirty ? null : preview,
                            child: const Text('Preview saved draft'),
                          ),
                        if (draft != null)
                          FilledButton(
                            onPressed: busy || dirty ? null : publish,
                            child: const Text('Publish saved draft'),
                          ),
                      ],
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
