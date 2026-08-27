#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Collapse the right panel so each grouped model occupies one row.
 *
 * Runs on ace_arsenal_rightPanelFilled, which ACE raises at the end of
 * fnc_fillRightPanel once the list is built and ace_arsenal_currentRightPanel is
 * set, but BEFORE it restores the previous selection.
 *
 * Why post-process the listbox instead of filtering ace_arsenal_virtualItems the
 * way ACEAX does for the left panel: attachment compatibility is per weapon. ACE
 * fills this list from `compatibleItems _weapon` and only uses virtualItems as a
 * membership test, so a representative chosen globally might not be compatible
 * with the weapon currently selected -- and the whole family would vanish. By the
 * time this runs, the list already holds exactly the attachments valid here.
 *
 * The side effect of that choice is that no ACEAX or ACE global is written, so
 * nothing outside this panel can be affected.
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

GVAR(allowedItems) = createHashMap;

// Always queue the refresh, including on the paths that collapse nothing.
// Switching from the optic tab to magazines has to tear the option panel down,
// and that only happens if refreshOptions runs and finds no model.
private _fnc_scheduleRefresh = {
    [{
        params ["_display"];
        if (!isNull _display) then { [_display] call FUNC(refreshOptions) };
    }, [_display]] call CBA_fnc_execNextFrame;
};

// The setting is registered in preInit; read it defensively in case something
// opens the arsenal before CBA has processed settings.
if !(missionNamespace getVariable [QGVAR(enabled), true]) exitWith { call _fnc_scheduleRefresh };

private _slot = call FUNC(currentSlot);
if (_slot isEqualTo []) exitWith { call _fnc_scheduleRefresh };
_slot params ["", "_equipped"];

private _ctrl = _display displayCtrl IDC_rightTabContent;
private _size = lbSize _ctrl;
if (_size < 2) exitWith { call _fnc_scheduleRefresh };

// Pass 1: bucket the rows by model. Rows with no data (ACE's "<empty>" entry) and
// rows whose class has no XtdGearInfo are left alone -- an unmapped attachment
// keeps its own row, exactly as today.
private _rowsOfModel = createHashMap;

for "_i" from 0 to (_size - 1) do {
    private _class = _ctrl lbData _i;
    if (_class == "") then { continue };

    private _model = ["CfgWeapons", _class] call GEARINFO(getConfigModel);
    if (_model == "") then { continue };

    (_rowsOfModel getOrDefault [_model, [], true]) pushBack _i;
    (GVAR(allowedItems) getOrDefault [_model, [], true]) pushBack _class;
};

// Pass 2: pick the survivor for each model.
private _doomed = [];

{
    private _rows = _y;
    if (count _rows < 2) then { continue };

    // Keep the equipped variant if it is in this group. ACE restores the previous
    // selection by searching the list for that exact class immediately after this
    // function returns, so removing its row would silently reset the selection to
    // "<empty>" and look like the attachment had been unequipped.
    private _keep = _rows select 0;

    if (_equipped != "") then {
        {
            if ((_ctrl lbData _x) == _equipped) exitWith { _keep = _x };
        } forEach _rows;
    };

    {
        if (_x != _keep) then { _doomed pushBack _x };
    } forEach _rows;
} forEach _rowsOfModel;

// Delete high indices first so the lower ones stay valid.
_doomed sort false;
{ _ctrl lbDelete _x } forEach _doomed;

// The selection has not been restored yet, so the option panel cannot be built
// from it here. ACE sets it moments later, which normally fires onSelChangedRight
// for us; this catches the case where the index does not actually change and the
// event therefore never fires.
call _fnc_scheduleRefresh;
