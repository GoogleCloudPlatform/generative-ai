import 'package:flutter/material.dart';

class ShortcutHelper extends StatelessWidget {
  const ShortcutHelper(
      {required this.bindings, required this.child, super.key});

  final Map<ShortcutActivator, void Function()> bindings;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return CallbackShortcuts(
      bindings: bindings,
      child: Focus(autofocus: true, child: child),
    );
  }
}

class PullToRefreshHelper extends StatefulWidget {
  const PullToRefreshHelper(
      {required this.onRefresh, required this.child, super.key});

  final Future<void> Function() onRefresh;
  final Widget child;

  @override
  State<PullToRefreshHelper> createState() => _PullToRefreshHelperState();
}

class _PullToRefreshHelperState extends State<PullToRefreshHelper> {
  final GlobalKey<RefreshIndicatorState> _refreshIndicatorKey =
      GlobalKey<RefreshIndicatorState>();

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      key: _refreshIndicatorKey,
      onRefresh: widget.onRefresh,
      child: widget.child,
    );
  }
}
