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

// ---- the arsenal display itself -------------------------------------------
#define IDD_ace_arsenal 1127001

// ---- panel controls -------------------------------------------------------
#define IDC_leftTabContent 13
#define IDC_rightTabContent 14

// The right panel's two sort combos. Both run ACE's sortPanel, which uses each
// row's right-hand text as a hidden sort key and clears it afterwards -- so a
// sort wipes the model labels fnc_labelPanel writes there.
#define IDC_sortRightTab 17
#define IDC_sortRightTabDirection 171

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

// ---- right panel buttons: the four ammunition tabs -----------------------
//
// All four list CfgMagazines classes, which is the only thing this addon needs
// of them -- unlike the attachment list above, nothing indexes this one by
// position, so the order carries no meaning and is free to change.
#define IDC_buttonCurrentMag 3002   // magazines for the selected weapon
#define IDC_buttonCurrentMag2 3004  // the secondary muzzle's, e.g. an underbarrel GL
#define IDC_buttonMag 30
#define IDC_buttonMagALL 32
#define MAGAZINE_SLOT_IDCS IDC_buttonCurrentMag, IDC_buttonCurrentMag2, IDC_buttonMag, IDC_buttonMagALL

// The panels that have a single equipped item, in ACE's order. ACE looks up a
// weapon's items array with
// `[IDC_buttonMuzzle, IDC_buttonItemAcc, IDC_buttonOptic, IDC_buttonBipod, IDC_buttonCurrentMag, IDC_buttonCurrentMag2] find _ctrlIDC`
// (fnc_fillRightPanel), so position IS the index into that array. fnc_equippedItem
// depends on it; keep it in this order.
//
// IDC_buttonMag and IDC_buttonMagALL are deliberately absent. They list ammunition
// compatible with the weapon rather than the contents of a slot, so there is no
// equipped item to read and the listbox row is the only thing to go on.
#define EQUIPPED_SLOT_IDCS ATTACHMENT_SLOT_IDCS, IDC_buttonCurrentMag, IDC_buttonCurrentMag2

// Deliberately NOT handled: IDC_buttonThrow (34) and IDC_buttonPut (36), the
// grenade and explosive tabs. They are CfgMagazines too and would need only a
// third list here, but the toolchain does not generate data for them -- see
// modconfig._magazine_kind -- so listing them would collapse nothing while
// making the addon claim a panel it does nothing with.

// ---- ace_arsenal_currentItems indices ------------------------------------
#define IDX_CURR_PRIMARY_WEAPON_ITEMS 18
#define IDX_CURR_SECONDARY_WEAPON_ITEMS 19
#define IDX_CURR_HANDGUN_WEAPON_ITEMS 20
#define IDX_CURR_BINO_ITEMS 21

// Same order as the IDX_CURR_*_ITEMS block above, so a left-panel IDC turns into
// an index into ace_arsenal_currentItems by position -- the four indices are
// contiguous, so the position simply adds to IDX_CURR_PRIMARY_WEAPON_ITEMS.
//
// fnc_equippedItem reads this together with EQUIPPED_SLOT_IDCS to answer "what is
// actually on the weapon", which is what the panel is driven from. An earlier
// version worked purely off what ACE had put in the listbox; that is what let the
// row and the weapon disagree after a refill. Both orders are load-bearing.
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
