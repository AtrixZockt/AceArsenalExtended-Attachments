#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * onLBSelChanged for the arsenal's right panel.
 *
 * ACE's own handler runs first and unchanged -- it equips the item, fires
 * ace_arsenal_weaponItemChanged and updates the weight readout. Everything this
 * addon does happens afterwards, so with no attachment compat loaded (or with the
 * setting off) the panel behaves exactly as stock.
 *
 * Arguments:
 * 0: Right panel control <CONTROL>
 * 1: Selected index <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_control", "_curSel"];

[_control, _curSel] call ace_arsenal_fnc_onSelChangedRight;

[ctrlParent _control] call FUNC(refreshOptions);
