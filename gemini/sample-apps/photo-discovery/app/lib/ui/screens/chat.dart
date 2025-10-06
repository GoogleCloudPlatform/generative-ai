import 'dart:async';
import 'dart:convert' as convert;

import 'package:app/config.dart';

import '../components/core_components.dart';
import 'package:flutter/material.dart';
import 'package:flutter_chat_ui/flutter_chat_ui.dart';
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import 'package:http/http.dart' as http;
import '../../functionality/state.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({this.onExit, super.key});

  final VoidCallback? onExit;

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  bool loading = false;
  final List<types.Message> _messages = [];
  final types.User _user = const types.User(id: 'user', firstName: 'You');
  final types.User _agent = const types.User(
      firstName: 'Khanh',
      id: 'agent',
      imageUrl: 'https://services.google.com/fh/files/misc/bunny.jpeg');

  @override
  void initState() {
    super.initState();
    _messages.add(types.TextMessage(
      id: const Uuid().v4(),
      author: _agent,
      text:
          'Hey there! My name is Khanh. I\'m your assistant, let me know how I can help.',
    ));
  }

  void _addMessage(types.Message message) {
    setState(() {
      _messages.insert(0, message);
    });
  }

  void _handleSendPressed(types.PartialText message) {
    final textMessage = types.TextMessage(
      author: _user,
      id: const Uuid().v4(),
      text: message.text,
    );

    _addMessage(textMessage);

    _sendMessageToAgent(message);
  }

  Future<String> askAgent(
      String name, String description, String question) async {
    var query = 'The photo is $name. $description. $question.';

    var endpoint = Uri.https(cloudRunHost, '/ask_gemini', {'query': query});
    var response = await http.get(endpoint);

    if (response.statusCode == 200) {
      var responseText = convert.utf8.decode(response.bodyBytes);

      return responseText.replaceAll(RegExp(r'\*'), '');
    }

    return 'Sorry I can\'t answer that.';
  }

  void _sendMessageToAgent(types.PartialText message) async {
    setState(() {
      loading = true;
    });

    var text = await askAgent(
      context.read<AppState>().metadata!.name,
      context.read<AppState>().metadata!.description,
      message.text,
    );

    final textMessage = types.TextMessage(
      author: _agent,
      id: const Uuid().v4(),
      text: text,
    );

    _addMessage(textMessage);

    setState(() {
      loading = false;
    });
  }

  void _pickSuggestedQuestion(String question) {
    var message = types.PartialText(text: question);

    _handleSendPressed(message);
  }

  @override
  Widget build(BuildContext context) {
    var metadata = context.watch<AppState>().metadata;

    Widget? suggestionsWidget;

    if (metadata != null) {
      if (_messages.length == 1) {
        suggestionsWidget = Padding(
          padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
          child: TagCapsule(
            onTap: _pickSuggestedQuestion,
            title: 'Suggested Questions',
            tags: metadata.suggestedQuestions,
          ),
        );
      }
    }

    List<types.User> typingUsers = [];

    if (loading) typingUsers.add(_agent);

    return Column(
      children: [
        AppBar(
          title: const Text('Chat with AI'),
          actions: (widget.onExit != null)
              ? [
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: IconButton(
                      color: Theme.of(context).colorScheme.secondary,
                      onPressed: widget.onExit,
                      icon: const Icon(
                        size: 28,
                        FontAwesomeIcons.circleXmark,
                      ),
                    ),
                  )
                ]
              : [],
        ),
        Expanded(
          child: Chat(
            typingIndicatorOptions: TypingIndicatorOptions(
              typingUsers: typingUsers,
            ),
            listBottomWidget: suggestionsWidget,
            messages: _messages,
            onSendPressed: _handleSendPressed,
            showUserAvatars: true,
            showUserNames: true,
            user: _user,
            theme: DefaultChatTheme(
              receivedMessageBodyTextStyle: TextStyle(
                color: Theme.of(context).colorScheme.onSurface,
              ),
              sentMessageBodyTextStyle: TextStyle(
                color: Theme.of(context).colorScheme.onSecondary,
              ),
              userAvatarNameColors: [
                Theme.of(context).colorScheme.primary,
              ],
              backgroundColor:
                  Theme.of(context).colorScheme.surfaceContainerHigh,
              primaryColor: Theme.of(context).colorScheme.primary,
              secondaryColor: Theme.of(context).colorScheme.surface,
            ),
          ),
        ),
      ],
    );
  }
}
