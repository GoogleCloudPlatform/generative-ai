import 'dart:typed_data';

class Metadata {
  Uint8List? imageBytes;
  String name = '';
  String description = '';
  List<String> suggestedQuestions = [];

  Metadata({
    required this.imageBytes,
    required this.name,
    required this.description,
    required this.suggestedQuestions,
  });

  Metadata.fromJson(Uint8List image, Map<String, dynamic> jsonMap) {
    String localName;
    String localDescription;
    List<dynamic> localSuggestedQuestions;

    {
      'name': localName,
      'description': localDescription,
      'suggestedQuestions': localSuggestedQuestions,
    } = jsonMap;

    name = localName;
    description = localDescription;
    suggestedQuestions = List<String>.from(localSuggestedQuestions);
  }

  @override
  String toString() =>
      'Metadata(name: $name, description: $description, suggestedQuestions: $suggestedQuestions)';
}
