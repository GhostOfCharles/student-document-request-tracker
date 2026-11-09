import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:uuid/uuid.dart';

import 'api.dart';
import 'design_system.dart';

class RequirementsForm extends StatefulWidget {
  final Api api;
  final Json service;
  final Json? request;
  final bool preview;
  final void Function(Json) onSubmitted;
  const RequirementsForm({
    super.key,
    required this.api,
    required this.service,
    this.request,
    this.preview = false,
    required this.onSubmitted,
  });
  @override
  State<RequirementsForm> createState() => _RequirementsFormState();
}

class _RequirementsFormState extends State<RequirementsForm> {
  final formKey = GlobalKey<FormState>();
  final Map<int, dynamic> values = {};
  final Map<int, Json> files = {};
  final reference = TextEditingController();
  final key = const Uuid().v4();
  Json? receipt;
  bool busy = false;
  String? error;
  Json? retryPayload;
  Json get version => widget.service['version'];
  List get fields => version['requirements'];
  Json? get correction => widget.request?['open_correction_round'];

  @override
  void initState() {
    super.initState();
    final revision = widget.request?['latest_revision'];
    if (revision != null) {
      for (final answer in revision['answers']) {
        values[answer['requirement_id']] =
            answer['text_value'] ??
            answer['date_value'] ??
            answer['boolean_value'] ??
            answer['selected_option_id'];
      }
      for (final a in revision['attachments']) {
        files[a['requirement_id']] = a['file'];
      }
      reference.text = revision['payment']['reference'] ?? '';
      receipt = revision['payment']['receipt'];
    }
  }

  @override
  void dispose() {
    reference.dispose();
    super.dispose();
  }

  bool editable(int? id, [String kind = 'requirement']) {
    if (correction == null) return true;
    return (correction!['items'] as List).any(
      (item) =>
          item['target_kind'] == kind &&
          (kind != 'requirement' || item['requirement_id'] == id),
    );
  }

