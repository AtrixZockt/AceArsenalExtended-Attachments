#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * ace_arsenal_rightPanelFilled -- collapse the list, then refresh the options.
 *
 * The two halves run at different times, and the split is the point.
 *
 * ACE raises this event partway through fnc_fillRightPanel: the list is built, but
 * it then goes on to sort the panel and to restore the selection by matching the
 * equipped class against each row's lbData.
 *
 * The COLLAPSE runs here, synchronously, before any of that. Deleting rows while
 * ACE still has the selection cleared means ACE performs its restore against the
 * already-collapsed list and picks the surviving row itself -- so the addon never
 * has to move the selection, and never has to call lbSetCurSel (which would fire
 * ACE's onSelChangedRight and re-add a magazine).
 *
 * This is the hook point ACEAX uses on the left panel for the same reason:
 * aceax_arsenal_fnc_onLeftPanelFilled reconciles rows during the fill event, and
 * ACE's restore loop runs afterwards.
 *
 * An earlier version deferred both halves by a frame. That put the collapse AFTER
 * ACE's restore, so deleting rows shifted the selection out from under it -- the
 * weapon kept the right attachment while the panel showed a different one.
 *
 * The REFRESH still waits a frame. It works from the equipped item, which is already
 * correct here, but it falls back to lbCurSel for the panels that have no equipped
 * slot -- the compatible-ammunition tabs -- and ACE has not restored the selection
 * yet at this point in the fill.
 *
 * It is also deliberately NOT told the selection is leading: on a refill the row can
 * disagree with the weapon, and there the weapon wins. See fnc_refreshOptions.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: Current left panel IDC <NUMBER>
 * 2: Current right panel IDC <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_display"];

[_display] call FUNC(collapsePanel);

[{
    params ["_display"];
    if (isNull _display) exitWith {};

    [_display] call FUNC(refreshOptions);
}, [_display]] call CBA_fnc_execNextFrame;
