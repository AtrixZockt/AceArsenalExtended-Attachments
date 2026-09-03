class Extended_PreStart_EventHandlers {
    class ADDON {
        init = QUOTE(call COMPILE_FILE(XEH_preStart));
    };
};
// Deliberately no Extended_PostInit_EventHandlers: CBA never runs postInit in the
// Eden Editor -- only preInit, via cba_xeh_fnc_initDisplay3DEN -- so anything
// registered there would be dead in the editor. Every hook lives in XEH_preInit.sqf.
class Extended_PreInit_EventHandlers {
    class ADDON {
        init = QUOTE(call COMPILE_FILE(XEH_preInit));
    };
};
