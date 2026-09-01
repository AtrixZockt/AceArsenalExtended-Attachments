#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Scripted LBSelChanged handler for the arsenal's right panel.
 *
 * Attached with ctrlAddEventHandler in XEH_postInit, which ADDS to the control's
 * config-defined onLBSelChanged rather than replacing it. ACE's handler equips the
 * item, updates the weight readout and raises ace_arsenal_weaponItemChanged; nothing
 * here repeats any of that -- and it must not, or magazines would be added twice.
 *
 * Do NOT assume ACE's handler has already run when this one does. Which of the two
 * the engine calls first is not something this addon should depend on, and an earlier
 * version that did read ace_arsenal_currentItems here showed the panel for the
 * PREVIOUS attachment until you clicked a second time.
 *
 * Hence the `true`: on this path the listbox leads the equipment rather than
 * following it. ACE equips the clicked row's data verbatim, so the row is what is
 * about to be on the weapon whichever order the handlers run in.
 *
 * Arguments:
 * 0: Right panel control <CONTROL>
 * 1: Selected index <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_control"];

[ctrlParent _control, true] call FUNC(refreshOptions);