  Future<void> choose(int? id) async {
    try {
      final field = id == null
          ? null
          : fields.cast<Json>().firstWhere((f) => f['id'] == id);
      final allowed =
          field?['allowed_mime_types'] as List? ??
          const ['application/pdf', 'image/jpeg', 'image/png'];
      final extensions = <String>[
        if (allowed.contains('application/pdf')) 'pdf',
        if (allowed.contains('image/jpeg')) ...['jpg', 'jpeg'],
        if (allowed.contains('image/png')) 'png',
      ];
      final limit = field?['max_file_size_bytes'] as int? ?? 5242880;
      final pick = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: extensions,
      );
      if (pick == null) return;
      final size = await pick.length();
      if (size == null || size > limit || size == 0) {
        throw ApiError(
          'FILE_TOO_LARGE',
          'Select a nonempty file within the configured size limit.',
          413,
        );
      }
      setState(() {
        busy = true;
        error = null;
      });
      final file = await widget.api.upload(pick.name, await pick.readAsBytes());
      if (!mounted) return;
      setState(() {
        if (id == null) {
          receipt = file;
        } else {
          files[id] = file;
        }
        retryPayload = null;
      });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Json payload() {
    final answers = <Json>[];
    final attachments = <Json>[];
    for (final field in fields) {
      final int id = field['id'];
      final type = field['field_type'];
      if (type == 'file') {
        if (files[id] != null) {
          attachments.add({
            'requirement_id': id,
            'stored_file_id': files[id]!['id'],
          });
        }
        continue;
      }
      final value = values[id];
      if (value == null || (value is String && value.trim().isEmpty)) continue;
      final property = {
        'text': 'text_value',
        'select': 'selected_option_id',
        'date': 'date_value',
        'checkbox': 'boolean_value',
      }[type]!;
      answers.add({'requirement_id': id, property: value});
    }
    final result = <String, dynamic>{
      'client_submission_key': key,
      'answers': answers,
      'attachments': attachments,
    };
    if (version['payment']['required']) {
      result['payment'] = {
        if (reference.text.trim().isNotEmpty)
          'reference': reference.text.trim(),
        if (receipt != null) 'receipt_file_id': receipt!['id'],
      };
    }
    if (widget.request != null) {
      result.addAll({
        'expected_row_version': widget.request!['row_version'],
        'correction_round_id': correction!['id'],
      });
    } else {
      result.addAll({
        'service_id': widget.service['id'],
        'service_version_id': version['id'],
      });
    }
    return result;
  }

  Future<void> submit() async {
    if (!formKey.currentState!.validate()) return;
    for (final field in fields) {
      if (field['field_type'] == 'date' &&
          field['required'] &&
          values[field['id']] == null) {
        setState(() => error = '${field['label']}: choose a valid date.');
        return;
      }
      if (field['field_type'] == 'file' &&
          field['required'] &&
          files[field['id']] == null) {
        setState(
          () => error = '${field['label']}: upload the required evidence.',
        );
        return;
      }
    }
    if (version['payment']['receipt_required'] && receipt == null) {
      setState(() => error = 'Upload the required payment evidence.');
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm submission'),
        content: const Text(
          'Submit these details and attachments for registrar review?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Go back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm submit'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      retryPayload ??= payload();
      final path = widget.request == null
          ? '/requests'
          : '/requests/${widget.request!['id']}/correction-submissions';
      final result = await widget.api.call('POST', path, retryPayload);
      if (mounted) widget.onSubmitted(result);
    } catch (e) {
      if (e is ApiError && e.status != 0 && e.status < 500) retryPayload = null;
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget fieldWidget(Json field) {
    final int id = field['id'];
    final type = field['field_type'];
    final label = '${field['label']}${field['required'] ? ' *' : ''}';
    final enabled = !busy && retryPayload == null && editable(id);
    Widget child;
    if (type == 'file') {
      child = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label),
          if (field['help_text'] != null) Text(field['help_text']),
          OutlinedButton.icon(
            onPressed: enabled && !widget.preview ? () => choose(id) : null,
            icon: const Icon(Icons.upload_file),
            label: Text(
              files[id] == null
                  ? 'Upload ${field['label']}'
                  : 'Replace ${field['label']}: ${files[id]!['original_filename']}',
            ),
          ),
        ],
      );
    } else if (type == 'select') {
      child = DropdownButtonFormField<int>(
        initialValue: values[id],
        isExpanded: true,
        decoration: InputDecoration(labelText: label),
        items: [
          for (final option in field['options'])
            DropdownMenuItem<int>(
              value: option['id'],
              child: Text(option['label']),
            ),
        ],
        onChanged: enabled
            ? (value) => setState(() => values[id] = value)
            : null,
        validator: (v) =>
            field['required'] && v == null ? 'Select an option.' : null,
      );
    } else if (type == 'checkbox') {
      child = FormField<bool>(
        initialValue: values[id] ?? false,
        validator: (_) => field['required'] && values[id] != true
            ? 'This confirmation is required.'
            : null,
        builder: (state) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(label),
              value: values[id] ?? false,
              onChanged: enabled
                  ? (value) {
                      setState(() => values[id] = value);
                      state.didChange(value);
                    }
                  : null,
            ),
            if (state.hasError)
              Text(
                state.errorText!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      );
    } else if (type == 'date') {
      child = OutlinedButton.icon(
        onPressed: enabled
            ? () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate:
                      DateTime.tryParse(values[id] ?? '') ?? DateTime.now(),
                  firstDate: DateTime(2000),
                  lastDate: DateTime(2100),
                );
                if (picked != null) {
                  setState(
                    () =>
                        values[id] = picked.toIso8601String().substring(0, 10),
                  );
                }
              }
            : null,
        icon: const Icon(Icons.calendar_month),
        label: Text('$label: ${values[id] ?? 'Choose date'}'),
      );
    } else {
      child = TextFormField(
        initialValue: values[id] ?? '',
        enabled: enabled,
        decoration: InputDecoration(
          labelText: label,
          helperText: field['help_text'],
        ),
        maxLength: field['max_length'] ?? 1000,
        onChanged: (value) => values[id] = value,
        validator: (v) {
          final value = (v ?? '').trim();
          if (field['required'] && value.isEmpty) {
            return 'This field is required.';
          }
          if (value.isNotEmpty && value.length < (field['min_length'] ?? 0)) {
            return 'Enter at least ${field['min_length']} characters.';
          }
          return null;
        },
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: StudentSpace.sectionGap),
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) => Form(
    key: formKey,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          widget.request == null ? 'Create request' : 'Correct and resubmit',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Text(
          '${version['name']} • version ${version['version_number']} • ${version['processing_days']} calendar days',
        ),
        Text(version['eligibility_instructions'] ?? ''),
        if (correction != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: StudentSpace.medium),
            child: Text(
              '${correction!['general_instructions']}\n${(correction!['items'] as List).map((i) => i['instruction']).join('\n')}',
            ),
          ),
        const SizedBox(height: StudentSpace.page - 4),
        for (final field in fields) fieldWidget(field),
        if (version['payment']['required']) ...[
          Text(
            'Payment evidence • ${version['payment']['currency']} ${version['payment']['amount']}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(version['payment']['instructions'] ?? ''),
          if (version['payment']['reference_required'])
            TextFormField(
              controller: reference,
              enabled:
                  !busy &&
                  retryPayload == null &&
                  editable(null, 'payment_reference'),
              decoration: const InputDecoration(labelText: 'Payment reference'),
              validator: (v) =>
                  version['payment']['reference_required'] &&
                      (v ?? '').trim().isEmpty
                  ? 'Enter the payment reference.'
                  : null,
            ),
          if (version['payment']['receipt_required'])
            OutlinedButton.icon(
              onPressed:
                  !widget.preview &&
                      !busy &&
                      retryPayload == null &&
                      editable(null, 'payment_receipt')
                  ? () => choose(null)
                  : null,
              icon: const Icon(Icons.receipt_long),
              label: Text(
                receipt == null
                    ? 'Upload payment receipt'
                    : 'Replace payment receipt: ${receipt!['original_filename']}',
              ),
            ),
        ],
        if (error != null)
          Padding(
            padding: const EdgeInsets.all(StudentSpace.itemGap),
            child: Text(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        if (retryPayload != null && !busy)
          const Text(
            'Retry sends the same submission safely. Reopen the form to edit after checking My Requests.',
          ),
        if (busy) const LinearProgressIndicator(),
        if (widget.preview)
          const Text('Preview only. Uploading and submission are disabled.')
        else
          FilledButton.icon(
            onPressed: busy ? null : submit,
            icon: const Icon(Icons.send),
            label: Text(
              retryPayload != null
                  ? 'Retry identical submission'
                  : 'Submit request',
            ),
          ),
      ],
    ),
  );
}
