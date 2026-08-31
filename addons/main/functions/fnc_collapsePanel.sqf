#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Collapse the right panel so each grouped model occupies one row.
 *
 * Runs synchronously inside ace_arsenal_rightPanelFilled, before ACE sorts the panel
 * and restores the selection -- see the note in fnc_onRightPanelFilled for why that
 * ordering matters. The list already holds exactly the items valid for the selected
 * weapon and tab, because ACE has filtered by compatibleItems or by compatible
 * magazines before raising the event.
 *
 * Which row survives a group is decided by the equipped item, not by the listbox:
 * ACE has cleared the selection by this point, and even after it restores one, the
 * row it lands on is not reliably the equipped variant. fnc_equippedItem has the
 * detail. Where the equipped class has no row of its own, the surviving row is
 * rewritten to BE that class, so ACE's restore finds it -- the same reconciliation
 * ACEAX does on the left in aceax_arsenal_fnc_onLeftPanelFilled.
 *
 * Collapsing the LIST rather than ace_arsenal_virtualItems is the whole design:
 * compatibility is per weapon, so a representative chosen once and globally might
 * not fit the weapon currently selected, and the entire family would vanish from
 * the list. It also means no ACE or ACEAX global is ever written.
 *
 * Attachments and magazines differ only in which config root the rows come from,
 * which fnc_currentPanelRoot answers.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 *
 * Return Value:
 * None
 */

params ["_display"];

GVAR(allowedItems) = createHashMap;
GVAR(collapsed) = false;

// Logged FIRST, before any early exit. The previous version logged after the
// "too few rows" guard, so when a broken control reported zero rows the whole
// pass produced no output at all -- which made a config bug look like a silent
// script that never ran.
private _debug = missionNamespace getVariable [QGVAR(debug), false];
private _ctrl = _display displayCtrl IDC_rightTabContent;
private _size = lbSize _ctrl;
private _root = call FUNC(currentPanelRoot);

// What is actually fitted to this slot. Logged rather than lbCurSel, which ACE has
// cleared to -1 by this point in the fill and would say nothing.
private _equipped = call FUNC(equippedItem);

if (_debug) then {
    diag_log format ["[aceaxatt] collapse: root=%1 leftPanel=%2 rightPanel=%3 rows=%4 equipped=%5 ctrlNull=%6 ctrlType=%7 enabled=%8",
        _root,
        missionNamespace getVariable ["ace_arsenal_currentLeftPanel", "nil"],
        missionNamespace getVariable ["ace_arsenal_currentRightPanel", "nil"],
        _size, _equipped, isNull _ctrl, ctrlType _ctrl,
        missionNamespace getVariable [QGVAR(enabled), true]];
};

if !(missionNamespace getVariable [QGVAR(enabled), true]) exitWith {};
if (_root == "") exitWith {};
if (_size < 2) exitWith { GVAR(collapsed) = true };

// The model the equipped item belongs to. Only that group needs a row chosen for
// it; every other group is free to keep whichever row came first.
private _equippedModel = if (_equipped != "") then {
    [_root, _equipped] call GEARINFO(getConfigModel)
} else {
    ""
};

// Bucket the rows by model. Rows with no data (ACE's "<empty>" entry) and rows
// whose class has no XtdGearInfo are left alone -- an unmapped item keeps its
// own row, exactly as it does without this addon.
//
// Written with nested ifs rather than `continue`: ACE only ever uses `continue`
// inside forEach, and there is no reason to find out the hard way whether it
// behaves in a `for..do`.
private _rowsOfModel = createHashMap;

for "_i" from 0 to (_size - 1) do {
    private _class = _ctrl lbData _i;

    if (_class != "") then {
        private _model = [_root, _class] call GEARINFO(getConfigModel);
        private _note = "";

        // An XtdGearInfo naming a model that was never defined is broken compat
        // data. Grouping on it would merge rows behind an option panel that cannot
        // be built, so those rows are left alone instead -- same treatment as an
        // item with no XtdGearInfo at all.
        //
        // Our own generator cannot emit this, but the addon is published for other
        // people's compats and their data never passes through tools/verify.py.
        if (_model != "" && {!isClass (configFile >> "XtdGearModels" >> _root >> _model)}) then {
            _note = " -- NO XtdGearModels class, left ungrouped";
            _model = "";
        };

        if (_model != "") then {
            (_rowsOfModel getOrDefault [_model, [], true]) pushBack _i;
            (GVAR(allowedItems) getOrDefault [_model, [], true]) pushBack _class;
        };

        if (_debug) then {
            diag_log format ["[aceaxatt]   row %1: %2 -> %3%4", _i, _class, _model, _note];
        };
    };
};

