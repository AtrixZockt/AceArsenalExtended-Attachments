#define MAINPREFIX z
#define PREFIX aceaxatt

#include "script_version.hpp"

#define VERSION MAJOR.MINOR
#define VERSION_AR MAJOR,MINOR,PATCH,BUILD

// Higher than ACEAX's own 1.88 because this addon uses HashMaps and `continue`.
// Not a practical restriction: ACE3, which is a hard dependency, needs far newer
// than this anyway.
#define REQUIRED_VERSION 2.02
