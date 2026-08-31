// One arsenal row: the Hawkeye scope family, with two dropdowns under it.
//
// The class name is global, so it carries the foo_ prefix. label is what the row and
// the option panel are titled; author is credited under it.

class foo_optic_hawkeye
{
    label = "Hawkeye Scope";
    author = "FooMod Team";

    // The axes, in the order the dropdowns are drawn. Every class listed here must
    // exist below, and every XtdGearInfos entry for this model must set every one.
    options[] = {"camo", "reticle"};

    // Bare, no parent. camo is one of the four conventional names, so the labels
    // ("Black", "Tan", "Olive Drab") and the colour swatches come from
    // aceax_gearinfo's CamoBase automatically. Only the subset this family has.
    class camo
    {
        values[] = {"BLK", "TAN", "OD"};
    };

    // Inherits the base in XtdGearModels_Common.hpp, which supplies the axis label
    // and a label plus description for each value. Without that parent this dropdown
    // would read "DOT" and "MILDOT".
    class reticle : foo_reticle
    {
        values[] = {"DOT", "MILDOT"};
    };
};