private _doomed = [];

{
    private _model = _x;
    private _rows = _y;

    private _keep = _rows select 0;

    // The equipped item's group is the one that has to survive as the equipped
    // variant -- anything else and the panel describes a scope the weapon is not
    // wearing, while ACE's restore either highlights the wrong row or gives up and
    // falls back to <empty>.
    //
    // Deliberately outside the "more than one row" test below: a family with a single
    // compatible variant still has to be reconciled, and it is not collapsing that
    // makes it necessary.
    if (_model == _equippedModel) then {
        private _match = _rows select { (_ctrl lbData _x) == _equipped };

        if (_match isNotEqualTo []) then {
            _keep = _match select 0;
        } else {
            // No row of its own: ACE listed the family under a different class of the
            // same model. Make the survivor BE the equipped variant instead of deleting
            // it -- ACE then matches it on lbData, and refreshOptions reads the right
            // values off it. Same four calls as fnc_changeCurrentConfig, and the same
            // fix ACEAX applies on the left.
            private _config = configFile >> _root >> _equipped;
            private _displayName = getText (_config >> "displayName");

            _ctrl lbSetData    [_keep, _equipped];
            _ctrl lbSetText    [_keep, _displayName];
            _ctrl lbSetTooltip [_keep, format ["%1\n%2", _displayName, _equipped]];
            _ctrl lbSetPicture [_keep, getText (_config >> "picture")];

            // The row's old class went into allowedItems during the bucketing pass,
            // but the one now on it did not. Without this, changeCurrentConfig's
            // membership guard would refuse to switch back to the equipped variant.
            (GVAR(allowedItems) getOrDefault [_model, [], true]) pushBackUnique _equipped;

            if (_debug) then {
                diag_log format ["[aceaxatt]   row %1 rewritten to equipped %2", _keep, _equipped];
            };
        };
    };

    // A model with one row here is not a group; nothing to collapse.
    if (count _rows > 1) then {
        {
            if (_x != _keep) then { _doomed pushBack _x };
        } forEach _rows;
    };
} forEach _rowsOfModel;

if (_debug) then {
    { diag_log format ["[aceaxatt]   group %1 -> rows %2", _x, _y]; } forEach _rowsOfModel;
    diag_log format ["[aceaxatt] collapse: deleting %1 of %2 rows", count _doomed, _size];
};

// There is deliberately no "too many rows removed" guard here.
//
// This used to refuse when a pass wanted to remove more than half the list, on the
// theory that such a pass had misidentified something. That premise is wrong, and it
// shipped: once the Tier One grouping data improved, a correct collapse of 159 of 289
// rows crossed the line and the addon switched itself off -- nothing merged at all.
//
// No threshold can work, because a correct collapse routinely removes almost
// everything. Select a weapon that only takes Micro T-2 variants and the panel goes
// from 32 rows to 1 -- 97% -- which is exactly what a compat is for. Meanwhile a
// genuine "every class resolved to one model" fault sits at 99.7%, above any bound
// loose enough to allow the legitimate case. The ratio simply does not carry the
// signal.
//
// What protects the panel instead is structural: a row is only ever removed when it
// resolves to the same model as a row that stays, and that model comes from authored
// XtdGearInfos data rather than from anything inferred here. Bad groupings are caught
// offline by gen_aceax.py --check and tools/verify.py, and a model with no definition
// is skipped above.
if (count _doomed >= _size) exitWith {
    // Cannot happen -- every group keeps one row -- so if it does, the bucketing
    // above is broken and an un-collapsed list is the better failure.
    ERROR_2("collapse would remove %1 of %2 rows, leaving none -- refusing, panel left intact",count _doomed,_size);
    GVAR(allowedItems) = createHashMap;
};

// Highest index first, so the lower ones stay valid as rows disappear.
_doomed sort false;
{ _ctrl lbDelete _x } forEach _doomed;

private _after = lbSize _ctrl;
if (_after != _size - (count _doomed)) then {
    ERROR_3("row count wrong after collapse: %1 rows minus %2 deleted should be %3",_size,count _doomed,_after);
};

GVAR(collapsed) = true;
