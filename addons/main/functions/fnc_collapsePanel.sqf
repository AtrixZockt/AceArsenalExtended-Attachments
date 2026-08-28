#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Collapse the right panel so each grouped model occupies one row.
 *
 * Runs a frame after ace_arsenal_rightPanelFilled, once ACE has finished sorting
 * the panel and restoring the selection. At that point the list holds exactly the
 * attachments valid for the selected weapon and slot -- ACE has already filtered by
 * compatibleItems -- so collapsing here needs no knowledge of the weapon at all.
 *
 * Collapsing the LIST rather than ace_arsenal_virtualItems is the whole design:
 * attachment compatibility is per weapon, so a representative chosen once and
 * globally might not fit the weapon currently selected, and the entire family would
 * vanish from the list. It also means no ACE or ACEAX global is ever written.
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
private _slot = call FUNC(currentSlot);

if (_debug) then {
    diag_log format ["[aceaxatt] collapse: slot=%1 leftPanel=%2 rightPanel=%3 rows=%4 selected=%5 ctrlNull=%6 ctrlType=%7 enabled=%8",
        _slot,
        missionNamespace getVariable ["ace_arsenal_currentLeftPanel", "nil"],
        missionNamespace getVariable ["ace_arsenal_currentRightPanel", "nil"],
        _size, lbCurSel _ctrl, isNull _ctrl, ctrlType _ctrl,
        missionNamespace getVariable [QGVAR(enabled), true]];
};

if !(missionNamespace getVariable [QGVAR(enabled), true]) exitWith {};
if (_slot < 0) exitWith {};
if (_size < 2) exitWith { GVAR(collapsed) = true };

// ACE has already restored the selection, so this is the equipped attachment.
// Keeping its row is what stops the selection falling back to <empty> and looking
// like the attachment came off.
private _selected = lbCurSel _ctrl;

// Bucket the rows by model. Rows with no data (ACE's "<empty>" entry) and rows
// whose class has no XtdGearInfo are left alone -- an unmapped attachment keeps its
// own row, exactly as it does without this addon.
//
// Written with nested ifs rather than `continue`: ACE only ever uses `continue`
// inside forEach, and there is no reason to find out the hard way whether it
// behaves in a `for..do`.
private _rowsOfModel = createHashMap;

for "_i" from 0 to (_size - 1) do {
    private _class = _ctrl lbData _i;

    if (_class != "") then {
        private _model = ["CfgWeapons", _class] call GEARINFO(getConfigModel);
        private _note = "";

        // An XtdGearInfo naming a model that was never defined is broken compat
        // data. Grouping on it would merge rows behind an option panel that cannot
        // be built, so those rows are left alone instead -- same treatment as an
        // attachment with no XtdGearInfo at all.
        //
        // Our own generator cannot emit this, but the addon is published for other
        // people's compats and their data never passes through tools/verify.py.
        if (_model != "" && {!isClass (configFile >> "XtdGearModels" >> "CfgWeapons" >> _model)}) then {
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
    private _rows = _y;

    // A model with one row here is not a group; nothing to collapse.
    if (count _rows > 1) then {
        private _keep = if (_selected in _rows) then { _selected } else { _rows select 0 };

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
