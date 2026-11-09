import 'package:flutter/material.dart';

abstract final class StudentColors {
  static const primary = Color(0xFF3157E8);
  static const primaryDark = Color(0xFF2447D8);
  static const background = Color(0xFFF4F6FA);
  static const surface = Colors.white;
  static const text = Color(0xFF172033);
  static const muted = Color(0xFF697386);
  static const border = Color(0xFFE5E9F1);
  static const green = Color(0xFF168447);
  static const greenTint = Color(0xFFE5F6EC);
  static const red = Color(0xFFC53A43);
  static const redTint = Color(0xFFFDEBEC);
  static const blueTint = Color(0xFFE9F0FF);
  static const amber = Color(0xFF96620A);
  static const amberTint = Color(0xFFFFF4D9);
  static const purple = Color(0xFF6741C8);
  static const purpleTint = Color(0xFFF0EBFF);
}

abstract final class StudentSpace {
  static const micro = 4.0;
  static const service = 10.0;
  static const tight = 8.0;
  static const compact = 14.0;
  static const medium = 16.0;
  static const page = 28.0;
  static const loginCard = 32.0;
  static const card = 22.0;
  static const sectionGap = 20.0;
  static const itemGap = 12.0;
}

abstract final class StudentSize {
  static const icon = 20.0;
  static const statusIcon = 36.0;
  static const navigationIcon = 38.0;
  static const serviceIcon = 44.0;
  static const loginLogo = 58.0;
  static const sidebar = 248.0;
  static const drawer = 264.0;
  static const topBar = 72.0;
  static const loginCardWidth = 470.0;
  static const dialogWidth = 600.0;
  static const dialogHorizontalAllowance = 40.0;
  static const searchWidth = 460.0;
  static const cardHeaderBreakpoint = 620.0;
}

abstract final class StudentRadius {
  static const iconTile = 11.0;
  static const logo = 12.0;
  static const loginLogo = 17.0;
  static const card = 18.0;
  static const control = 12.0;
  static const pill = 999.0;
}

class StudentTheme {
  static ThemeData get data {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: StudentColors.primary,
          brightness: Brightness.light,
        ).copyWith(
          primary: StudentColors.primary,
          onPrimary: Colors.white,
          surface: StudentColors.surface,
          error: StudentColors.red,
        );
    final outline = OutlineInputBorder(
      borderRadius: BorderRadius.circular(StudentRadius.control),
      borderSide: const BorderSide(color: StudentColors.border),
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: StudentColors.background,
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          color: StudentColors.text,
          fontSize: 28,
          height: 1.2,
          fontWeight: FontWeight.w700,
        ),
        headlineSmall: TextStyle(
          color: StudentColors.text,
          fontSize: 23,
          height: 1.25,
          fontWeight: FontWeight.w700,
        ),
        titleLarge: TextStyle(
          color: StudentColors.text,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        titleMedium: TextStyle(
          color: StudentColors.text,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: TextStyle(color: StudentColors.text, fontSize: 15),
        bodyMedium: TextStyle(color: StudentColors.text, fontSize: 14),
        bodySmall: TextStyle(color: StudentColors.muted, fontSize: 12),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: StudentColors.surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        border: outline,
        enabledBorder: outline,
        focusedBorder: outline.copyWith(
          borderSide: const BorderSide(color: StudentColors.primary, width: 2),
        ),
        errorBorder: outline.copyWith(
          borderSide: const BorderSide(color: StudentColors.red),
        ),
        focusedErrorBorder: outline.copyWith(
          borderSide: const BorderSide(color: StudentColors.red, width: 2),
        ),
        labelStyle: const TextStyle(color: StudentColors.muted),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: StudentColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(StudentRadius.control),
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: StudentColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(StudentRadius.control),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: StudentColors.primary,
          minimumSize: const Size(44, 44),
          side: const BorderSide(color: StudentColors.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(StudentRadius.control),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: StudentColors.primary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(StudentRadius.control),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: StudentColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(StudentRadius.card),
          side: const BorderSide(color: StudentColors.border),
        ),
        margin: EdgeInsets.zero,
      ),
      dividerTheme: const DividerThemeData(color: StudentColors.border),
      dialogTheme: DialogThemeData(
        backgroundColor: StudentColors.surface,
        surfaceTintColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(
          horizontal: StudentSpace.medium,
          vertical: StudentSpace.page,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(StudentRadius.card),
        ),
        titleTextStyle: const TextStyle(
          color: StudentColors.text,
          fontSize: 20,
          fontWeight: FontWeight.w700,
        ),
        contentTextStyle: const TextStyle(
          color: StudentColors.text,
          fontSize: 14,
          height: 1.45,
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: StudentColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(StudentRadius.control),
          side: const BorderSide(color: StudentColors.border),
        ),
      ),
      dropdownMenuTheme: const DropdownMenuThemeData(
        inputDecorationTheme: InputDecorationTheme(filled: true),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: StudentColors.blueTint,
        side: BorderSide.none,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(StudentRadius.pill),
        ),
        labelStyle: const TextStyle(color: StudentColors.text),
      ),
      listTileTheme: const ListTileThemeData(
        iconColor: StudentColors.muted,
        textColor: StudentColors.text,
        contentPadding: EdgeInsets.symmetric(horizontal: StudentSpace.medium),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: StudentColors.primary,
        linearTrackColor: StudentColors.blueTint,
      ),
    );
  }
}

class StudentPageHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  const StudentPageHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: StudentSpace.sectionGap),
    child: LayoutBuilder(
      builder: (context, constraints) {
        final titleBlock = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            if (subtitle != null) ...[
              const SizedBox(height: 5),
              Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        );
        if (trailing == null) return titleBlock;
        if (constraints.maxWidth < 520) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [titleBlock, const SizedBox(height: 8), trailing!],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: titleBlock),
            const SizedBox(width: StudentSpace.itemGap),
            trailing!,
          ],
        );
      },
    ),
  );
}

class StudentSectionCard extends StatelessWidget {
  final Widget child;
  final String? title;
  final IconData? icon;
  final Widget? action;
  final EdgeInsetsGeometry padding;
  const StudentSectionCard({
    super.key,
    required this.child,
    this.title,
    this.icon,
    this.action,
    this.padding = const EdgeInsets.all(StudentSpace.card),
  });

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: padding,
    decoration: BoxDecoration(
      color: StudentColors.surface,
      borderRadius: BorderRadius.circular(StudentRadius.card),
      border: Border.all(color: StudentColors.border),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0A14213D),
          blurRadius: 22,
          offset: Offset(0, 7),
        ),
      ],
    ),
    child: Material(
      type: MaterialType.transparency,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact =
              constraints.maxWidth < StudentSize.cardHeaderBreakpoint;
          final titleRow = Row(
            children: [
              if (icon != null) ...[
                Container(
                  width: StudentSize.statusIcon,
                  height: StudentSize.statusIcon,
                  decoration: BoxDecoration(
                    color: StudentColors.blueTint,
                    borderRadius: BorderRadius.circular(StudentRadius.control),
                  ),
                  child: Icon(
                    icon,
                    color: StudentColors.primary,
                    size: StudentSize.icon - 1,
                  ),
                ),
                const SizedBox(width: StudentSpace.tight + 3),
              ],
              Expanded(
                child: Text(
                  title ?? '',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (!compact) ?action,
            ],
          );
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (title != null) ...[
                titleRow,
                if (compact && action != null) ...[
                  const SizedBox(height: StudentSpace.tight),
                  Align(alignment: Alignment.centerLeft, child: action),
                ],
                const SizedBox(height: StudentSpace.itemGap),
              ],
              child,
            ],
          );
        },
      ),
    ),
  );
}

class StudentStatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final Color tint;
  const StudentStatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.color = StudentColors.primary,
    this.tint = StudentColors.blueTint,
  });

  @override
  Widget build(BuildContext context) => Container(
    constraints: const BoxConstraints(minWidth: 175),
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: StudentColors.surface,
      borderRadius: BorderRadius.circular(StudentRadius.card),
      border: Border.all(color: StudentColors.border),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0814213D),
          blurRadius: 16,
          offset: Offset(0, 4),
        ),
      ],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: tint,
                borderRadius: BorderRadius.circular(StudentRadius.pill),
              ),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(value, style: Theme.of(context).textTheme.headlineSmall),
      ],
    ),
  );
}

class StudentStatusBadge extends StatelessWidget {
  final String status;
  const StudentStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final key = status.toLowerCase();
    final positive = [
      'completed',
      'verified',
      'succeeded',
      'released',
      'resolved_manually',
      'resolved',
    ];
    final negative = [
      'rejected',
      'cancelled',
      'permanent_failure',
      'failed',
      'failed_permanently',
      'critical',
      'escalation',
      'escalated',
    ];
    final warning = [
      'needs_correction',
      'overdue',
      'stalled',
      'aging',
      'warning',
      'escalated',
      'aging',
    ];
    final neutral = [
      'not_reviewed',
      'unverified',
      'info',
      'informational',
      'no_payment',
    ];
    final color = positive.contains(key)
        ? StudentColors.green
        : negative.contains(key)
        ? StudentColors.red
        : warning.contains(key)
        ? StudentColors.amber
        : neutral.contains(key)
        ? StudentColors.muted
        : StudentColors.primary;
    final tint = positive.contains(key)
        ? StudentColors.greenTint
        : negative.contains(key)
        ? StudentColors.redTint
        : warning.contains(key)
        ? StudentColors.amberTint
        : neutral.contains(key)
        ? StudentColors.background
        : StudentColors.blueTint;
    final label = status
        .split('_')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(
        color: tint,
        borderRadius: BorderRadius.circular(StudentRadius.pill),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

abstract final class StudentDialogWidth {
  static double of(BuildContext context) =>
      (MediaQuery.sizeOf(context).width - StudentSize.dialogHorizontalAllowance)
          .clamp(0.0, StudentSize.dialogWidth)
          .toDouble();
}

class StudentEmptyState extends StatelessWidget {
  final String title;
  final String message;
  final IconData icon;
  const StudentEmptyState({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.inbox_outlined,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 34, horizontal: 16),
    child: Column(
      children: [
        Icon(icon, size: 34, color: StudentColors.muted),
        const SizedBox(height: 10),
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 4),
        Text(
          message,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    ),
  );
}

class StudentLoadingState extends StatelessWidget {
  const StudentLoadingState({super.key});
  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.all(StudentSpace.card),
    child: Center(child: CircularProgressIndicator()),
  );
}

class StudentErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const StudentErrorState({
    super.key,
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) => StudentSectionCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(message, style: const TextStyle(color: StudentColors.red)),
        const SizedBox(height: StudentSpace.itemGap),
        OutlinedButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: const Text('Try again'),
        ),
      ],
    ),
  );
}

enum StudentActionKind { primary, secondary, destructive, text }

class StudentActionButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final StudentActionKind kind;
  final bool loading;
  final IconData? icon;

  const StudentActionButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.kind = StudentActionKind.primary,
    this.loading = false,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final child = loading
        ? const SizedBox.square(
            dimension: StudentSize.icon,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: StudentSize.icon),
                const SizedBox(width: StudentSpace.tight),
              ],
              Text(label),
            ],
          );
    final callback = loading ? null : onPressed;
    return switch (kind) {
      StudentActionKind.primary => FilledButton(
        onPressed: callback,
        child: child,
      ),
      StudentActionKind.secondary => OutlinedButton(
        onPressed: callback,
        child: child,
      ),
      StudentActionKind.text => TextButton(onPressed: callback, child: child),
      StudentActionKind.destructive => FilledButton(
        onPressed: callback,
        style: FilledButton.styleFrom(
          backgroundColor: StudentColors.red,
          foregroundColor: Colors.white,
        ),
        child: child,
      ),
    };
  }
}

