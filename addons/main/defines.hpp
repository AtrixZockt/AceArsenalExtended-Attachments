// Constants borrowed from ACE3's ace_arsenal (addons/arsenal/defines.hpp).
//
// They are copied rather than included because ACE ships binarised: there is no
// \z\ace\addons\arsenal\defines.hpp to #include at build time. Anything here that
// ACE ever renumbers has to be updated -- see TESTING.md for how that surfaces.

// pixelScale is NOT an engine-provided UI variable -- it is a macro ACE defines.
// Leaving it out ships the literal identifier into the config, where it evaluates
// as undefined and the panel lands in the wrong place.
#define pixelScale  0.25
#define GRID_W (pixelW * pixelGridNoUIScale * pixelScale)
#define GRID_H (pixelH * pixelGridNoUIScale * pixelScale)

// ---- panel controls -------------------------------------------------------
#define IDC_leftTabContent 13
#define IDC_rightTabContent 14

// ---- left panel buttons: which weapon the right panel is showing ----------
#define IDC_buttonPrimaryWeapon 2002
#define IDC_buttonHandgun 2004
#define IDC_buttonSecondaryWeapon 2006
#define IDC_buttonBinoculars 2020

// ---- right panel buttons: which attachment slot --------------------------
#define IDC_buttonOptic 22
#define IDC_buttonItemAcc 24
#define IDC_buttonMuzzle 26
#define IDC_buttonBipod 28

// Order matters: ace_arsenal_fnc_onSelChangedRight indexes the weapon's item
// array with `[IDC_buttonMuzzle, IDC_buttonItemAcc, IDC_buttonOptic, IDC_buttonBipod] find _x`,
// so 0=muzzle, 1=pointer, 2=optic, 3=bipod. Keep this list in that order.
#define ATTACHMENT_SLOT_IDCS IDC_buttonMuzzle, IDC_buttonItemAcc, IDC_buttonOptic, IDC_buttonBipod

// ---- ace_arsenal_currentItems indices ------------------------------------
#define IDX_CURR_PRIMARY_WEAPON_ITEMS 18
#define IDX_CURR_SECONDARY_WEAPON_ITEMS 19
#define IDX_CURR_HANDGUN_WEAPON_ITEMS 20
#define IDX_CURR_BINO_ITEMS 21

// Same order as the IDX_CURR_*_ITEMS block above, which is what lets
// fnc_currentSlot turn a left-panel IDC into an index by position.
#define WEAPON_PANEL_IDCS IDC_buttonPrimaryWeapon, IDC_buttonSecondaryWeapon, IDC_buttonHandgun, IDC_buttonBinoculars

// ---------------------------------------------------------------------------
// IDC allocation
//
// ACEAX's own option UI is live at the same time as ours -- a grouped weapon can
// be selected on the left while a grouped optic is selected on the right -- so the
// two blocks must not overlap. ACEAX occupies roughly 9900000..10030002:
//
//     configControl  9990000, titles 9990001 / 9990002
//     option titles  shift + 9980000 + optionIndex
//     value controls shift + 9900000 + optionIndex*1000 + valueIndex*4
//     shift          0 for "options", 40000 for "textureoptions"
//
// Ours sits below it at 9600000..9730002 and has no textureoptions shift, because
// an attachment is not worn and cannot carry texture options.
// ---------------------------------------------------------------------------
#define IDC_optionsGroup 9690000
#define IDC_optionsLabel 9690001
#define IDC_optionsAuthor 9690002

#define IDC_OPTION_TITLE_BASE 9680000
#define IDC_OPTION_VALUE_BASE 9600000
