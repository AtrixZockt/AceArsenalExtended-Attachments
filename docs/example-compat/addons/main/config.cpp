// The whole addon. A compat is pure config -- no SQF, no CBA macros, no
// script_component.hpp -- so this file plus the two trees it includes is everything.

class CfgPatches
{
    class aceaxfoo_main
    {
        name = "ACEAX FooMod Compat";
        units[] = {};
        weapons[] = {};
        requiredVersion = "1.0";
        // Deliberately only aceax_gearinfo. Listing FooMod's own addons here would
        // stop the mod loading for anyone without it. XtdGearInfos refers to the
        // source classes by name only, in a config tree of its own, so entries for
        // absent classes are inert rather than broken.
        requiredAddons[] = {"aceax_gearinfo"};
        author = "You";
        version = "1.0.0";
    };
};

#include "XtdGearModels.hpp"

#include "XtdGearInfos.hpp"