class StudentFilterBar extends StatelessWidget {
  final List<Widget> children;
  const StudentFilterBar({super.key, required this.children});

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 700
          ? children.length.clamp(1, 3)
          : 1;
      final gap = StudentSpace.itemGap;
      final width = columns == 1
          ? constraints.maxWidth
          : (constraints.maxWidth - (columns - 1) * gap) / columns;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: [
          for (final child in children) SizedBox(width: width, child: child),
        ],
      );
    },
  );
}

class StudentAppShell extends StatelessWidget {
  final String selected;
  final String userName;
  final int unreadCount;
  final bool busy;
  final TextEditingController searchController;
  final ValueChanged<String> onSearch;
  final ValueChanged<String> onNavigate;
  final VoidCallback onRefresh;
  final VoidCallback onSignOut;
  final VoidCallback? onProfile;
  final Widget child;
  final String brandName;
  final String menuLabel;
  final String searchHint;
  final bool showSearch;
  final List<(String, IconData)>? navigationItems;

  const StudentAppShell({
    super.key,
    required this.selected,
    required this.userName,
    required this.unreadCount,
    required this.busy,
    required this.searchController,
    required this.onSearch,
    required this.onNavigate,
    required this.onRefresh,
    required this.onSignOut,
    this.onProfile,
    required this.child,
    this.brandName = 'Student Docs',
    this.menuLabel = 'MENU',
    this.searchHint = 'Search requests...',
    this.showSearch = true,
    this.navigationItems,
  });

  static const _studentItems = [
    ('Dashboard', Icons.grid_view_rounded),
    ('Services', Icons.folder_open_outlined),
    ('Requests', Icons.description_outlined),
    ('Notifications', Icons.notifications_none_rounded),
  ];

  List<(String, IconData)> get _items => navigationItems ?? _studentItems;

