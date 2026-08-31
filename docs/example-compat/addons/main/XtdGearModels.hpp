// The models: one class per arsenal row, describing what its dropdowns offer.
//
// The nesting is XtdGearModels >> <config root> >> <model class>. A model belongs to
// exactly one root -- an optic is a CfgWeapons item, a magazine is a CfgMagazines one --
// and must not span arsenal tabs.
//
// One #include per model, grouped by source-mod pack, is only an organising habit
// copied from the generated compats so this looks like what you will meet there. Two
// models would fit perfectly well inline.

class XtdGearModels
{
    // Included INSIDE the class, so the option bases land as siblings of the config
    // roots below rather than at file scope.
    #include "XtdGearModels_Common.hpp"

    class CfgWeapons
    {
        // foo
        #include "XtdGearModels\foo\CfgWeapons\foo_optic_hawkeye.hpp"
    };

    class CfgMagazines
    {
        // foo
        #include "XtdGearModels\foo\CfgMagazines\foo_mag_556.hpp"
    };
};
