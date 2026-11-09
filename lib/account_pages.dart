import 'package:flutter/material.dart';

import 'api.dart';
import 'design_system.dart';

class RegisterPage extends StatefulWidget {
  final Api api;
  const RegisterPage({super.key, required this.api});
  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final form = GlobalKey<FormState>();
  final name = TextEditingController();
  final number = TextEditingController();
  final email = TextEditingController();
  final phone = TextEditingController();
  final password = TextEditingController();
  final confirmation = TextEditingController();
  bool accepted = false;
  bool showPassword = false;
  bool busy = false;
  String? error;

  @override
  void dispose() {
    for (final controller in [
      name,
      number,
      email,
      phone,
      password,
      confirmation,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    if (!accepted) {
      setState(() => error = 'Confirm that this is a development account.');
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.api.call('POST', '/auth/register', {
        'full_name': name.text.trim(),
        'student_number': number.text.trim(),
        'email': email.text.trim(),
        'phone_number': phone.text.trim().isEmpty ? null : phone.text.trim(),
        'password': password.text,
        'password_confirmation': confirmation.text,
        'terms_accepted': true,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Create student account')),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: StudentSize.loginCardWidth),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(StudentSpace.page),
          child: StudentSectionCard(
            child: Form(
              key: form,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Development registration uses test information. Student numbers are not verified.',
                  ),
                  const SizedBox(height: StudentSpace.sectionGap),
                  TextFormField(
                    controller: name,
                    decoration: const InputDecoration(labelText: 'Full name'),
                    validator: (v) => (v ?? '').trim().length < 2
                        ? 'Enter your full name.'
                        : null,
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  TextFormField(
                    controller: number,
                    decoration: const InputDecoration(
                      labelText: 'Student number',
                    ),
                    validator: (v) => (v ?? '').trim().isEmpty
                        ? 'Enter your student number.'
                        : null,
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  TextFormField(
                    controller: email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'Email'),
                    validator: (v) => (v ?? '').contains('@')
                        ? null
                        : 'Enter an email address.',
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  TextFormField(
                    controller: phone,
                    decoration: const InputDecoration(
                      labelText: 'Phone number (optional)',
                    ),
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  TextFormField(
                    controller: password,
                    obscureText: !showPassword,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      suffixIcon: IconButton(
                        tooltip: showPassword
                            ? 'Hide password'
                            : 'Show password',
                        onPressed: () =>
                            setState(() => showPassword = !showPassword),
                        icon: Icon(
                          showPassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                      ),
                    ),
                    validator: (v) => (v ?? '').length < 12
                        ? 'Use at least 12 characters.'
                        : null,
                  ),
                  const SizedBox(height: StudentSpace.itemGap),
                  TextFormField(
                    controller: confirmation,
                    obscureText: !showPassword,
                    decoration: const InputDecoration(
                      labelText: 'Confirm password',
                    ),
                    validator: (v) =>
                        v != password.text ? 'Passwords do not match.' : null,
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: accepted,
                    title: const Text(
                      'I understand this account is for development and testing.',
                    ),
                    onChanged: (v) => setState(() => accepted = v ?? false),
                  ),
                  if (error != null)
                    Text(
                      error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  if (busy) const LinearProgressIndicator(),
                  FilledButton(
                    onPressed: busy ? null : submit,
                    child: const Text('Create account'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class AccountPage extends StatefulWidget {
  final Api api;
  final Json actor;
  final bool forcePasswordChange;
  final VoidCallback? onSignedOut;
  final VoidCallback? onSignOut;
  const AccountPage({
    super.key,
    required this.api,
    required this.actor,
    this.forcePasswordChange = false,
    this.onSignedOut,
    this.onSignOut,
  });
  @override
  State<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends State<AccountPage> {
  final profileForm = GlobalKey<FormState>();
  final passwordForm = GlobalKey<FormState>();
  late Json actor;
  late final TextEditingController email;
  late final TextEditingController phone;
  final current = TextEditingController();
  final password = TextEditingController();
  final confirmation = TextEditingController();
  bool busy = false;
  String? error;
  String? success;

  @override
  void initState() {
    super.initState();
    actor = widget.actor;
    email = TextEditingController(text: actor['email']);
    phone = TextEditingController(text: actor['phone_number'] ?? '');
  }

  @override
  void dispose() {
    for (final controller in [email, phone, current, password, confirmation]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> save() async {
    if (!profileForm.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
      success = null;
    });
    try {
      final updated = await widget.api.call('PATCH', '/account/me', {
        'email': email.text.trim(),
        'phone_number': phone.text.trim(),
      }) as Json;
      if (mounted) {
        setState(() {
          actor = updated;
          success = 'Contact details saved.';
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> changePassword() async {
    if (!passwordForm.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
      success = null;
    });
    try {
      await widget.api.call('POST', '/account/password', {
        'current_password': current.text,
        'new_password': password.text,
        'new_password_confirmation': confirmation.text,
      });
      widget.api.csrf = null;
      if (mounted) {
        if (widget.forcePasswordChange) {
          widget.onSignedOut?.call();
        } else {
          Navigator.pop(context, {'signed_out': true});
        }
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: false,
    onPopInvokedWithResult: (didPop, _) {
      if (!didPop && !widget.forcePasswordChange) {
        Navigator.pop(context, {'actor': actor});
      }
    },
    child: Scaffold(
      appBar: AppBar(
        title: const Text('My account'),
        automaticallyImplyLeading: !widget.forcePasswordChange,
        actions: [
          if (widget.forcePasswordChange)
            TextButton(
              onPressed: busy ? null : widget.onSignOut,
              child: const Text('Sign out'),
            ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 700),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(StudentSpace.page),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.forcePasswordChange)
                  const Text(
                    'Change your temporary password before continuing.',
                  ),
                if (!widget.forcePasswordChange)
                  StudentSectionCard(
                    title: 'Profile',
                    icon: Icons.person_outline,
                    child: Form(
                      key: profileForm,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            actor['full_name'],
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(
                            actor['student_number'] ??
                                actor['staff_number'] ??
                                '',
                          ),
                          const SizedBox(height: StudentSpace.itemGap),
                          TextFormField(
                            controller: email,
                            decoration: const InputDecoration(
                              labelText: 'Email',
                            ),
                            validator: (v) => (v ?? '').contains('@')
                                ? null
                                : 'Enter an email address.',
                          ),
                          const SizedBox(height: StudentSpace.itemGap),
                          TextFormField(
                            controller: phone,
                            decoration: const InputDecoration(
                              labelText: 'Phone number (optional)',
                            ),
                          ),
                          const SizedBox(height: StudentSpace.itemGap),
                          FilledButton(
                            onPressed: busy ? null : save,
                            child: const Text('Save contact details'),
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: StudentSpace.sectionGap),
                StudentSectionCard(
                  title: 'Change password',
                  icon: Icons.lock_outline,
                  child: Form(
                    key: passwordForm,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Changing your password signs you out on all devices.',
                        ),
                        TextFormField(
                          controller: current,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Current password',
                          ),
                          validator: (v) => (v ?? '').isEmpty
                              ? 'Enter your current password.'
                              : null,
                        ),
                        const SizedBox(height: StudentSpace.itemGap),
                        TextFormField(
                          controller: password,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'New password',
                          ),
                          validator: (v) => (v ?? '').length < 12
                              ? 'Use at least 12 characters.'
                              : null,
                        ),
                        const SizedBox(height: StudentSpace.itemGap),
                        TextFormField(
                          controller: confirmation,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Confirm new password',
                          ),
                          validator: (v) => v != password.text
                              ? 'Passwords do not match.'
                              : null,
                        ),
                        const SizedBox(height: StudentSpace.itemGap),
                        OutlinedButton(
                          onPressed: busy ? null : changePassword,
                          child: const Text('Change password'),
                        ),
                      ],
                    ),
                  ),
                ),
                if (error != null)
                  Text(
                    error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                if (success != null) Text(success!),
                if (busy) const LinearProgressIndicator(),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
