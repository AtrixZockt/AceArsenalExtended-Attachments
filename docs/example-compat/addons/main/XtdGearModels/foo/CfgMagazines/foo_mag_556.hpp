// A magazine family. Same schema as the optic -- the only difference is the config
// root it is nested under, which is what puts it on the arsenal's ammunition tabs
// instead of the attachment tabs.
//
// A model may not span roots: if FooMod shipped a 5.56 magazine and a 5.56 belt that
// belong on different tabs, they are two models, not two values of one axis.

class foo_mag_556
{
    label = "5.56 mm 30Rnd Magazine";
    author = "FooMod Team";

    options[] = {"ammo"};

    class ammo : foo_ammo
    {
        values[] = {"BALL", "TRACER", "AP"};
    };
};
