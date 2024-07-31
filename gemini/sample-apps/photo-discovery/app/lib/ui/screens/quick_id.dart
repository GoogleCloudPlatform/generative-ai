import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:firebase_vertexai/firebase_vertexai.dart';
import 'package:image_picker/image_picker.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:image_gallery_saver/image_gallery_saver.dart';
import 'package:permission_handler/permission_handler.dart';
import '../components/adaptive_helper_widgets.dart';

import '../../models/metadata.dart';
import '../components/core_components.dart';
import '../../functionality/state.dart';
import '../../functionality/adaptive/policies.dart';
import '../screens/chat.dart';
import '../utilities.dart';
import '../../config.dart';

class GenerateMetadataScreen extends StatefulWidget {
  const GenerateMetadataScreen({super.key});

  @override
  State<GenerateMetadataScreen> createState() => _GenerateMetadataScreenState();
}

class _GenerateMetadataScreenState extends State<GenerateMetadataScreen> {
  late final GenerativeModel model;
  bool _loading = false;
  Uint8List? _image;
  double chatWidth = 0;

  @override
  void initState() {
    super.initState();
    model = FirebaseVertexAI.instance.generativeModel(
      model: geminiModel,
      generationConfig: GenerationConfig(
        temperature: 0,
        responseMimeType: 'application/json',
      ),
    );
  }

  @override
  void didChangeDependencies() {
    if (Policy.shouldTakePicture) {
      requestCameraPermissions();
    }
    super.didChangeDependencies();
  }

  void requestCameraPermissions() async {
    // Request multiple permissions at once.
    await [Permission.camera, Permission.photos].request();
  }

  void pickImage(ImageSource source) async {
    try {
      final pickedImage = await ImagePicker().pickImage(source: source);

      if (pickedImage == null) {
        return;
      }

      var fileBytes = await pickedImage.readAsBytes();

      if (source == ImageSource.camera &&
          await Permission.mediaLibrary.request().isGranted) {
        ImageGallerySaver.saveImage(
          fileBytes,
          quality: 100,
          name: pickedImage.name,
        );
      }

      setState(() {
        _image = fileBytes;
      });

      _sendVertexMessage();
    } catch (e) {
      _showError(e.toString());
    }
  }

  void removeImage(BuildContext context) {
    setState(() {
      _image = null;
      context.read<AppState>().clearMetadata();
    });
  }

  @override
  Widget build(BuildContext context) {
    Metadata? metadata = context.watch<AppState>().metadata;
    final isExpanded = MediaQuery.sizeOf(context).width >= Breakpoints.expanded;

    // Ask for a photo from the user if they haven't provided one.
    if (_image == null) {
      return PhotoSelectionScreen(
        onTakePicture: () => pickImage(ImageSource.camera),
        onSelectPicture: () => pickImage(ImageSource.gallery),
      );
    }

    // Build main content screen with image, metadata, etc.
    return (isExpanded)
        // Build horizontal row layout for wide devices
        ? ExpandedScreen(
            image: _image!,
            loading: _loading,
            metadata: metadata,
            onRemoveImage: () => removeImage(context),
          )
        // Build vertical column layout for small devices
        : CompactScreen(
            image: _image!,
            loading: _loading,
            metadata: metadata,
            onRemoveImage: () => removeImage(context),
          );
  }

  Future<void> _sendVertexMessage() async {
    if (_loading == true || _image == null) {
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      final messageContents = Content.multi(
        [
          TextPart(
              'What is the subject in this photo? Provide the name of the photo subject, and description as specific as possible, and 3 suggested questions that I can ask for more information about this object. Answer in JSON format with the keys "name", "description" and "suggestedQuestions".'),
          DataPart('image/jpeg', _image!),
        ],
      );

      var response = await model.generateContent([messageContents]);

      var text = response.text;

      if (text == null) {
        _showError('No response from API.');
        return;
      } else {
        var jsonMap = json.decode(text);

        if (mounted) {
          context.read<AppState>().updateMetadata(Metadata.fromJson(jsonMap));
        }
      }
    } catch (e) {
      _showError(e.toString());
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  void _showError(String message) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Something went wrong'),
          content: SingleChildScrollView(
            child: Text(message),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: const Text('OK'),
            )
          ],
        );
      },
    );
  }
}

class CompactScreen extends StatelessWidget {
  const CompactScreen(
      {required this.image,
      required this.loading,
      required this.metadata,
      required this.onRemoveImage,
      super.key});

  final Uint8List image;
  final bool loading;
  final Metadata? metadata;
  final VoidCallback onRemoveImage;

  void goToChat(BuildContext context) {
    if (loading) return;

    context.go('/chat');
  }

