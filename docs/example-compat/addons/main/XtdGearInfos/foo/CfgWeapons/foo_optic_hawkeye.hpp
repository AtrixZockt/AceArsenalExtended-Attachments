// The six real optics that collapse into the one Hawkeye row.
//
// Each class is named after an item in FooMod, and gives its coordinates on the
// model's axes. A full 3 x 2 grid: three finishes times two reticles.
//
// Two rules, both of which fail silently when broken:
//   - every entry sets EVERY option in the model's options[]. A missing line reads
//     back as "" and that item then matches no dropdown combination at all.
//   - no two entries share the same coordinates, or they collide on one position.

class FooMod_Optic_Hawkeye_Black
{
    model = "foo_optic_hawkeye";
    camo = "BLK";
    reticle = "DOT";
};
class FooMod_Optic_Hawkeye_Black_Mildot
{
    model = "foo_optic_hawkeye";
    camo = "BLK";
    reticle = "MILDOT";
};
class FooMod_Optic_Hawkeye_Tan
{
    model = "foo_optic_hawkeye";
    camo = "TAN";
    reticle = "DOT";
};
class FooMod_Optic_Hawkeye_Tan_Mildot
{
    model = "foo_optic_hawkeye";
    camo = "TAN";
    reticle = "MILDOT";
};
class FooMod_Optic_Hawkeye_Olive
{
    model = "foo_optic_hawkeye";
    camo = "OD";
    reticle = "DOT";
};
class FooMod_Optic_Hawkeye_Olive_Mildot
{
    model = "foo_optic_hawkeye";
    camo = "OD";
    reticle = "MILDOT";
};
