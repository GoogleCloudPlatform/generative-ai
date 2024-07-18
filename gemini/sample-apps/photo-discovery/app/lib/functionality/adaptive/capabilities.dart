/* 
This code assumes no camera access and always has physical keyboardfor demo 
purposes. Please use native OS APIs to determine if the device has certain
capabilities. See flutter.dev/adaptive for additional guidance.
*/

class Capabilities {
  static bool get hasCamera {
    return false;
  }

  static bool get hasPhysicalKeyboard {
    return true;
  }
}
