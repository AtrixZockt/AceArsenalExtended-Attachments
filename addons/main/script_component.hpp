#define COMPONENT main
#include "\z\aceaxatt\addons\main\script_mod.hpp"

// #define DEBUG_MODE_FULL
// #define DISABLE_COMPILE_CACHE

#ifdef DEBUG_ENABLED_MAIN
    #define DEBUG_MODE_FULL
#endif
#ifdef DEBUG_SETTINGS_MAIN
    #define DEBUG_SETTINGS DEBUG_SETTINGS_MAIN
#endif

#include "\z\aceaxatt\addons\main\script_macros.hpp"

// ACEAX's gearinfo functions, which do all the model/option resolution.
//
// CBA's EFUNC() cannot be used for these: it builds the name from THIS addon's
// PREFIX and would produce aceaxatt_gearinfo_fnc_*. They belong to a different
// mod, so the prefix has to be spelled out.
#define GEARINFO(fncName) TRIPLES(aceax_gearinfo,fnc,fncName)

// Matches ACEAX's arsenal component so the two option panels look identical.
#define INVISIBLE_COLOR 0, 0, 0, 0

#define WEAK_MATCH_BG_COLOR 0.4, 0.4, 0.4, 0.4
#define ACTIVE_BG_COLOR 0.5, 0.5, 0.5, 0.2

#define EXACT_MATCH_TEXT_COLOR 1, 1, 1, 1
#define WEAK_MATCH_TEXT_COLOR 0.9, 0.9, 0.9, 0.9
#define DISABLED_TEXT_COLOR 0.8, 0.8, 0.8, 0.8
