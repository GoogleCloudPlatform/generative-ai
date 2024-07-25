import 'package:app/ui/utilities.dart';
import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:go_router/go_router.dart';

import '../../functionality/routing.dart';

var navBarDestinations = const [
  NavigationDestination(
    icon: Icon(FontAwesomeIcons.cameraRetro),
    label: 'Quick ID',
  ),
  NavigationDestination(
    icon: Icon(FontAwesomeIcons.gear),
    label: 'Settings',
  ),
];

var navRailDestinations = const [
  NavigationRailDestination(
    icon: Icon(FontAwesomeIcons.cameraRetro),
    label: Text('Quick ID'),
    padding: EdgeInsets.all(16),
  ),
  NavigationRailDestination(
    icon: Icon(FontAwesomeIcons.gear),
    label: Text('Settings'),
    padding: EdgeInsets.all(16),
  ),
];

class ScaffoldWithNavbar extends StatefulWidget {
  const ScaffoldWithNavbar({required this.child, super.key});

  final Widget child;

  @override
  State<ScaffoldWithNavbar> createState() => _ScaffoldWithNavbarState();
}

class _ScaffoldWithNavbarState extends State<ScaffoldWithNavbar> {
  int screenIndex = 0;

  void selectDestination(int index) {
    var route = routes[index];
    context.go(route.path);
    setState(
      () {
        screenIndex = index;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final useSideNavRail =
        MediaQuery.sizeOf(context).width >= Breakpoints.compact;

    return Scaffold(
      body: Row(
        children: [
          if (useSideNavRail)
            NavRail(
              backgroundColor: Theme.of(context).colorScheme.surface,
              selectedIndex: screenIndex,
              onDestinationSelected: selectDestination,
            ),
          Expanded(child: widget.child),
        ],
      ),
      bottomNavigationBar: useSideNavRail
          ? null
          : NavigationBar(
              selectedIndex: screenIndex,
              onDestinationSelected: selectDestination,
              destinations: navBarDestinations,
            ),
    );
  }
}

class NavRail extends StatelessWidget {
  const NavRail({
    super.key,
    required this.backgroundColor,
    required this.selectedIndex,
    this.onDestinationSelected,
  });

  final Color backgroundColor;
  final int selectedIndex;
  final ValueChanged<int>? onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    return NavigationRail(
      selectedIndex: selectedIndex,
      backgroundColor: backgroundColor,
      onDestinationSelected: onDestinationSelected,
      labelType: NavigationRailLabelType.all,
      useIndicator: true,
      leading: const SizedBox(height: 48),
      destinations: navRailDestinations,
    );
  }
}
