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
 *
 * Return Value:
 * None
 */

params ["_display"];

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

    // The equipped item first, not the row. The two can disagree -- see
    // fnc_equippedItem -- and when they do it is the weapon that is right; showing
    // the row instead is what made the panel tick the wrong variant after a refill.
    // ACEAX reads the left panel the same way round (fnc_onSelChangedLeft).
    //
    // Safe on the click path too: ACE's config-defined onLBSelChanged runs before
    // handlers added with ctrlAddEventHandler, so by the time fnc_onSelChangedRight
    // gets here ACE has equipped the clicked item and currentItems is current.
    _class = call FUNC(equippedItem);

    // The compatible-ammunition tabs have no equipped slot, so the row is all there
    // is to go on. "" is also ACE's <empty> row, which unequips rather than
    // selecting an item, and correctly leaves the panel down.
    if (_class == "") then {
        private _ctrl = _display displayCtrl IDC_rightTabContent;
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
