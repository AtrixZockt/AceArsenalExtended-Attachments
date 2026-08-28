#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Scripted LBSelChanged handler for the arsenal's right panel.
 *
 * Attached with ctrlAddEventHandler in XEH_postInit, which ADDS to the control's
 * config-defined onLBSelChanged rather than replacing it. ACE's own handler has
 * therefore already run by the time this does: the item is equipped, the weight
 * readout is updated and ace_arsenal_weaponItemChanged has fired. Nothing here
 * needs to repeat any of that -- and it must not, or magazines would be added
 * twice.
 *
 * Arguments:
 * 0: Right panel control <CONTROL>
 * 1: Selected index <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_control"];

[ctrlParent _control] call FUNC(refreshOptions);
