#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * ButtonClick handler for a value button in the right-hand option panel.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: The button that was clicked <CONTROL>
 *
 * Return Value:
 * None
 */

params ["_display", "_control"];

// The button sits at base + 2; idcToConfig is keyed on the base.
private _data = GVAR(idcToConfig) get ((ctrlIDC _control) - 2);

if (isNil "_data") exitWith {};

[_display, _data] call FUNC(changeCurrentConfig);
