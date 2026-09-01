#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Bring the right-hand option panel in line with whatever is selected.
 *
 * Idempotent: the controls are only rebuilt when the selected model changes, which
 * is what makes it safe to call from both onSelChangedRight and the deferred pass
 * in onRightPanelFilled.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: Called from a selection change, so the listbox row leads the equipment rather
 *    than following it <BOOL> (default: false)
 *
 * Return Value:
 * None
 */

params ["_display", ["_fromSelection", false]];

private _model = "";
private _class = "";
private _root = call FUNC(currentPanelRoot);

// GVAR(collapsed) is false when the collapse did not run -- the addon is switched
// off, the panel is not one it handles, or fnc_collapsePanel bailed. Offering
// dropdowns over a list that still holds every duplicate would be worse than
// offering none, so the panel stays down.
if (missionNamespace getVariable [QGVAR(enabled), true]
    && {GVAR(collapsed)}
    && {_root != ""}) then {

    private _ctrl = _display displayCtrl IDC_rightTabContent;

    // Which of the row and the weapon to believe depends on how we got here, and the
    // caller is the only one that knows.
    //
    // After a REFILL the row can disagree with the weapon -- ACE's baseWeapon
    // normalisation lands on a sibling variant, or its match fails and it falls back
    // to <empty> -- and there the weapon is right. See fnc_equippedItem.
    //
    // After a CLICK it is the other way round. ACE equips the clicked row's data
    // verbatim (ace_arsenal_fnc_onSelChangedRight: `_item = _control lbData _curSel`),
    // so the row is by definition what is about to be on the weapon, no matter which
    // handler runs first. currentItems meanwhile still holds the PREVIOUS attachment,
    // because ACE does not write it until the end of its own handler. Reading it here
    // is what left the panel one click behind.
    if (!_fromSelection) then {
        _class = call FUNC(equippedItem);
    };

    // Also the fallback for the compatible-ammunition tabs, which have no equipped
    // slot. "" is ACE's <empty> row, which unequips rather than selecting an item,
    // and correctly leaves the panel down.
    if (_class == "") then {
        private _curSel = lbCurSel _ctrl;

        if (_curSel >= 0) then {
            _class = _ctrl lbData _curSel;
        };
    };

    if (_class != "") then {
        _model = [_root, _class] call GEARINFO(getConfigModel);
    };
};

// Every function below reads the root back from here rather than re-deriving it.
// Re-deriving would be wrong as well as wasteful: changeCurrentConfig runs from a
// button click, by which point the panel could in principle have moved on, and the
// model it is working with belongs to whichever root produced it.
GVAR(currentRoot) = _root;

if (_model != GVAR(currentModel)) then {
    [_display, _model] call FUNC(generateOptionsUI);
    GVAR(currentModel) = _model;
};

if (_model == "") exitWith {
    GVAR(currentModelOptions) = [];
};

GVAR(currentModelOptions) = [_root, _class, _model] call GEARINFO(getConfigOptions);

[_display] call FUNC(refreshCheckboxes);
