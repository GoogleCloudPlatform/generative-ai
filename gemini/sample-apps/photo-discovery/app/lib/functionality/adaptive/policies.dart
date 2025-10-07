import './capabilities.dart';

class Policy {
  static bool get shouldTakePicture {
    return Capabilities.hasCamera;
  }

  static bool get shouldHaveKeyboardShortcuts {
    return Capabilities.hasPhysicalKeyboard;
  }
}
