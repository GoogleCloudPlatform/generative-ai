import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../ui/screens/settings.dart';
import '../ui/screens/quick_id.dart';
import '../ui/screens/chat.dart';
import '../ui/components/navigation.dart';

List<GoRoute> routes = [
  GoRoute(
    path: '/',
    builder: (context, state) {
      return const GenerateMetadataScreen();
    },
    routes: [
      GoRoute(
        path: 'chat',
        builder: (context, state) {
          return const ChatPage();
        },
      ),
    ],
  ),
  GoRoute(
    path: '/settings',
    builder: (context, state) {
      return const SettingsScreen();
    },
  ),
];

// GoRouter configuration
final router = GoRouter(
  routes: [
    ShellRoute(
      builder: (context, state, child) {
        return ScaffoldWithNavbar(child: child);
      },
      routes: routes,
    )
  ],
);
