import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../functionality/state.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            child: Card(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: 400,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SwitchListTile(
                      title: const Text('Super Cool Dark Mode'),
                      value: context.watch<ThemeNotifier>().darkMode,
                      onChanged: (val) {
                        context.read<ThemeNotifier>().toggleDarkMode(val);
                      },
                    ),
                    const ListTile(
                      title: Text(
                        'Made with ❤️',
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
