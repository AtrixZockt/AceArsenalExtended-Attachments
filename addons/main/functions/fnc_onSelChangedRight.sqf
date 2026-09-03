#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Scripted LBSelChanged handler for the arsenal's right panel.
 *
 * Attached with ctrlAddEventHandler in XEH_preInit, which ADDS to the control's
 * config-defined onLBSelChanged rather than replacing it. ACE's handler equips the
 * item, updates the weight readout and raises ace_arsenal_weaponItemChanged; nothing
 * here repeats any of that -- and it must not, or magazines would be added twice.
 *
 * Do NOT assume ACE's handler has already run when this one does. Which of the two
 * the engine calls first is not something this addon should depend on, and an earlier
 * version that did read ace_arsenal_currentItems here showed the panel for the
 * PREVIOUS attachment until you clicked a second time.
 *
 * Hence the `true`: on a click the listbox leads the equipment rather than
 * following it. ACE equips the clicked row's data verbatim, so the row is what is
 * about to be on the weapon whichever order the handlers run in.
 *
 * The other branch is not a click at all. ACE ends fnc_fillRightPanel by restoring
 * the selection, which fires this handler -- and in the Eden Editor that is the only
 * chance the deferred half of a fill ever gets, because nothing deferred runs there
 * (fnc_onRightPanelFilled has the detail). GVAR(edenPending) is set by the fill and
 * only ever in 3DEN, so it says "this selection change IS the end of a fill".
 *
 * That distinction is worth having rather than labelling on every selection change:
 *
 *   - a refill wants the WEAPON to lead, not the row, which is what the missing
 *     `true` means -- the same answer the deferred pass reaches in a mission;
 *   - ACE's fnc_sortPanel calls lbSetCurSel from INSIDE the loop that clears each
 *     row's right-hand text, so labelling from an unguarded selection handler would
 *     write every row and then have everything below the selected one wiped by the
 *     rest of that loop. A flag only the fill sets never lands mid-sort.
 *
 * Reading ace_arsenal_currentItems via refreshOptions is safe on THAT path despite
 * the warning above: ACE's restore selects the row that is already equipped, so its
 * handler re-equips the same class and currentItems reads the same either way. The
 * warning still stands for the click branch, which is why it still passes `true`.
 *
 * Arguments:
 * 0: Right panel control <CONTROL>
 * 1: Selected index <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_control"];

private _display = ctrlParent _control;

if (GVAR(edenPending)) then {
    GVAR(edenPending) = false;

    [_display] call FUNC(refreshOptions);
    [_display] call FUNC(labelPanel);
} else {
    [_display, true] call FUNC(refreshOptions);
};
