// Shared option definitions. Models inherit these, so a label is written once no
// matter how many models use the axis.
//
// WHICH AXES NEED ONE OF THESE
//
// camo, pantscamo, sleeves and Faction do NOT. aceax_gearinfo resolves those through
// XtdGearModels >> Conventional, so a bare `class camo { values[] = {...}; }` in a
// model already gets its labels and colour swatches -- see foo_optic_hawkeye.hpp.
//
// EVERY OTHER AXIS DOES. Without a base, values render as the raw uppercase config
// name: a dropdown reading "MILDOT" rather than "Mil-dot". That is the single most
// common thing to get wrong, and it does not error.
//
// Class names here are global, so prefix them with something of your own -- Arma
// merges same-named config classes across addons, and two compats defining a bare
// `reticle` differently would blend into each other.
//
// You may also re-declare `class CamoBase` here to ADD finishes to the palette
// aceax_gearinfo ships. Existing values are inherited, so restate only what is new.

class foo_reticle
{
    label = "Reticle";
    // 0 = the arsenal may switch this freely. Non-zero marks an axis that only
    // changes through an in-game action, which a compat rarely wants.
    changeingame = 0;
    // Empty on purpose: each model narrows it to the values that model actually has.
    values[] = {};

    class DOT
    {
        label = "Red dot";
        description = "1x, unmagnified";
    };
    class MILDOT
    {
        label = "Mil-dot";
        description = "Ranging reticle";
    };
};

class foo_ammo
{
    label = "Ammunition";
    changeingame = 0;
    values[] = {};

    class BALL
    {
        label = "Ball";
        description = "M855 standard ball";
    };
    class TRACER
    {
        label = "Tracer";
        description = "Every fourth round";
    };
    class AP
    {
        label = "Armour-piercing";
        description = "M995 tungsten core";
    };
};
