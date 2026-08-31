#include "script_component.hpp"
#include "defines.hpp"

// Hook the right panel's selection event at RUNTIME rather than in config.
//
// ctrlAddEventHandler adds a handler alongside the control's config-defined
// onLBSelChanged; it does not replace it (that is ctrlSetEventHandler). So ACE's
// own handler still runs and still equips the item, and this one runs afterwards
// purely to rebuild the option panel.
//
// The alternative -- patching `class rightTabContent` in config -- is what broke
// the panel entirely the first time round: re-declaring an existing class without
// restating its parent resets that parent, and the control lost its listbox type.
// Attaching at runtime touches no ACE class at all, so it cannot break inheritance
// and cannot fight another addon hooking the same control.
["ace_arsenal_displayOpened", {
    params ["_display"];

    private _ctrl = _display displayCtrl IDC_rightTabContent;

    // 5 is CT_LISTBOX. A null control, or one that is not a listbox, means
    // something has broken rightTabContent -- most likely an addon patching it in
    // config without restating its parent. Naming it here turns a silently blank
    // panel into one line in the RPT.
    if (isNull _ctrl) exitWith {
        ERROR("rightTabContent (idc 14) not found -- attachment merging disabled for this session");
    };

    if (ctrlType _ctrl != 5) exitWith {
        ERROR_1("rightTabContent is not a listbox (ctrlType %1) -- another addon has probably reset its base class; attachment merging disabled for this session",ctrlType _ctrl);
    };

    _ctrl ctrlAddEventHandler ["LBSelChanged", {
        _this call FUNC(onSelChangedRight);
    }];
}] call CBA_fnc_addEventHandler;

// Registered in postInit, which runs after every addon's preInit, so this handler
// is guaranteed to fire after ACEAX's own rightPanelFilled handler regardless of
// addon load order.
//
// ACE raises this partway through fnc_fillRightPanel: the list is built, but it
// then goes on to sort the panel and restore the selection. The work is deferred
// by a frame so all of that has finished -- see fnc_onRightPanelFilled.
["ace_arsenal_rightPanelFilled", {
    _this call FUNC(onRightPanelFilled);
}] call CBA_fnc_addEventHandler;

// ---------------------------------------------------------------------------
// Hide the option panel whenever ACE hides the arsenal.
//
// ace_arsenal_fnc_buttonHide ctrlShows a hardcoded list of ACE's own IDCs, so it
// never touches ours -- without these the panel floats on top of the loadouts
// screen. See fnc_toggleUI.
// ---------------------------------------------------------------------------
["ace_arsenal_loadoutsDisplayOpened", { [false] call FUNC(toggleUI); }] call CBA_fnc_addEventHandler;
["ace_arsenal_loadoutsDisplayClosed", { [true] call FUNC(toggleUI); }] call CBA_fnc_addEventHandler;

// Also covers the Hide button (idc 1002) and its BACKSPACE keybind, which the
// two events above miss -- buttonHide is called from all three places.
//
// Newer ACE than the loadouts events (added 2026-02-12, ACE #11285), so it is an
// addition to them rather than a replacement: on an older ACE it simply never
// fires and the loadouts case is still handled. On the loadouts path both fire;
// that is harmless, since they set the same state and ctrlShow is idempotent.
["ace_arsenal_showToggle", {
    params ["", "_show"];
    [_show] call FUNC(toggleUI);
}] call CBA_fnc_addEventHandler;

// Nothing is grouped once the arsenal is gone; drop the state so a stale model
// cannot leak into the next session.
["ace_arsenal_displayClosed", {
    GVAR(currentModel) = "";
    GVAR(currentRoot) = "";
    GVAR(currentModelOptions) = [];
    GVAR(valuesIdc) = [];
    GVAR(idcToConfig) = createHashMap;
    GVAR(allowedItems) = createHashMap;
    GVAR(collapsed) = false;
    // Closing the arsenal from the loadouts screen leaves this set. Without the
    // reset the panel would stay hidden for the rest of the session, because
    // nothing raises a show event on the way back in.
    GVAR(uiHidden) = false;
}] call CBA_fnc_addEventHandler;