  @override
  Widget build(BuildContext context) {
    Widget content = LayoutBuilder(
      builder: (context, constraints) {
        return ListView(
          children: [
            Image.memory(image),
            const SizedBox.square(dimension: 16),
            Padding(
              padding: const EdgeInsets.all(8),
              child: MetadataCard(
                loading: loading,
                metadata: metadata,
              ),
            ),
            const SizedBox.square(dimension: 8),
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              RemoveImageButton(
                onPressed: onRemoveImage,
              ),
              const SizedBox.square(
                dimension: 8,
              ),
              TellMeMoreButton(
                onPressed: () => goToChat(context),
              )
            ]),
            const SizedBox.square(dimension: 24),
          ],
        );
      },
    );

    if (Policy.shouldHaveKeyboardShortcuts) {
      content = ShortcutHelper(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(control: true, LogicalKeyboardKey.keyT): () {
            goToChat(context);
          },
        },
        child: content,
      );
    }

    return content;
  }
}

class ExpandedScreen extends StatelessWidget {
  ExpandedScreen(
      {required this.image,
      required this.loading,
      required this.metadata,
      required this.onRemoveImage,
      super.key});

  final Uint8List image;
  final bool loading;
  final Metadata? metadata;
  final VoidCallback onRemoveImage;
  final OverlayPortalController _aiChatController = OverlayPortalController();

  void showChat() {
    if (loading) return;

    _aiChatController.toggle();
  }

  @override
  Widget build(BuildContext context) {
    Widget content = LayoutBuilder(builder: (context, constraints) {
      return Padding(
        padding: const EdgeInsets.all(4.0),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ConstrainedBox(
              constraints: BoxConstraints(maxWidth: constraints.maxWidth * .55),
              child: Image.memory(image),
            ),
            SizedBox.square(
              dimension: constraints.maxWidth * .010,
            ),
            Column(
                mainAxisAlignment: MainAxisAlignment.start,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  ConstrainedBox(
                    constraints:
                        BoxConstraints(maxWidth: constraints.maxWidth * .4),
                    child: MetadataCard(
                      loading: loading,
                      metadata: metadata,
                    ),
                  ),
                  const SizedBox.square(dimension: 24),
                  Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    RemoveImageButton(
                      onPressed: onRemoveImage,
                    ),
                    const SizedBox.square(
                      dimension: 8,
                    ),
                    TellMeMoreButton(
                      onPressed: () => showChat(),
                    ),
                    ChatPopUp(
                      opController: _aiChatController,
                      onToggleChat: () => showChat(),
                    ),
                  ]),
                ]),
          ],
        ),
      );
    });

    if (Policy.shouldHaveKeyboardShortcuts) {
      content = ShortcutHelper(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(control: true, LogicalKeyboardKey.keyT): () {
            showChat();
          },
        },
        child: content,
      );
    }

    return content;
  }
}

class RemoveImageButton extends StatelessWidget {
  const RemoveImageButton({required this.onPressed, super.key});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return TextButton.icon(
      icon: Icon(
        FontAwesomeIcons.trashCan,
        color: Theme.of(context).colorScheme.error,
      ),
      onPressed: onPressed,
      label: Text(
        'Remove image',
        style: TextStyle(color: Theme.of(context).colorScheme.error),
      ),
    );
  }
}

class TellMeMoreButton extends StatelessWidget {
  const TellMeMoreButton({required this.onPressed, super.key});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      style: const ButtonStyle(
        padding: WidgetStatePropertyAll(
          EdgeInsets.symmetric(horizontal: 36, vertical: 16),
        ),
      ),
      onPressed: onPressed,
      icon: const Icon(FontAwesomeIcons.solidMessage),
      label: const Text(
        'Tell me more',
        style: TextStyle(
          fontSize: 18,
        ),
      ),
    );
  }
}

class PhotoSelectionScreen extends StatelessWidget {
  const PhotoSelectionScreen(
      {required this.onTakePicture, required this.onSelectPicture, super.key});

  final VoidCallback onTakePicture;
  final VoidCallback onSelectPicture;

  @override
  Widget build(BuildContext context) {
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      if (Policy.shouldTakePicture)
        ElevatedButton.icon(
          onPressed: onTakePicture,
          icon: const Icon(FontAwesomeIcons.camera),
          label: const Text('Take Photo'),
        ),
      const SizedBox.square(
        dimension: 16,
      ),
      ElevatedButton.icon(
        onPressed: onSelectPicture,
        icon: const Icon(FontAwesomeIcons.image),
        label: const Text('Choose from Library'),
      ),
    ]);
  }
}

class ChatPopUp extends StatelessWidget {
  const ChatPopUp(
      {required this.opController, required this.onToggleChat, super.key});

  final OverlayPortalController opController;
  final VoidCallback onToggleChat;

  @override
  Widget build(BuildContext context) {
    return OverlayPortal(
      controller: opController,
      overlayChildBuilder: (BuildContext context) {
        var width = MediaQuery.sizeOf(context).width;
        var height = MediaQuery.sizeOf(context).height;
        return Positioned(
          right: width * .05,
          bottom: 0,
          child: Container(
            decoration: BoxDecoration(boxShadow: [
              BoxShadow(
                color: Theme.of(context).colorScheme.surfaceDim,
                blurRadius: 36,
              )
            ]),
            width: width * .28,
            height: height * .5,
            child: ChatPage(
              onExit: onToggleChat,
            ),
          ),
        );
      },
    );
  }
}
