#include "script_component.hpp"

// Registered in postInit, which runs after every addon's preInit, so this
// handler is guaranteed to fire after ACEAX's own rightPanelFilled handler
// regardless of addon load order.
//
// ACE raises this at the end of ace_arsenal_fnc_fillRightPanel, after the list
// has been filled and ace_arsenal_currentRightPanel has been set, but BEFORE it
// restores the previous selection. Collapsing here is what lets the selection
// restore still find the equipped attachment -- see fnc_onRightPanelFilled.
["ace_arsenal_rightPanelFilled", {
    _this call FUNC(onRightPanelFilled);
}] call CBA_fnc_addEventHandler;

// Nothing is grouped once the arsenal is gone; drop the state so a stale model
// cannot leak into the next session.
["ace_arsenal_displayClosed", {
    GVAR(currentModel) = "";
    GVAR(currentModelOptions) = [];
    GVAR(valuesIdc) = [];
    GVAR(idcToConfig) = createHashMap;
    GVAR(allowedItems) = createHashMap;
}] call CBA_fnc_addEventHandler;
