// The infos: one class per REAL in-game item, saying which model it belongs to and
// where it sits on that model's axes.
//
// Note the plural. The root-level class read by aceax_gearinfo is XtdGearInfos --
// singular XtdGearInfo means something else (a class nested inside the item's own
// CfgWeapons entry), and a root-level singular is silently never read.
//
// These classes are named after FooMod's items but do not inherit from them, and they
// live in their own config tree rather than under CfgWeapons. That is what lets the
// compat load without FooMod: the entries simply describe items that are not there.
//
// No XtdGearModels_Common.hpp here -- option bases belong to the models side only.

class XtdGearInfos
{
    class CfgWeapons
    {
        // foo
        #include "XtdGearInfos\foo\CfgWeapons\foo_optic_hawkeye.hpp"
    };

    class CfgMagazines
    {
        // foo
        #include "XtdGearInfos\foo\CfgMagazines\foo_mag_556.hpp"
    };
};
