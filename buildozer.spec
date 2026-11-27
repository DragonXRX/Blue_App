[app]

# (str) Title of your application
title = BlueChat

# (str) Package name
package.name = bluechat

# (str) Package domain (needed for android packaging)
package.domain = org.bluechat.app

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the source directory)
source.include_exts = py,png,jpg,jpeg,3gp,wav

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,pyjnius,android

# (list) Permissions required for Bluetooth, Audio Recording, Media File Sharing, WakeLock and Discovery
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,BLUETOOTH_ADVERTISE,RECORD_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,READ_MEDIA_VIDEO,WAKE_LOCK,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) Automatically accept Android SDK licenses
android.accept_sdk_license = True

# (list) The Android architectures to build for
android.archs = arm64-v8a

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with py_compile)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