  Widget _sidebar(BuildContext context, {required bool inDrawer}) => Container(
    color: StudentColors.surface,
    child: SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 20, 16, 32),
            child: Row(
              children: [
                Container(
                  width: StudentSize.navigationIcon,
                  height: StudentSize.navigationIcon,
                  decoration: BoxDecoration(
                    color: StudentColors.primary,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.school_rounded,
                    color: Colors.white,
                    size: 21,
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Text(
                    brandName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 0, 16, 10),
            child: Text(
              menuLabel,
              style: TextStyle(
                color: StudentColors.muted,
                fontSize: 11,
                letterSpacing: 1,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          for (final (name, icon) in _items)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
              child: _navItem(context, name, icon, inDrawer: inDrawer),
            ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Container(
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color: StudentColors.background,
                borderRadius: BorderRadius.circular(StudentRadius.control),
              ),
              child: const Text(
                'Development demo\nTest records only',
                style: TextStyle(
                  color: StudentColors.muted,
                  fontSize: 12,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _navItem(
    BuildContext context,
    String name,
    IconData icon, {
    required bool inDrawer,
  }) {
    final active = selected == name;
    return Builder(
      builder: (navContext) => Semantics(
        button: true,
        selected: active,
        child: Material(
          color: active ? StudentColors.primary : Colors.transparent,
          borderRadius: BorderRadius.circular(StudentRadius.control),
          child: InkWell(
            borderRadius: BorderRadius.circular(StudentRadius.control),
            onTap: () {
              if (inDrawer) Scaffold.of(navContext).closeDrawer();
              onNavigate(name);
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 12),
              child: Row(
                children: [
                  Icon(
                    icon,
                    size: 20,
                    color: active ? Colors.white : StudentColors.muted,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    name,
                    style: TextStyle(
                      color: active ? Colors.white : StudentColors.text,
                      fontSize: 14,
                      fontWeight: active ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _topBar(BuildContext context, {required bool compact}) => Container(
    height: StudentSize.topBar,
    padding: EdgeInsets.symmetric(horizontal: compact ? 14 : 26),
    decoration: const BoxDecoration(
      color: StudentColors.surface,
      border: Border(bottom: BorderSide(color: StudentColors.border)),
    ),
    child: Row(
      children: [
        if (compact)
          Builder(
            builder: (context) => IconButton(
              tooltip: 'Open navigation menu',
              onPressed: () => Scaffold.of(context).openDrawer(),
              icon: const Icon(Icons.menu_rounded),
            ),
          ),
        if (showSearch)
          Expanded(
            child: Align(
              alignment: Alignment.centerLeft,
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: StudentSize.searchWidth,
                ),
                child: TextField(
                  controller: searchController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: onSearch,
                  decoration: InputDecoration(
                    hintText: searchHint,
                    prefixIcon: Icon(Icons.search_rounded),
                    isDense: true,
                  ),
                ),
              ),
            ),
          )
        else
          const Spacer(),
        IconButton(
          tooltip: unreadCount > 0
              ? '$unreadCount unread notifications'
              : 'Notifications',
          onPressed: () => onNavigate('Notifications'),
          icon: Badge(
            isLabelVisible: unreadCount > 0,
            label: Text(unreadCount > 9 ? '9+' : '$unreadCount'),
            child: const Icon(Icons.notifications_none_rounded),
          ),
        ),
        const SizedBox(width: 4),
        PopupMenuButton<String>(
          tooltip: 'User menu',
          onSelected: (value) {
            if (value == 'signout') onSignOut();
            if (value == 'refresh') onRefresh();
            if (value == 'profile') onProfile?.call();
          },
          itemBuilder: (context) => [
            if (onProfile != null)
              const PopupMenuItem(value: 'profile', child: Text('My account')),
            const PopupMenuItem(
              value: 'refresh',
              child: Text('Refresh current page'),
            ),
            const PopupMenuItem(value: 'signout', child: Text('Sign out')),
          ],
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 7),
            child: Row(
              children: [
                CircleAvatar(
                  radius: StudentRadius.loginLogo,
                  backgroundColor: StudentColors.purpleTint,
                  child: Text(
                    userName.isEmpty ? 'S' : userName[0].toUpperCase(),
                    style: const TextStyle(
                      color: StudentColors.purple,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (!compact) ...[
                  const SizedBox(width: 9),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 150),
                    child: Text(
                      userName,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: StudentColors.text,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: 3),
                  const Icon(
                    Icons.expand_more,
                    size: 18,
                    color: StudentColors.muted,
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) => Theme(
    data: StudentTheme.data,
    child: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 900;
        return Scaffold(
          backgroundColor: StudentColors.background,
          drawer: compact
              ? Drawer(
                  width: StudentSize.drawer,
                  child: _sidebar(context, inDrawer: true),
                )
              : null,
          body: Row(
            children: [
              if (!compact) ...[
                SizedBox(
                  width: StudentSize.sidebar,
                  child: _sidebar(context, inDrawer: false),
                ),
                const VerticalDivider(
                  width: 1,
                  thickness: 1,
                  color: StudentColors.border,
                ),
              ],
              Expanded(
                child: Column(
                  children: [
                    _topBar(context, compact: compact),
                    if (busy) const LinearProgressIndicator(minHeight: 2),
                    Expanded(
                      child: SingleChildScrollView(
                        padding: EdgeInsets.all(
                          compact ? 18 : StudentSpace.page,
                        ),
                        child: Center(
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 1240),
                            child: child,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}
