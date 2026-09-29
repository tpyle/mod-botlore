#!/usr/bin/env python3
"""Combinatorial layers for the mod-botlore corpus.

gen_bot_lore.py holds the hand-written, hand-placed lines: this zone, that
quest, that boss. It tops out in the high hundreds, because every line is
authored individually.

This file is the other half. It authors *fragments* along the axes the module
can actually filter on - class, archetype, race, gender, spec, item category -
and multiplies them out. Two complete sentences joined with a space stay
grammatical, so an object observation plus an archetype reaction gives a line
neither fragment was written to be:

    "A two-handed hammer. Heavy work, and honest work."   (item class 2/5)
  + "The Light gave it into my hands. I will not waste it." (devout)
  = one line, filtered to devout plate-wearers looting a two-handed mace.

That is where the thousands come from, and why the result is not repetitive:
each line carries the full filter set of both fragments, so a given bot only
ever draws from the slice that fits who it is.

Imported and driven by gen_bot_lore.py, which injects its own line()/many()
and constants so both halves append to the same row list.
"""


def build(ns):
    globals().update(ns)

    # ======================================================================
    # Archetype reactions to acquiring something. Each is a standalone
    # sentence that reads correctly after any object observation below.
    # ======================================================================
    REACT = {
        DEVOUT: [
            "The Light gave it into my hands. I will not waste it.",
            "I will bless it before I bleed with it.",
            "Gifts arrive when they are needed, never when they are wanted.",
            "I will carry it humbly. That is the whole of the discipline.",
        ],
        GRIM: [
            "It will last until it does not. So will I.",
            "Good. That is one less excuse.",
            "I do not need it to be fine. I need it to hold.",
            "Everything I own is borrowed from the next corpse.",
        ],
        SCHOLAR: [
            "The craftsmanship tells you where it was made, if you can read it.",
            "I will note the weight and the balance before I trust it.",
            "Someone thought hard about this. I would like to know who.",
            "Every object is a record of the hands that shaped it.",
        ],
        BOASTFUL: [
            "About time the spoils matched the deed.",
            "They will ask where I got it. I will take my time answering.",
            "Better than yours, and I say that kindly.",
            "This will look very well on me.",
        ],
        WRY: [
            "Well. The war improves my wardrobe if nothing else.",
            "Someone died disappointed about this. Thank them for me.",
            "I came for coin and I keep getting responsibilities.",
            "Not what I asked for. Better than what I expected.",
        ],
        HAUNTED: [
            "It was someone's before it was mine. I try not to wonder whose.",
            "I keep collecting things. None of them fill the hole.",
            "I will use it. I will not grow fond of it.",
            "Another thing to lose later.",
        ],
        SAVAGE: [
            "Good. It will break things.",
            "Enough talk. Let me test it on something that moves.",
            "I do not care how it looks. I care what it does to bone.",
            "Now the hunting gets easier.",
        ],
        SINISTER: [
            "How useful. And how little anyone will suspect.",
            "Everything is a tool. Some are merely honest about it.",
            "I will find a use for this its maker never intended.",
            "Mine now. Ask the previous owner if you doubt it.",
        ],
    }

    # ======================================================================
    # Item categories. (itemClass, itemSubClass, classes that plausibly use
    # it, observations). itemSubClass -1 means "any subclass of this class".
    #
    # Subclass numbers are ItemSubclassWeapon / ItemSubclassArmor from
    # ItemTemplate.h: weapon 0 axe, 1 axe2, 2 bow, 3 gun, 4 mace, 5 mace2,
    # 6 polearm, 7 sword, 8 sword2, 10 staff, 13 fist, 15 dagger, 16 thrown,
    # 18 crossbow, 19 wand; armour 0 misc, 1 cloth, 2 leather, 3 mail,
    # 4 plate, 6 shield, 7 libram, 8 idol, 9 totem, 10 sigil.
    # ======================================================================
    ALL_CLASSES = (WARRIOR | PALADIN | HUNTER | ROGUE | PRIEST | DEATH_KNIGHT
                   | SHAMAN | MAGE | WARLOCK | DRUID)

    CATEGORIES = [
        (2, 5, WARRIOR | PALADIN | DEATH_KNIGHT | SHAMAN | DRUID, [
            "A two-handed hammer. Heavy work, and honest work.",
            "A warhammer, the kind that does not care what armour you wore.",
            "This head weighs more than my first shield.",
            "A maul. No edge to keep and nothing to sharpen. Weight and intent.",
        ]),
        (2, 1, WARRIOR | PALADIN | HUNTER | DEATH_KNIGHT | SHAMAN, [
            "A greataxe. Crude, effective, and older than any argument about it.",
            "Two hands on the haft and nothing between you and the swing.",
            "The edge is as wide as my forearm.",
        ]),
        (2, 8, WARRIOR | PALADIN | HUNTER | DEATH_KNIGHT, [
            "A two-handed blade. Half my height of good steel.",
            "A greatsword. Ceremony on one side, butchery on the other.",
            "It needs both arms and a wide stance. Fair trade.",
        ]),
        (2, 6, WARRIOR | PALADIN | HUNTER | DEATH_KNIGHT | DRUID, [
            "A polearm. Reach is its own kind of armour.",
            "A halberd. Hook, spike and blade, for people who could not decide.",
            "Long enough to keep trouble at arm's length, and then some.",
        ]),
        (2, 10, WARRIOR | HUNTER | PRIEST | SHAMAN | MAGE | WARLOCK | DRUID, [
            "A staff. Plain wood, to anyone who cannot feel what runs through it.",
            "A focus, and a walking stick when nobody is looking.",
            "There is a pattern carved the length of the shaft. Old work.",
        ]),
        (2, 0, WARRIOR | PALADIN | HUNTER | ROGUE | DEATH_KNIGHT | SHAMAN, [
            "A hand axe. Nothing clever about it, which is rather the point.",
            "Balanced for one hand, and it bites.",
            "A woodsman's tool that found other employment.",
        ]),
        (2, 4, WARRIOR | PALADIN | ROGUE | PRIEST | DEATH_KNIGHT | SHAMAN | DRUID, [
            "A mace. For breaking what an edge only scratches.",
            "A flanged head. Cruel design, and an honest one.",
            "Heavy in the hand and heavier at the end of the swing.",
        ]),
        (2, 7, WARRIOR | PALADIN | HUNTER | ROGUE | DEATH_KNIGHT | MAGE | WARLOCK, [
            "A sword. One hand, and well balanced.",
            "The grip is worn to somebody else's palm. It will learn mine.",
            "Good steel, and the fuller is cut straight.",
        ]),
        (2, 15, WARRIOR | HUNTER | ROGUE | PRIEST | SHAMAN | MAGE | WARLOCK | DRUID, [
            "A dagger. Quiet, close and quick.",
            "A short blade. It ends conversations rather than starting them.",
            "It sits along the forearm without a whisper.",
        ]),
        (2, 13, WARRIOR | HUNTER | ROGUE | SHAMAN | DRUID, [
            "Claws, strapped to the fist. Someone meant this personally.",
            "Fist weapons. All the honesty of a brawl, with better results.",
            "Steel where knuckles were. I approve.",
        ]),
        (2, 2, WARRIOR | HUNTER | ROGUE, [
            "A bow. Yew, well seasoned, strung by someone who knew the work.",
            "The draw is heavier than it looks.",
            "A bow asks for patience and gives it back with interest.",
        ]),
        (2, 3, WARRIOR | HUNTER | ROGUE, [
            "A gun. Loud, dwarven and unarguable.",
            "Powder and shot. Crude next to a bowstring, and it does not care.",
            "Ironforge work, or a very good copy of it.",
        ]),
        (2, 18, WARRIOR | HUNTER | ROGUE, [
            "A crossbow. Draw once, then wait as long as you like.",
            "Mechanical patience. I can respect that.",
            "Heavier than a bow, and far less forgiving of the target.",
        ]),
        (2, 16, WARRIOR | HUNTER | ROGUE, [
            "Throwing blades, weighted properly, which is rarer than you think.",
            "A handful of steel for the moment before the charge.",
        ]),
        (2, 19, PRIEST | MAGE | WARLOCK, [
            "A wand. Barely a weapon, and it will still burn through plate.",
            "A channel, not a club. Try not to hit anyone with it.",
            "The core is still warm. That is either fine work or bad news.",
        ]),
        (4, 4, WARRIOR | PALADIN | DEATH_KNIGHT, [
            "Plate. Weight you learn to forget.",
            "Good plate, articulated at the elbow, which the cheap stuff never is.",
            "Somebody hammered this out over weeks. It shows.",
        ]),
        (4, 3, WARRIOR | PALADIN | HUNTER | SHAMAN | DEATH_KNIGHT, [
            "Mail. Thousands of rings, every one of them riveted by hand.",
            "It moves like cloth and stops like steel.",
            "Mail is a patient armourer's work.",
        ]),
        (4, 2, HUNTER | ROGUE | SHAMAN | DRUID, [
            "Leather, boiled hard and cut close.",
            "Supple enough to move in, thick enough to matter.",
            "Worked leather. Light, quiet, and it breathes.",
        ]),
        (4, 1, PRIEST | MAGE | WARLOCK, [
            "Cloth. Thread and enchantment, and nothing else between me and the world.",
            "Woven fine. The protection is not in the fabric.",
            "Light as a rumour. It will have to be enough.",
        ]),
        (4, 6, WARRIOR | PALADIN | SHAMAN, [
            "A shield. The most underrated weapon on any field.",
            "Boss and rim both sound. Whoever carried it kept it well.",
            "Heavy on the arm, and worth every pound of it.",
        ]),
        (4, 0, ALL_CLASSES, [
            "A ring, and there is more work in the band than in the stone.",
            "Small things carry the strongest enchantments. Nobody knows why.",
            "A trinket. Half of them are junk and half of them win fights.",
        ]),
        (4, 7, PALADIN, [
            "A libram. Scripture bound in silver, and it hums in the hand.",
            "The order keeps these locked away. I intend to use mine.",
        ]),
        (4, 8, DRUID, [
            "An idol. Carved from heartwood that was old before Kalimdor split.",
            "It smells of moss and rain. The Circle would approve.",
        ]),
        (4, 9, SHAMAN, [
            "A totem. The elements answer a little quicker through good work.",
            "The carving is ancestor work. I can feel who held it before me.",
        ]),
        (4, 10, DEATH_KNIGHT, [
            "A sigil. Runes that were cut by someone who understood the cost.",
            "It is cold, and it makes the blade colder. Good.",
        ]),
        (9, -1, ALL_CLASSES, [
            "A recipe, and a rare one. Someone will pay for a copy before the craft.",
            "Written by hand, and the hand was shaking. Interesting.",
        ]),
        (15, 5, ALL_CLASSES, [
            "A mount. I have walked enough of Azeroth to know what this is worth.",
            "I will not have to feel every mile of the next road.",
        ]),
    ]

    # Mirror of PersonalitiesForClass in mod_botlore.cpp. A line filtered to
    # both a class and an archetype is only reachable if that class can roll
    # that archetype, so the cross-product below intersects the two rather
    # than emitting rows no bot can ever match.
    CLASS_ARCHETYPES = {
        WARRIOR:      [BOASTFUL, GRIM, SAVAGE, WRY],
        PALADIN:       [DEVOUT, BOASTFUL, GRIM, HAUNTED],
        HUNTER:        [SAVAGE, WRY, SCHOLAR, GRIM],
        ROGUE:         [WRY, SINISTER, GRIM, SAVAGE],
        PRIEST:        [DEVOUT, HAUNTED, SCHOLAR, GRIM],
        DEATH_KNIGHT:  [GRIM, HAUNTED, SINISTER, SAVAGE],
        SHAMAN:        [SCHOLAR, DEVOUT, SAVAGE, HAUNTED],
        MAGE:          [SCHOLAR, WRY, BOASTFUL, SINISTER],
        WARLOCK:       [SINISTER, SCHOLAR, WRY, GRIM],
        DRUID:         [SCHOLAR, SAVAGE, DEVOUT, HAUNTED],
    }

    def classes_with(archetype):
        """Class mask of every class that can roll this archetype."""
        mask = 0
        for cls, archetypes in CLASS_ARCHETYPES.items():
            if archetype in archetypes:
                mask |= cls
        return mask

    def join(first, second):
        return f"{first} {second}"

    # ---------------------------------------------------------------- loot
    # Pass one: the observation alone, with no class or archetype filter, so
    # a mage who loots a greatsword still has something in character to say
    # about the object without claiming it will swing the thing.
    for iclass, isub, _users, observations in CATEGORIES:
        for obs in observations:
            line("loot_rare", obs, iclass=iclass, isub=isub, weight=2,
                 comment=f"item class {iclass}/{isub} observation")

    # Pass two: observation plus archetype reaction, restricted to the
    # classes that would actually carry the thing.
    for iclass, isub, users, observations in CATEGORIES:
        for archetype, reactions in REACT.items():
            cls_mask = users & classes_with(archetype)
            if not cls_mask:
                continue
            for obs in observations:
                for react in reactions:
                    line("loot_rare", join(obs, react), iclass=iclass,
                         isub=isub, cls=cls_mask, personality=archetype,
                         weight=2,
                         comment=f"item {iclass}/{isub} "
                                 f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Class voice. Four fragments per class per situation: what this class
    # is doing, thinking, or about to do. Every one is a whole sentence so
    # it can be followed by any archetype fragment underneath.
    # ======================================================================
    CLASS_IDLE = {
        WARRIOR: [
            "I sharpen in the evening. It keeps the hands busy and the head quiet.",
            "Every dent in this armour has a name attached to it.",
            "No magic and no prayers. Just the drill, until it is faster than thought.",
            "They train you to hold the line. Nobody trains you for afterwards.",
        ],
        PALADIN: [
            "The Light is not a weapon you draw. It is a thing you slowly become.",
            "I say the words each morning whether I feel them or not.",
            "Silver polish and scripture. That is most of the order's work, in truth.",
            "A paladin who fights more than they mend has misunderstood the vow.",
        ],
        HUNTER: [
            "Track, wait, breathe, release. The rest is noise.",
            "My beast eats before I do. That is not kindness, it is arithmetic.",
            "You learn more from the ground than from anyone who talks.",
            "Half of hunting is knowing when to go home.",
        ],
        ROGUE: [
            "The trick is being somewhere nobody thought to look.",
            "I count the exits in a room before I count the friends.",
            "Poisons want cool and dark. So do I, most days.",
            "Nobody writes songs about us. That is rather the arrangement.",
        ],
        PRIEST: [
            "Faith is mostly bookkeeping. Who needs mending, and in what order.",
            "I have held more hands at the end than I have raised in blessing.",
            "The Light and the Void both answer. That troubles me less than it should.",
            "Prayer is not asking. It is listening until you can bear the answer.",
        ],
        DEATH_KNIGHT: [
            "I remember being warm. I do not remember what it felt like.",
            "The Lich King made me an instrument. Acherus made me a problem.",
            "I do not sleep. I stand in the dark and let the hours pass through me.",
            "Every rune on this blade was cut into me first.",
        ],
        SHAMAN: [
            "The elements do not obey. They agree, when they are asked properly.",
            "Water is the hardest to bargain with. It has all the time in the world.",
            "I listen more than I speak. The wind has better material.",
            "My ancestors are not gone. They are simply quieter than they were.",
        ],
        MAGE: [
            "The arcane is a habit as much as a power. Skip a day and the hands forget.",
            "I have read three theories of the Nether and distrust all of them equally.",
            "The Kirin Tor teach you precision long before they teach you strength.",
            "Magic is only mathematics that bites back.",
        ],
        WARLOCK: [
            "It whispers even when I do not ask. That is the arrangement, not the flaw.",
            "I keep what I summoned on a short leash and a shorter memory.",
            "Everyone wants the power. Nobody reads the terms.",
            "Fel leaves a taste. You stop noticing, and that is the worrying part.",
        ],
        DRUID: [
            "The Dream is louder when I am tired. I have stopped fighting that.",
            "I have been bear and cat and bird today, and myself least of all.",
            "Cenarius taught balance, and balance is exhausting.",
            "Nature does not need us. It only needs us to stop.",
        ],
    }

    CLASS_COMBAT = {
        WARRIOR: [
            "Shield up. This is the part I was made for.",
            "Come on then. I have been hit by worse and I am still standing.",
            "Hold the line. Nothing gets past me while I can stand on it.",
        ],
        PALADIN: [
            "By the Light, stand down or be put down.",
            "I have a duty and you are standing in the middle of it.",
            "The Light shields me. Nothing you bring will change that.",
        ],
        HUNTER: [
            "Mark it. Range first, teeth second.",
            "My beast has your scent now. You will not shake it.",
            "I had you in my sights well before you saw me.",
        ],
        ROGUE: [
            "You should not have turned your back.",
            "Nothing personal. It is simply the arrangement.",
            "I have been behind you for a while now.",
        ],
        PRIEST: [
            "The Light will judge you. I am only the paperwork.",
            "I would rather have mended you. You chose otherwise.",
            "Shadow or Light, one of them ends this.",
        ],
        DEATH_KNIGHT: [
            "Your suffering will be legendary.",
            "The cold comes with me. Try to keep up.",
            "Death is a discipline, and I was taught by the best.",
        ],
        SHAMAN: [
            "The elements have already decided this.",
            "Wind, stone, flame and tide. Choose which one takes you.",
            "The ancestors are watching. Do not make this dull for them.",
        ],
        MAGE: [
            "You are standing exactly where I needed you to stand.",
            "Let me show you what the Kirin Tor keeps behind glass.",
            "Arcane, fire or frost. Pick your ending.",
        ],
        WARLOCK: [
            "Something worse than me is listening. Be quick.",
            "I have already promised your soul to something patient.",
            "You will burn, and the fel will not even warm me.",
        ],
        DRUID: [
            "Nature is not gentle. That is a thing people invented.",
            "The wild is with me, and the wild does not negotiate.",
            "Claw or root, the ending is the same.",
        ],
    }

    CLASS_LEVEL = {
        WARRIOR: [
            "Stronger. The armour sits differently at %level.",
            "Another rank earned the honest way.",
            "The drill finally paid out. %level, and the arms know it.",
        ],
        PALADIN: [
            "The Light grants a little more when you have proved you will carry it.",
            "%level, and still nowhere near worthy. Good.",
            "The vow gets heavier. That is how you know it is real.",
        ],
        HUNTER: [
            "The bow feels lighter. Or my arms got serious.",
            "%level. The wild teaches faster than any academy.",
            "My beast noticed before I did.",
        ],
        ROGUE: [
            "Quieter, quicker, and harder to find. %level suits me.",
            "The trade rewards practice more than talent.",
            "Nobody handed me this one either.",
        ],
        PRIEST: [
            "The prayers carry further now.",
            "%level. More strength to spend on other people.",
            "The Light does not reward ambition. It rewards attendance.",
        ],
        DEATH_KNIGHT: [
            "The runes drink deeper. %level, and colder for it.",
            "Stronger. Not warmer. That was never on offer.",
            "The Ebon Blade does not celebrate. It simply notes the improvement.",
        ],
        SHAMAN: [
            "The elements speak a little plainer at %level.",
            "They trust me with more. I intend to deserve it.",
            "The ancestors approve, in their own silence.",
        ],
        MAGE: [
            "%level. The theory finally caught up with the practice.",
            "More power, and more ways to lose a hand. Precision, then.",
            "Dalaran would grudgingly acknowledge this.",
        ],
        WARLOCK: [
            "%level. The terms improve, and so does the interest.",
            "It gave me more. It always wants something for more.",
            "Stronger, and one step further from anything that would take me back.",
        ],
        DRUID: [
            "The Dream widened a little. %level, and deeper in.",
            "The shapes come easier now, and come back harder to leave.",
            "Balance at %level. Ask me again in a season.",
        ],
    }

    CLASS_BOSS = {
        WARRIOR: [
            "%target went down the way they all do. Slowly, then all at once.",
            "That is what a shield wall is for.",
        ],
        PALADIN: [
            "%target is judged. The Light was never going to lose this.",
            "Rest, if the Light allows it. I doubt it will.",
        ],
        HUNTER: [
            "%target was tracked, cornered and taken. In that order.",
            "Every hunt ends. %target simply took longer.",
        ],
        ROGUE: [
            "%target never saw where the last one came from.",
            "That is one contract nobody will admit to paying for.",
        ],
        PRIEST: [
            "%target is beyond mending now. I did offer.",
            "May whatever waits for %target be fairer than I was.",
        ],
        DEATH_KNIGHT: [
            "%target is dead. I know the difference better than most.",
            "The Ebon Blade collects. %target has been collected.",
        ],
        SHAMAN: [
            "The elements have taken %target back into the cycle.",
            "%target fought the storm. The storm is patient and very old.",
        ],
        MAGE: [
            "%target was a problem of geometry. Solved.",
            "Note the time. %target lasted longer than I predicted.",
        ],
        WARLOCK: [
            "%target belongs to something else now. I only arranged the transfer.",
            "The soul of %target will go somewhere useful.",
        ],
        DRUID: [
            "%target is returned to the earth, willing or not.",
            "The Circle would call that balance restored.",
        ],
    }

    # ======================================================================
    # Archetype follow-ups, one set per situation.
    # ======================================================================
    MUSE = {
        DEVOUT: [
            "Whatever comes, it comes with permission.",
            "I would like to be found doing my duty.",
            "Grace is not earned, but I intend to try anyway.",
            "There are worse things than being needed.",
        ],
        GRIM: [
            "None of it lasts. Work anyway.",
            "I stopped expecting better a long way back.",
            "Hope is a ration. Spend it carefully.",
            "We are all only delaying something.",
        ],
        SCHOLAR: [
            "There is a book about this somewhere, and it is probably wrong.",
            "I would like to write it down before I forget the order of it.",
            "Understanding is slower than surviving, and worth more.",
            "Every answer comes with three new questions attached.",
        ],
        BOASTFUL: [
            "They will tell this part badly when they tell it.",
            "I am better than the stories, and the stories are generous.",
            "Modesty is for people with less to work with.",
            "Give me an audience and I will give you a legend.",
        ],
        WRY: [
            "Glorious. Truly. Someone should paint it.",
            "I was promised adventure. This is mostly walking.",
            "I would complain, but the pay is poor and the company is worse.",
            "At least the scenery is trying.",
        ],
        HAUNTED: [
            "I hear it worst when everything goes quiet.",
            "There are names I do not say out loud any more.",
            "I keep moving so it cannot catch up.",
            "Sleep is where it waits for me.",
        ],
        SAVAGE: [
            "Talk is the part before the good part.",
            "I am at my best when I stop thinking.",
            "Peace makes me itch.",
            "Give me something to break and I will be pleasant company.",
        ],
        SINISTER: [
            "Everyone is useful, once you know which lever to pull.",
            "I am owed a great deal, and I am patient.",
            "Let them underestimate me. It saves so much effort.",
            "Trust is a debt I never intend to repay.",
        ],
    }

    THREAT = {
        DEVOUT: [
            "I did not want this. I will finish it regardless.",
            "May it be quick, for both our sakes.",
            "Stand aside or stand before the Light.",
        ],
        GRIM: [
            "Get on with it.",
            "This changes nothing. It never does.",
            "One of us walks away. I have no strong feelings about which.",
        ],
        SCHOLAR: [
            "I have studied things like you. You are not the interesting part.",
            "Let us see whether the theory holds.",
            "Predictable. Disappointingly so.",
        ],
        BOASTFUL: [
            "Watch closely. This will be worth describing later.",
            "You have chosen very poorly, and publicly.",
            "I will make this look easy, because it is.",
        ],
        WRY: [
            "Marvellous. Another one who wants to be a story.",
            "I had plans. You are not in them.",
            "We could both walk away. No? Right.",
        ],
        HAUNTED: [
            "I have killed better than you and it did not help.",
            "Come on. Add yourself to the list.",
            "I am so tired of this, and I am still very good at it.",
        ],
        SAVAGE: [
            "Finally.",
            "Bleed for me.",
            "Do not die quickly. Where is the joy in that.",
        ],
        SINISTER: [
            "You will be a useful example.",
            "I had hoped you would try something. Thank you.",
            "Nobody is coming. I checked.",
        ],
    }

    RISE = {
        DEVOUT: [
            "It is not mine to be proud of. It is mine to use well.",
            "One more step along a road that does not end.",
        ],
        GRIM: [
            "Stronger is only further from the ground. It still ends the same.",
            "Good. The odds were insulting.",
        ],
        SCHOLAR: [
            "I should record what changed. The details matter later.",
            "Progress is measurable, which is the only reason I trust it.",
        ],
        BOASTFUL: [
            "And I am not finished. Not remotely.",
            "Someone write this down properly.",
        ],
        WRY: [
            "I feel exactly the same, only with better posture.",
            "All this and still no one has offered me a chair.",
        ],
        HAUNTED: [
            "Stronger. It still follows me at the same pace.",
            "I did not do this to be better. I did it to survive the next one.",
        ],
        SAVAGE: [
            "More. I want more.",
            "Now bring me something that lasts longer than a breath.",
        ],
        SINISTER: [
            "Every rung is a person I can afford to disappoint.",
            "Power is only leverage that arrived early.",
        ],
    }

    TRIUMPH = {
        DEVOUT: [
            "The Light be thanked, and the fallen remembered.",
            "Grace carried us. Say so when you tell it.",
        ],
        GRIM: [
            "Do not cheer. There is always another one.",
            "It cost more than it looks like from here.",
        ],
        SCHOLAR: [
            "I want that skull, the notes, and an hour alone with both.",
            "Now we know what such a thing can actually do.",
        ],
        BOASTFUL: [
            "Tell them who did it. Use my name properly.",
            "That is what a real champion looks like.",
        ],
        WRY: [
            "Astonishing. And no one saw it but us.",
            "Right. Who is carrying the loot.",
        ],
        HAUNTED: [
            "One more face I will see again tonight.",
            "It should feel better than it does.",
        ],
        SAVAGE: [
            "That was worth the walk.",
            "Find me another one. A bigger one.",
        ],
        SINISTER: [
            "The reputation is worth more than the reward.",
            "Word of this will open doors I would rather not knock on.",
        ],
    }

    SITUATIONS = [
        ("idle",         CLASS_IDLE,   MUSE,    1),
        ("combat_start", CLASS_COMBAT, THREAT,  1),
        ("level_up",     CLASS_LEVEL,  RISE,    2),
        ("kill_boss",    CLASS_BOSS,   TRIUMPH, 2),
    ]

    for trigger, class_frags, arch_frags, weight in SITUATIONS:
        for cls, archetypes in CLASS_ARCHETYPES.items():
            for archetype in archetypes:
                for first in class_frags[cls]:
                    for second in arch_frags[archetype]:
                        text = join(first, second)
                        if len(text) > 255:
                            continue
                        line(trigger, text, cls=cls, personality=archetype,
                             weight=weight,
                             comment=f"{CLASS_NAMES[cls]} "
                                     f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Quests, crossed the same way. %quest is the quest title, so these work
    # for any quest in the game while still sounding like the speaker - the
    # hand-placed lines in gen_bot_lore.py beat them whenever a specific
    # quest matches, because that line scores higher on specificity.
    # ======================================================================
    CLASS_QUEST_ACCEPT = {
        WARRIOR: [
            "%quest. Point me at it and stand clear.",
            "They asked for a sword and I am the nearest one.",
            "I do not need the reason. I need the direction.",
        ],
        PALADIN: [
            "%quest. If it needs doing, it needs doing properly.",
            "The Light does not ask for volunteers twice.",
            "This is what the vow looks like on an ordinary day.",
        ],
        HUNTER: [
            "%quest. I will find the tracks before I find the trouble.",
            "Give me the ground and a day and it is done.",
            "My beast will have the scent long before I have the details.",
        ],
        ROGUE: [
            "%quest. Discreetly, I assume.",
            "You are paying me not to ask questions. I accept both.",
            "Quietly done is done twice.",
        ],
        PRIEST: [
            "%quest. Somebody is suffering at the end of this.",
            "I will go. Someone has to be the one who goes.",
            "The Light rarely sends comfortable errands.",
        ],
        DEATH_KNIGHT: [
            "%quest. The living ask, and it amuses me to answer.",
            "The Ebon Blade has no orders here. I choose this one.",
            "Whatever it is, it will end. I am very good at endings.",
        ],
        SHAMAN: [
            "%quest. The elements are already unsettled about it.",
            "I will ask the spirits what they know before I go.",
            "The land is asking as loudly as the man is.",
        ],
        MAGE: [
            "%quest. Interesting phrasing. There is something omitted.",
            "I will want the details written down, not shouted.",
            "Very well. I have read about worse.",
        ],
        WARLOCK: [
            "%quest. And what is it worth, precisely.",
            "I will do it. Do not ask how.",
            "Everything is a bargain. This one is merely honest about it.",
        ],
        DRUID: [
            "%quest. The land will tell me whether this is wise.",
            "The Circle would want this looked into.",
            "If it wounds the balance, I will go. That is all the reason I need.",
        ],
    }

    CLASS_QUEST_DONE = {
        WARRIOR: [
            "%quest is finished. It went about as well as these things do.",
            "Done. My arms will remind me of it for a week.",
            "That is settled. Do not ask about the details.",
        ],
        PALADIN: [
            "%quest is done, and done cleanly.",
            "The Light saw it through. I merely carried it.",
            "One less wrong standing. There are always more.",
        ],
        HUNTER: [
            "%quest is done. Tracked it, found it, ended it.",
            "The trail went cold twice. It did not stay cold.",
            "My beast got the last of it. It earned that.",
        ],
        ROGUE: [
            "%quest is finished and nobody saw me do it.",
            "It is done. That is all anyone needs to know.",
            "No witnesses, no mess, no questions. Standard.",
        ],
        PRIEST: [
            "%quest is done. I hope it was worth what it cost them.",
            "It is finished. I will say the words for the ones it was too late for.",
            "The Light gave me enough to see it through.",
        ],
        DEATH_KNIGHT: [
            "%quest is over. It was never in doubt.",
            "Done. The living may sleep a little better and never know why.",
            "Everything in my way is dead. Task complete, I believe.",
        ],
        SHAMAN: [
            "%quest is done. The land breathes easier for it.",
            "The elements are calmer now. That is how I know it worked.",
            "The ancestors were watching. They are satisfied.",
        ],
        MAGE: [
            "%quest concluded, and mostly as predicted.",
            "Done. The interesting part was not the part they asked for.",
            "Filed and finished. I will want to reread my notes.",
        ],
        WARLOCK: [
            "%quest is done. The price was paid by someone else, as usual.",
            "Finished. Nobody need know what it took.",
            "It is complete. I would not examine the method too closely.",
        ],
        DRUID: [
            "%quest is done. The balance holds, for now.",
            "Finished. The land will take years to say thank you.",
            "Done, and done gently where it could be.",
        ],
    }

    QUEST_ACCEPT_TAIL = {
        DEVOUT: [
            "I go where I am sent.",
            "Let it be done in the Light's name, or not at all.",
        ],
        GRIM: [
            "It will be worse than they said. It always is.",
            "Nobody else was going to do it.",
        ],
        SCHOLAR: [
            "I will want to know why, even if nobody else does.",
            "There is more to this than the errand.",
        ],
        BOASTFUL: [
            "They picked the right one, obviously.",
            "This will make a fine chapter.",
        ],
        WRY: [
            "What could possibly go wrong.",
            "Another errand from a stranger. My favourite kind of career.",
        ],
        HAUNTED: [
            "Keeping busy is the only thing that works.",
            "I would rather be walking than remembering.",
        ],
        SAVAGE: [
            "Point me at whatever needs killing.",
            "Less talking. More going.",
        ],
        SINISTER: [
            "And I will take rather more from it than they offered.",
            "Useful. People remember who helped them.",
        ],
    }

    QUEST_DONE_TAIL = {
        DEVOUT: [
            "Thanks be, and on to the next.",
            "It was never my strength that finished it.",
        ],
        GRIM: [
            "It fixed nothing. It was still worth doing.",
            "That is one hole plugged in a very leaky world.",
        ],
        SCHOLAR: [
            "I learned more than they will ever ask about.",
            "The notes will be longer than the errand was.",
        ],
        BOASTFUL: [
            "Efficient, decisive and largely unassisted.",
            "You may all express your gratitude in coin.",
        ],
        WRY: [
            "My reward will be a copper and a handshake, I expect.",
            "Somehow I am still the one holding the bag.",
        ],
        HAUNTED: [
            "For a moment I did not think about anything else. That was the reward.",
            "Now the quiet comes back.",
        ],
        SAVAGE: [
            "Good. I am still warm. Find me another.",
            "That barely counted as work.",
        ],
        SINISTER: [
            "They owe me now, and they know it.",
            "A favour banked is better than gold spent.",
        ],
    }

    # ======================================================================
    # Arriving somewhere. %zone carries the actual zone name, so these cover
    # the whole world; the hand-placed zone lines still win in the zones
    # that have them.
    # ======================================================================
    CLASS_ARRIVE = {
        WARRIOR: [
            "%zone. Good ground, if it comes to a fight.",
            "I judge a place by where I would make a stand in it.",
            "No walls here worth the name. Remember that.",
        ],
        PALADIN: [
            "%zone. There will be people here who need someone standing between.",
            "I can feel where the Light is thin in a place like this.",
            "Wherever I set the shield down, that is the chapel.",
        ],
        HUNTER: [
            "%zone. Different tracks here. Give me an hour with them.",
            "Listen to the birds. They stop before anything bad happens.",
            "I can live off this country. Most people could not.",
        ],
        ROGUE: [
            "%zone. Plenty of shadow and plenty of pockets.",
            "First thing in a new place is the way out of it.",
            "Somebody is running something profitable here. There always is.",
        ],
        PRIEST: [
            "%zone. I can hear the grief in it from the road.",
            "Every place has its dead. Some are just louder.",
            "There is suffering here that nobody has come for yet.",
        ],
        DEATH_KNIGHT: [
            "%zone. The dead here are restless, and they know me.",
            "The living stare. Let them.",
            "I have burned places like this. I try not to dwell on it.",
        ],
        SHAMAN: [
            "%zone. The elements here are talking over one another.",
            "The land remembers what was done to it. Listen.",
            "Old spirits here, and not all of them are settled.",
        ],
        MAGE: [
            "%zone. There are ley lines under this, and they are bent.",
            "I would like a week, a desk and a window facing that.",
            "The magic here is untidy. Somebody was careless.",
        ],
        WARLOCK: [
            "%zone. Thin walls between here and somewhere worse.",
            "Something here would answer, if I called it by name.",
            "I can taste where the veil has been torn before.",
        ],
        DRUID: [
            "%zone. The balance here is off, and it did not happen by itself.",
            "The Dream is close here. Sleep lightly.",
            "Growth and rot in the wrong proportions. Someone should tend this.",
        ],
    }

    ARRIVE_TAIL = {
        DEVOUT: [
            "The Light reaches even here.",
            "Whatever waits, it waits for a reason.",
        ],
        GRIM: [
            "Another place that will not miss me.",
            "It will do. Nowhere is better than anywhere.",
        ],
        SCHOLAR: [
            "I have read about this country and read it badly.",
            "Half of what I know about here came from a drunk cartographer.",
        ],
        BOASTFUL: [
            "They will be telling stories about my visit for years.",
            "%zone has no idea what just walked into it.",
        ],
        WRY: [
            "Lovely. I shall summer here.",
            "I am sure the local cuisine is a highlight.",
        ],
        HAUNTED: [
            "New country, same shadow walking behind me.",
            "I was somewhere like this when it happened.",
        ],
        SAVAGE: [
            "Something out there is worth hunting. I can feel it.",
            "Good. Room to run.",
        ],
        SINISTER: [
            "Every new place is a new set of people who owe me nothing yet.",
            "I shall find out who matters here, and then who does not.",
        ],
    }

    CROSSED = [
        ("quest_accept",   CLASS_QUEST_ACCEPT, QUEST_ACCEPT_TAIL, 1),
        ("quest_complete", CLASS_QUEST_DONE,   QUEST_DONE_TAIL,   1),
        ("zone_enter",     CLASS_ARRIVE,       ARRIVE_TAIL,       1),
    ]

    for trigger, class_frags, arch_frags, weight in CROSSED:
        for cls, archetypes in CLASS_ARCHETYPES.items():
            for archetype in archetypes:
                for first in class_frags[cls]:
                    for second in arch_frags[archetype]:
                        text = join(first, second)
                        if len(text) > 255:
                            continue
                        line(trigger, text, cls=cls, personality=archetype,
                             weight=weight,
                             comment=f"{CLASS_NAMES[cls]} "
                                     f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Race. Light dialect for trolls and dwarves, the way the game writes
    # them. Crossed with archetype, so the same heritage sounds different
    # depending on who is carrying it.
    # ======================================================================
    RACE_NAMES = {
        HUMAN: "human", DWARF: "dwarf", GNOME: "gnome",
        NIGHTELF: "night elf", DRAENEI: "draenei", ORC: "orc",
        UNDEAD: "forsaken", TAUREN: "tauren", TROLL: "troll",
        BLOODELF: "blood elf",
    }

    RACE_IDLE = {
        HUMAN: [
            "Stormwind taught me that a kingdom is mostly paperwork and grief.",
            "We are short-lived, and we get a great deal done for it.",
            "My grandfather fought orcs. I have orc allies. Call that progress.",
        ],
        DWARF: [
            "There is stone under everything, and stone keeps records.",
            "Three clans, one Forge, and a great deal of shouting.",
            "Ye can trust a dwarf tae finish the ale and the job. In that order.",
        ],
        GNOME: [
            "We lost a city to our own cleverness. I think about that daily.",
            "Every problem is a mechanism you have not opened yet.",
            "Being small means I am never the biggest mistake in the room.",
        ],
        NIGHTELF: [
            "I have watched empires rise and be forgotten. Twice.",
            "We gave up immortality and we are still deciding how we feel.",
            "Ten thousand years of vigil, and the Legion came anyway.",
        ],
        DRAENEI: [
            "We have been refugees on two worlds. The word has lost its sting.",
            "The naaru promised the Light would find us. It took its time.",
            "Argus was beautiful. I have only my grandmother's word for it.",
        ],
        ORC: [
            "The blood curse is broken. The shame is not, quite.",
            "We build with our own hands now, not with demon gifts.",
            "Thrall gave us honour back. We are still learning how to carry it.",
        ],
        UNDEAD: [
            "I remember dying. Everyone assumes that is the worst part.",
            "The Dark Lady kept us. That is more than the living offered.",
            "I have no heartbeat and I keep making plans regardless.",
        ],
        TAUREN: [
            "The Earth Mother is patient with us. We are not always patient with her.",
            "We drove the centaur off our own grass. It took generations.",
            "Nothing is wasted. Not the hide, not the bone, not the grief.",
        ],
        TROLL: [
            "Da Darkspear don' go back ta what we was. We go forward.",
            "Trolls been on dis world longer than any of dem. Remember dat.",
            "Da loa still listen, when ya show dem proper respect.",
        ],
        BLOODELF: [
            "We were Quel'dorei once. Now we are whatever came after.",
            "Arthas walked through my city. I need not explain my anger.",
            "The thirst never leaves. You only get better at the manners.",
        ],
    }

    RACE_TRAVEL = {
        HUMAN: [
            "Human roads, or no roads at all. I have walked both.",
            "Every league out of Stormwind feels like a league from home.",
        ],
        DWARF: [
            "Uphill, downhill, it is all rock tae me.",
            "I have walked colder country than this and complained less.",
        ],
        GNOME: [
            "I measured the distance. Nobody asked me to.",
            "I have a map, three corrections to the map, and a theory.",
        ],
        NIGHTELF: [
            "I have walked this continent since before your kings had names.",
            "Elune's light finds the road, even here.",
        ],
        DRAENEI: [
            "I have crossed worlds. A country is a small thing after that.",
            "We walk because we ran out of places to be carried to.",
        ],
        ORC: [
            "The march is the easy part. The waiting is the hard part.",
            "My feet have known far worse ground than this.",
        ],
        UNDEAD: [
            "I do not tire. It is the one mercy of this condition.",
            "The living need rest. I need only a direction.",
        ],
        TAUREN: [
            "We were a wandering people. My hooves remember it.",
            "Walk slowly enough and the land starts telling you things.",
        ],
        TROLL: [
            "Dese legs been carryin' me a long way, mon.",
            "Da jungle taught me ta move quiet. Dis be easy goin'.",
        ],
        BLOODELF: [
            "I would prefer a road, a horse, and someone else carrying things.",
            "We used to travel by spellwork. I miss it hourly.",
        ],
    }

    RACE_DEATH = {
        HUMAN: [
            "Tell them... I died on my feet.",
            "The Light take me, if it will have me.",
        ],
        DWARF: [
            "Bury me in stone. Not dirt.",
            "Tell the Forge... I never went out first.",
        ],
        GNOME: [
            "Miscalculated. Badly.",
            "Someone... record the variables.",
        ],
        NIGHTELF: [
            "Elune. Guide me into the long dark.",
            "Ten thousand years, and I still was not ready.",
        ],
        DRAENEI: [
            "The Light does not abandon. It does not.",
            "I will see Argus after all.",
        ],
        ORC: [
            "Lok'tar... ogar.",
            "No grave. Burn me, and say it was a good death.",
        ],
        UNDEAD: [
            "Again. Of course. Again.",
            "Do not weep. I have done this before.",
        ],
        TAUREN: [
            "The Earth Mother takes me back.",
            "Return me to the soil. Waste nothing.",
        ],
        TROLL: [
            "Da loa be callin' me.",
            "Dis body be done. Dat don' mean I be done.",
        ],
        BLOODELF: [
            "Not like this. Not after everything.",
            "Silvermoon. I never went back.",
        ],
    }

    for race, texts in RACE_DEATH.items():
        for text in texts:
            line("death", text, race=race, weight=3,
                 comment=f"{RACE_NAMES[race]} death")

    for race, texts in RACE_IDLE.items():
        for archetype, tails in MUSE.items():
            for first in texts:
                for second in tails:
                    body = join(first, second)
                    if len(body) > 255:
                        continue
                    line("idle", body, race=race, personality=archetype,
                         comment=f"{RACE_NAMES[race]} "
                                 f"{PERSONALITY_NAMES[archetype]}")

    for race, texts in RACE_TRAVEL.items():
        for archetype, tails in ARRIVE_TAIL.items():
            for first in texts:
                for second in tails:
                    body = join(first, second)
                    if len(body) > 255:
                        continue
                    line("zone_enter", body, race=race,
                         personality=archetype,
                         comment=f"{RACE_NAMES[race]} travel "
                                 f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Race and class together - the layer that makes a devout human paladin
    # sound like one rather than like a paladin who happens to be human.
    # Only combinations the game allows, and only the ones with real lore
    # attached; the generic class and race layers above cover the rest.
    # ======================================================================
    RACE_CLASS = {
        (HUMAN, PALADIN): [
            "A knight of the Silver Hand, out of Stormwind, and proud of both.",
            "Uther's order broke and reformed. I carry whatever survived.",
        ],
        (HUMAN, WARRIOR): [
            "Stormwind trained me and Stormwind spent me. Fair enough.",
            "Footman first, and I have never stopped standing like one.",
        ],
        (HUMAN, MAGE): [
            "Dalaran took me in as a child. I have been paying attention since.",
            "The Kirin Tor is a purple robe and a lifetime of homework.",
        ],
        (HUMAN, PRIEST): [
            "Northshire raised me and never once let me forget it.",
            "I learned the Light in a stone room that smelled of candles.",
        ],
        (HUMAN, ROGUE): [
            "SI:7 does not exist, and I have certainly never worked for it.",
            "The alleys of Old Town taught me more than the barracks would have.",
        ],
        (HUMAN, WARLOCK): [
            "There is a reason we practise this in cellars in Stormwind.",
            "The Kirin Tor would have me arrested. They are not entirely wrong.",
        ],
        (DWARF, HUNTER): [
            "A rifle, a hound and a mountain. That is a dwarf's whole religion.",
            "Ironforge breeds marksmen. The rest is only practice.",
        ],
        (DWARF, WARRIOR): [
            "Mountain King is a title. Standin' yer ground is a habit.",
            "I have held a line in a tunnel. Nothing above ground frightens me.",
        ],
        (DWARF, PALADIN): [
            "The Light and the Forge. Both want a steady hand and a hot temper.",
            "We took to the Light late and hard, like everything else.",
        ],
        (DWARF, PRIEST): [
            "The Explorers dig up the past. I pray over what they find.",
            "Anvilmar's kin prayed before they mined. I keep the order of it.",
        ],
        (DWARF, ROGUE): [
            "Nobody expects a dwarf to be quiet. That is the entire advantage.",
            "I learned locks in Ironforge, where every door is worth opening.",
        ],
        (GNOME, MAGE): [
            "Arcane theory is engineering with fewer springs.",
            "I have improved on six published spells and been thanked for none.",
        ],
        (GNOME, WARLOCK): [
            "Gnomeregan made me curious about things that should stay shut.",
            "I keep my demon in a very well documented arrangement.",
        ],
        (GNOME, ROGUE): [
            "Nobody watches the small one. That is a design flaw I exploit.",
            "Lockpicks are only very rude keys.",
        ],
        (GNOME, WARRIOR): [
            "I fight at knee height. You would be amazed what is undefended there.",
            "Armour, at my size, is mostly a very expensive barrel.",
        ],
        (NIGHTELF, DRUID): [
            "Malfurion was the first. I am far down the list, and still here.",
            "I slept in the Dream for an age. I am still shaking it off.",
        ],
        (NIGHTELF, PRIEST): [
            "The Sisters of Elune taught me long before the Light was mentioned.",
            "Elune does not shout. You learn to listen in the dark.",
        ],
        (NIGHTELF, HUNTER): [
            "I was a Sentinel. The forest was the wall.",
            "Ten thousand years of watching treelines makes its own patience.",
        ],
        (NIGHTELF, ROGUE): [
            "Shadowmeld is not a trick. It is inheritance.",
            "We were assassins while your people were still farming.",
        ],
        (NIGHTELF, WARRIOR): [
            "A glaive, a wall of Darnassus, and a very long memory.",
            "The Sentinels do not break. It is not in the training.",
        ],
        (DRAENEI, SHAMAN): [
            "We learned the elements from the orcs, before everything went wrong.",
            "Farseer is not a rank. It is a burden with a pleasant name.",
        ],
        (DRAENEI, PALADIN): [
            "The Light found us adrift. We did not find it.",
            "Hand of Argus. The name is heavier than the hammer.",
        ],
        (DRAENEI, PRIEST): [
            "The naaru sang to us for a thousand years. I still hear the note.",
            "Exodar's halls taught me the Light in a language you do not have.",
        ],
        (DRAENEI, MAGE): [
            "We had this art on Argus. I am only remembering it in a new tongue.",
            "The Exodar's crystals taught me more than any human academy.",
        ],
        (ORC, WARRIOR): [
            "Lok'tar ogar. It is not a boast, it is a description.",
            "Blademaster training, and scars enough to prove I was a slow student.",
        ],
        (ORC, SHAMAN): [
            "The elements forgave us. That is the whole miracle of my people.",
            "Thrall was a shaman before he was Warchief. Remember the order.",
        ],
        (ORC, HUNTER): [
            "The wolves of Durotar chose me. I only agreed to it.",
            "We hunt to eat, and to remember how.",
        ],
        (ORC, WARLOCK): [
            "My people were ruined by this power once. I am very careful.",
            "Orgrimmar tolerates me. Barely, and in the cellars.",
        ],
        (ORC, ROGUE): [
            "An orc who moves quietly is a thing nobody plans for.",
            "Honour says face them. Sense says do not let them see you.",
        ],
        (UNDEAD, ROGUE): [
            "No pulse, no breath, no sound at all. It is almost unfair.",
            "The Deathstalkers taught me patience I never had while alive.",
        ],
        (UNDEAD, WARLOCK): [
            "I was damned before I took up the craft. The craft was a formality.",
            "Shadow is more honest company than most of the living.",
        ],
        (UNDEAD, PRIEST): [
            "I serve the Light with dead hands. Argue with the results.",
            "A Forsaken priest. Yes, I have heard the joke.",
        ],
        (UNDEAD, MAGE): [
            "I studied in Lordaeron. It is a ruin and I remember the shelves.",
            "Cold stopped bothering me some time ago. Useful, for frost work.",
        ],
        (UNDEAD, WARRIOR): [
            "I do not feel the hits any more. I simply count them.",
            "A dead soldier makes a very poor coward.",
        ],
        (TAUREN, DRUID): [
            "Hamuul walks with the Circle now. My people were always listening.",
            "The Earth Mother and the Dream are one teaching in two voices.",
        ],
        (TAUREN, SHAMAN): [
            "The elements speak plainly on the plains. Fewer walls in the way.",
            "I learned the totems before I learned to ride a kodo.",
        ],
        (TAUREN, WARRIOR): [
            "We do not fight for glory. We fight because the centaur came.",
            "A tauren who raises a weapon has already tried everything else.",
        ],
        (TAUREN, HUNTER): [
            "Mulgore teaches you to take only what the herd can spare.",
            "I thank the kill. Every time. It is not a formality.",
        ],
        (TROLL, SHAMAN): [
            "Da loa an' da elements both be listenin'. Ya just gotta ask right.",
            "Voodoo an' spirits, mon. Same road, different shoes.",
        ],
        (TROLL, HUNTER): [
            "Da Darkspear hunt raptors. Everythin' else be practice.",
            "I been trackin' since before I could hold a spear proper.",
        ],
        (TROLL, ROGUE): [
            "Shadow hunter blood in dis family, an' I use it quiet.",
            "Ya don' see a troll in da trees till it be far too late, mon.",
        ],
        (TROLL, MAGE): [
            "Dey say trolls don' do arcane. Dey be wrong, an' loud about it.",
            "Da old empire had mages, mon. We just don' write it down.",
        ],
        (TROLL, PRIEST): [
            "Da spirits an' da Light both be healin'. I don' argue wit' either.",
            "I mend wit' voodoo an' wit' faith, an' nobody complain after.",
        ],
        (BLOODELF, MAGE): [
            "Silvermoon made me. The Sunwell unmade half of what I was.",
            "We were casting spells while your ancestors still feared lightning.",
        ],
        (BLOODELF, PALADIN): [
            "Blood Knight. We took the Light by force and it stayed anyway.",
            "Liadrin knelt properly in the end. Some of us are still catching up.",
        ],
        (BLOODELF, WARLOCK): [
            "Fel is an old habit in Quel'Thalas. We pretend otherwise.",
            "Kael'thas showed us where the thirst leads. I took notes, not a side.",
        ],
        (BLOODELF, ROGUE): [
            "Farstriders in the family. I chose quieter work.",
            "Elegance and a knife. We invented that combination.",
        ],
        (BLOODELF, PRIEST): [
            "I serve the Light in a city that nearly lost the right to ask.",
            "We prayed to nothing for years. The Light came back first.",
        ],
        (BLOODELF, HUNTER): [
            "Farstrider training. A bow, a hawkstrider, and a great deal of pride.",
            "Eversong taught me to shoot between the leaves without touching one.",
        ],
    }

    for (race, cls), texts in RACE_CLASS.items():
        for archetype in CLASS_ARCHETYPES[cls]:
            for first in texts:
                for second in MUSE[archetype][:2]:
                    body = join(first, second)
                    if len(body) > 255:
                        continue
                    line("idle", body, race=race, cls=cls,
                         personality=archetype, weight=2,
                         comment=f"{PERSONALITY_NAMES[archetype]} "
                                 f"{RACE_NAMES[race]} {CLASS_NAMES[cls]}")

    # ======================================================================
    # Gender. Only used where it actually changes the words - kinship and
    # the forms of address the orders use. Everything else in this corpus is
    # written to read correctly either way.
    # ======================================================================
    MALE, FEMALE = 0, 1

    CLASS_GENDER = [
        (PRIEST, MALE,   "Brother, they call me, and I have never grown used to it."),
        (PRIEST, FEMALE, "Sister, they call me, and I have never grown used to it."),
        (PALADIN, MALE,   "A brother of the Light, sworn and sealed."),
        (PALADIN, FEMALE, "A sister of the Light, sworn and sealed."),
        (WARRIOR, MALE,   "Shield-brother to anyone who holds the line beside me."),
        (WARRIOR, FEMALE, "Shield-sister to anyone who holds the line beside me."),
        (DRUID, MALE,   "The Circle calls me brother. The trees are less formal."),
        (DRUID, FEMALE, "The Circle calls me sister. The trees are less formal."),
        (MAGE, MALE,   "Archmage, one day. They will have to call me something."),
        (MAGE, FEMALE, "Archmage, one day. They will have to call me something."),
        (SHAMAN, MALE,   "Farseer, if the ancestors are generous about it."),
        (SHAMAN, FEMALE, "Farseer, if the ancestors are generous about it."),
        (ROGUE, MALE,   "No title, no order, no one to write to if it goes badly."),
        (ROGUE, FEMALE, "No title, no order, no one to write to if it goes badly."),
        (HUNTER, MALE,   "My father taught me the draw. My beast taught me the rest."),
        (HUNTER, FEMALE, "My mother taught me the draw. My beast taught me the rest."),
        (WARLOCK, MALE,   "They whisper about me in the market. They are quite right."),
        (WARLOCK, FEMALE, "They whisper about me in the market. They are quite right."),
        (DEATH_KNIGHT, MALE,   "I had a son. He would be grown now, and he thinks I am buried."),
        (DEATH_KNIGHT, FEMALE, "I had a daughter. She would be grown now, and she thinks I am buried."),
    ]

    RACE_GENDER = [
        (TAUREN, MALE,   "A son of Mulgore, and the Earth Mother knows my stride."),
        (TAUREN, FEMALE, "A daughter of Mulgore, and the Earth Mother knows my stride."),
        (DWARF, MALE,   "A son of the mountain, lad, and I will thank ye tae remember it."),
        (DWARF, FEMALE, "A daughter of the mountain, and I will thank ye tae remember it."),
        (NIGHTELF, MALE,   "A son of the moon, though we do not use the phrase often."),
        (NIGHTELF, FEMALE, "A daughter of Elune. The moon has watched me a very long time."),
        (ORC, MALE,   "My father's axe, my father's name, and my own debts."),
        (ORC, FEMALE, "My mother's axe, my mother's name, and my own debts."),
        (HUMAN, MALE,   "One more of Stormwind's sons, spent on somebody else's border."),
        (HUMAN, FEMALE, "One more of Stormwind's daughters, and they still ask if I am the healer."),
        (UNDEAD, MALE,   "I had a wife, once. I do not go near the house any more."),
        (UNDEAD, FEMALE, "I had a husband, once. I do not go near the house any more."),
        (BLOODELF, MALE,   "My brothers went with Kael'thas. I stayed. We do not write."),
        (BLOODELF, FEMALE, "My sisters went with Kael'thas. I stayed. We do not write."),
        (TROLL, MALE,   "Me mudda raised eight of us. I be da one dat left, mon."),
        (TROLL, FEMALE, "Me mudda raised eight of us. I be da one dat stayed angry."),
        (DRAENEI, MALE,   "My father held the line at Tempest Keep. I never found the body."),
        (DRAENEI, FEMALE, "My mother held the line at Tempest Keep. I never found the body."),
        (GNOME, MALE,   "My brothers are all still in Gnomeregan. Officially, they are missing."),
        (GNOME, FEMALE, "My sisters are all still in Gnomeregan. Officially, they are missing."),
    ]

    for cls, gender, text in CLASS_GENDER:
        line("idle", text, cls=cls, gender=gender, weight=2,
             comment=f"{CLASS_NAMES[cls]} gender {gender}")
        for archetype in CLASS_ARCHETYPES[cls]:
            for tail in MUSE[archetype][:2]:
                body = join(text, tail)
                if len(body) > 255:
                    continue
                line("idle", body, cls=cls, gender=gender,
                     personality=archetype, weight=2,
                     comment=f"{PERSONALITY_NAMES[archetype]} "
                             f"{CLASS_NAMES[cls]} gender {gender}")

    for race, gender, text in RACE_GENDER:
        line("idle", text, race=race, gender=gender, weight=2,
             comment=f"{RACE_NAMES[race]} gender {gender}")
        for archetype, tails in MUSE.items():
            for tail in tails[:2]:
                body = join(text, tail)
                if len(body) > 255:
                    continue
                line("idle", body, race=race, gender=gender,
                     personality=archetype, weight=2,
                     comment=f"{PERSONALITY_NAMES[archetype]} "
                             f"{RACE_NAMES[race]} gender {gender}")

    # ======================================================================
    # Specialisation. SpecMask is a bit per talent tree in tab order, so
    # 1 is the first tree, 2 the second, 4 the third - Arms, Fury,
    # Protection for a warrior, and so on down the list. mod-botlore only
    # reads a spec once the bot has actually spent points, so these stay
    # silent on a fresh character rather than calling everyone Arms.
    # ======================================================================
    TREE1, TREE2, TREE3 = 1, 2, 4

    SPEC_LINES = {
        (WARRIOR, TREE1): ("arms", [
            "Two hands on the hilt and one clean opening. That is the whole of Arms.",
            "A mortal strike is a wound that does not close. Learn where to put it.",
        ]),
        (WARRIOR, TREE2): ("fury", [
            "Two weapons, no shield, and no intention of lasting long enough to need one.",
            "Rage is fuel. Sit still and it drains away.",
        ]),
        (WARRIOR, TREE3): ("protection", [
            "I am the wall. Everything behind me is the reason for the wall.",
            "Taunt, block, hold. There is no glory in it and no substitute for it.",
        ]),
        (PALADIN, TREE1): ("holy", [
            "I carry a hammer and I use it to keep people breathing.",
            "Holy Light in one hand, and never quite enough hours in the day.",
        ]),
        (PALADIN, TREE2): ("protection", [
            "Consecrate the ground, and then refuse to leave it.",
            "A shield is a promise you make to the people behind you.",
        ]),
        (PALADIN, TREE3): ("retribution", [
            "The Light is patient. I am the part of it that is not.",
            "Retribution is a vow with an edge on it.",
        ]),
        (HUNTER, TREE1): ("beast mastery", [
            "My beast is not a pet. It is the better half of the pair.",
            "Feed it, trust it, and get out of its way.",
        ]),
        (HUNTER, TREE2): ("marksmanship", [
            "One arrow, placed properly, ends more than a volley does.",
            "The shot is made long before the string moves.",
        ]),
        (HUNTER, TREE3): ("survival", [
            "Traps, poison and patience. The wild does not fight fair either.",
            "I would rather win ugly at forty yards than nobly at ten.",
        ]),
        (ROGUE, TREE1): ("assassination", [
            "Poison does the work. I only arrange the introduction.",
            "One strike from behind is worth ten from in front.",
        ]),
        (ROGUE, TREE2): ("combat", [
            "I do not skulk. I simply fight better than people expect.",
            "Two blades, no manners, and a great deal of practice.",
        ]),
        (ROGUE, TREE3): ("subtlety", [
            "You will not find me. People have tried, professionally.",
            "The best work leaves no story to tell afterwards.",
        ]),
        (PRIEST, TREE1): ("discipline", [
            "A shield before the wound is worth two prayers after it.",
            "Discipline is the art of never letting it get that far.",
        ]),
        (PRIEST, TREE2): ("holy", [
            "The Light mends. I only hold the door open for it.",
            "I have pulled people back from further than this.",
        ]),
        (PRIEST, TREE3): ("shadow", [
            "The Void answers faster than the Light. That is the trouble with it.",
            "I hear voices. I have learned which ones to use.",
        ]),
        (DEATH_KNIGHT, TREE1): ("blood", [
            "I take the wound and I keep the blood. It is a simple arrangement.",
            "Every drop that leaves me is a drop I intend to collect again.",
        ]),
        (DEATH_KNIGHT, TREE2): ("frost", [
            "The cold goes into the bone and stays there.",
            "Two runeblades, and winter in both of them.",
        ]),
        (DEATH_KNIGHT, TREE3): ("unholy", [
            "The dead work for me now. It seemed a waste not to ask.",
            "Disease, decay and a ghoul that does not complain. Ideal.",
        ]),
        (SHAMAN, TREE1): ("elemental", [
            "Lightning is only impatience with a direction.",
            "I ask the storm politely. It arrives rudely.",
        ]),
        (SHAMAN, TREE2): ("enhancement", [
            "Weapons first, and the elements riding along the edge of them.",
            "Windfury is what happens when a hammer stops waiting its turn.",
        ]),
        (SHAMAN, TREE3): ("restoration", [
            "Water mends what fire took. That is the oldest bargain there is.",
            "Chain the healing along the line. Nobody falls out of it.",
        ]),
        (MAGE, TREE1): ("arcane", [
            "Raw arcane, precisely measured. Elegance is not decoration.",
            "The Nether is a ledger. I have learned to keep it balanced.",
        ]),
        (MAGE, TREE2): ("fire", [
            "Fire is honest. It only ever does the one thing.",
            "I do not aim to wound. I aim to finish the argument.",
        ]),
        (MAGE, TREE3): ("frost", [
            "Nothing reaches me. That is not luck, it is architecture.",
            "Slow them down and the fight becomes arithmetic.",
        ]),
        (WARLOCK, TREE1): ("affliction", [
            "Curses are patient. They work while I walk away.",
            "It will die of what I already gave it. There is no hurry.",
        ]),
        (WARLOCK, TREE2): ("demonology", [
            "My demon and I have terms, and I reread them often.",
            "It is easier to command a fiend than to become one. Barely.",
        ]),
        (WARLOCK, TREE3): ("destruction", [
            "Subtlety is for people who cannot summon enough fire.",
            "Shadow and flame. Nothing left to interrogate afterwards.",
        ]),
        (DRUID, TREE1): ("balance", [
            "Sun and moon, and a robe instead of a hide. It confuses people.",
            "Balance is not compromise. It is knowing which side to lean on today.",
        ]),
        (DRUID, TREE2): ("feral", [
            "Claw and fang suit me better than words ever did.",
            "Bear when it must hold, cat when it must end. Simple.",
        ]),
        (DRUID, TREE3): ("restoration", [
            "Life comes back if you give it somewhere to come back to.",
            "Rejuvenation is patience with a root system.",
        ]),
    }

    for (cls, tree), (spec_name, texts) in SPEC_LINES.items():
        for text in texts:
            line("idle", text, cls=cls, spec=tree, weight=2,
                 comment=f"{CLASS_NAMES[cls]} {spec_name}")
            for archetype in CLASS_ARCHETYPES[cls]:
                for tail in MUSE[archetype][:2]:
                    body = join(text, tail)
                    if len(body) > 255:
                        continue
                    line("idle", body, cls=cls, spec=tree,
                         personality=archetype, weight=2,
                         comment=f"{PERSONALITY_NAMES[archetype]} "
                                 f"{CLASS_NAMES[cls]} {spec_name}")
            for archetype in CLASS_ARCHETYPES[cls]:
                for tail in THREAT[archetype][:1]:
                    body = join(text, tail)
                    if len(body) > 255:
                        continue
                    line("combat_start", body, cls=cls, spec=tree,
                         personality=archetype, weight=2,
                         comment=f"{PERSONALITY_NAMES[archetype]} "
                                 f"{CLASS_NAMES[cls]} {spec_name}")

    # ======================================================================
    # Named quests. Every id here was checked against quest_template by
    # title. Three openings and three closings each, and then each of those
    # crossed with one archetype tail, so a single quest carries around
    # fifty possible lines and a bot draws only the ones that suit it.
    # ======================================================================
    SPECIFIC_QUESTS = {
        7: ([
            "Kobolds in the Jasperlode again. They will tell me not to take the candle.",
            "Somebody has to clear the kobold camp. It may as well be me.",
            "Vermin work. Elwynn's farmers cannot plough around them.",
        ], [
            "The kobolds are scattered. I did take the candle.",
            "Twenty kobolds and one very determined candle. Elwynn is quieter.",
            "The mine is clear. They will be back by harvest, of course.",
        ]),
        83: ([
            "Red linen, and a great deal of it. Not every errand is a battle.",
            "I am to fetch cloth. My sword weeps.",
            "Sara wants red linen goods. Honest work for honest coin.",
        ], [
            "The linen is delivered and nobody bled for it.",
            "Cloth counted and handed over. A rare quiet victory.",
            "Done. I shall not tell the others what this errand was.",
        ]),
        39: ([
            "A report to carry to the garrison. Gnolls on the road, mind.",
            "Thomas wants his report at Westbrook. Riverpaw country the whole way.",
            "Courier work through gnoll country. Simple until it is not.",
        ], [
            "The report reached Westbrook. The gnolls got nothing from me.",
            "Delivered. The garrison did not seem surprised by the contents.",
            "Message carried. Somebody should garrison the road itself.",
        ]),
        65: ([
            "The Defias again. They were masons before anyone called them bandits.",
            "I am to look into the Brotherhood. That name goes further up than Westfall.",
            "Stormwind stiffed the Stonemasons and called the result banditry.",
        ], [
            "The Brotherhood's trail leads where nobody in Stormwind wants it to.",
            "It is done. Van Cleef was a mason before he was a monster.",
            "The investigation is closed. The grievance is not.",
        ]),
        66: ([
            "Stalvan Mistmantle. Every letter in that story is worse than the last.",
            "I am reading a dead man's correspondence, and it darkens as it goes.",
            "The Mistmantle papers. Duskwood documents its madmen thoroughly.",
        ], [
            "Stalvan's tale is told. I wish I had not finished it.",
            "I know what Stalvan became, and how slowly he became it.",
            "The last letter was the worst of them. Do not ask.",
        ]),
        55: ([
            "Morbent Fel. A necromancer in a farmhouse, and Duskwood lets him keep it.",
            "I need the Mark of the Lightbringer before I face Morbent.",
            "Fel raised the dead of Raven Hill. That ends today.",
        ], [
            "Morbent Fel is ash. Raven Hill can rest a little.",
            "The necromancer is destroyed. The graveyard is still full of his work.",
            "Fel is finished. It took the Lightbringer's mark to do it.",
        ]),
        228: ([
            "Mor'Ladim was a father before he was a monster. Remember that.",
            "The thing in Raven Hill was a man named Barrett. I keep that in mind.",
            "Mor'Ladim walks the graves looking for a daughter he already lost.",
        ], [
            "Mor'Ladim is at rest. He was searching for his daughter, in the end.",
            "Barrett is dead twice over now. His grief outlived him.",
            "It is done. Nothing about that felt like a victory.",
        ]),
        1014: ([
            "Arugal made the worgen and then made himself one. Silverpine's own fault.",
            "I am for Shadowfang Keep. Arugal has answered for nothing yet.",
            "The archmage's experiments are still howling in these hills.",
        ], [
            "Arugal is dead. The worgen he loosed are not.",
            "Shadowfang is quieter. Not quiet, mind. Quieter.",
            "The mad archmage is finished. Silverpine will take generations.",
        ]),
        1241: ([
            "A diplomat has gone missing out of Stormwind. That is never just a diplomat.",
            "I am to find the missing envoy, and quietly.",
            "Missing diplomat, and half the court hoping he stays missing.",
        ], [
            "The diplomat business goes higher than anyone will put in writing.",
            "Onyxia. It was always going to be something like that.",
            "I found the trail. What waits at the end of it wears a human face.",
        ]),
        338: ([
            "I am collecting pages of a book. In a jungle. For a hunter's memoir.",
            "Chapters of the Green Hills, scattered across Stranglethorn. Wonderful.",
            "Everyone in Booty Bay is hunting the same missing pages.",
        ], [
            "The Green Hills is complete. Every page cost me blood.",
            "Hemet's memoir is assembled. I have read worse prose in Dalaran.",
            "The book is whole. I know Stranglethorn page by page now.",
        ]),
        581: ([
            "Yenniku is Darkspear, taken by the Bloodscalp. Sen'jin wants him back.",
            "A chief's son, held by his own kind's enemies.",
            "I am to find Yenniku. Stranglethorn is very large and very green.",
        ], [
            "Yenniku is found. His soul was the harder half of the problem.",
            "The Bloodscalp had him. They do not have him now.",
            "Sen'jin will have their son back, after a fashion.",
        ]),
        595: ([
            "Booty Bay wants the Bloodsail thinned. Goblins never ask politely.",
            "Pirates on the coast, and a goblin willing to pay by the head.",
            "The Bloodsail have overstayed. Baron Revilgaz is displeased.",
        ], [
            "The Bloodsail are fewer. Revilgaz counts in corpses and coin.",
            "Done. I am now permanently unwelcome aboard their ships.",
            "The pirates learned something. Not enough, but something.",
        ]),
        624: ([
            "A pirate's riddle and a treasure nobody has found. Naturally I am in.",
            "Cortello left his fortune behind a puzzle. Vain to the last.",
            "Everyone in Booty Bay owns a copy of this riddle and no answer.",
        ], [
            "The riddle is solved. Cortello was cleverer dead than alive.",
            "Found it. I will not say where, and neither will you.",
            "The treasure was real. The riddle was still the better part.",
        ]),
        665: ([
            "Wreck diving off Stranglethorn. The murlocs claimed it first.",
            "There is treasure under that water and something living on top of it.",
            "A sunken ship, a shopping list, and no air down there at all.",
        ], [
            "The wreck gave up its cargo. I will taste salt for a week.",
            "Recovered, and the murlocs are still complaining about it.",
            "It is off the seabed and in a crate. Ask me no more than that.",
        ]),
        717: ([
            "The Badlands are shaking, and it is dwarven digging, not the earth.",
            "Something under Uldaman is waking. The ground keeps saying so.",
            "Shadowforge picks at a titan vault and calls it archaeology.",
        ], [
            "The digging is stopped for now. The tremors say otherwise.",
            "Done. Whatever is under Uldaman noticed us.",
            "Uldaman is quieter. I would not call it settled.",
        ]),
        761: ([
            "Swoops on the bluff again. They take the calves if we allow it.",
            "Mulgore needs thinning of swoops. It is not sport.",
            "The birds have grown bold. That is on us for waiting.",
        ], [
            "The swoops are thinned. The herds will graze easier.",
            "Done. I thanked each of them, as we do.",
            "Mulgore is safer for a season. Only a season.",
        ]),
        767: ([
            "The Rite of Vision. I have waited for this since I was a calf.",
            "I take the vision now. The Earth Mother chooses what she shows.",
            "Every tauren walks this road. Mine begins today.",
        ], [
            "I have seen what the Rite shows. I am not ready to say it aloud.",
            "The vision is given. I understand a little and fear the rest.",
            "The Earth Mother showed me my road. It is longer than I hoped.",
        ]),
        788: ([
            "First blood in Durotar. Everyone starts with the scorpids.",
            "A blade and an errand. This is how every orc begins.",
            "They send the young at the scorpids. It teaches quickly.",
        ], [
            "Teeth cut. The scorpids taught me more than the drill did.",
            "Done. It was small work and it still drew blood.",
            "First task finished. Durotar hands out nothing free.",
        ]),
        790: ([
            "Sarkoth. A scorpid big enough to have a name and a reputation.",
            "They named the beast, which means it has eaten somebody.",
            "I go for Sarkoth. The Valley of Trials talks of nothing else.",
        ], [
            "Sarkoth is dead. The Valley of Trials can find a new story.",
            "The named scorpid is finished. My first true kill.",
            "Sarkoth was slower than the stories. The stories were still fair.",
        ]),
        845: ([
            "Zhevra hooves, and the Barrens ask strange things of everyone.",
            "Hunting zhevra out of the Crossroads. They run and run and run.",
            "The herd will not miss what I take. Barely.",
        ], [
            "The zhevra are hunted. I have run half the Barrens for those hooves.",
            "Done. I will be picking Barrens dust out of my boots for months.",
            "Hooves gathered. These plains are wider than any map suggests.",
        ]),
        879: ([
            "Betrayal from inside the walls. Those are the ones that kill you.",
            "Someone turned. That is always uglier than an enemy at the gate.",
            "I am to root out a traitor. Unpleasant, necessary work.",
        ], [
            "The traitor is dealt with. Nobody thanked me, and I understand why.",
            "It is done. Betrayal leaves a smell in a place for years.",
            "Handled. I will not repeat the name.",
        ]),
        992: ([
            "Water samples across Tanaris, for goblins, in this heat.",
            "A survey of every well and spring in the desert. Marvellous.",
            "Gadgetzan wants to know where the water is. So does everyone.",
        ], [
            "The survey is done and I have never been thirstier.",
            "Every sample collected. Tanaris hides its water thoroughly.",
            "Done. The goblins will sell what I measured, of course.",
        ]),
        2161: ([
            "A peon's satchel, lost to the scorpids. Someone has to fetch it.",
            "Even peons deserve their things back. Durotar disagrees.",
            "An errand for a peon. Nobody in Orgrimmar will hear of it from me.",
        ], [
            "The peon has his burden back. Small kindness, small world.",
            "Returned. He was more grateful than any noble I have served.",
            "Done. It was one satchel, and it mattered to someone.",
        ]),
        2761: ([
            "Thorium smelting, and the Brotherhood tests everyone who asks.",
            "Dark Iron work, and dwarves who mean it. I like them already.",
            "Smelting for the Thorium Brotherhood. Hot work, good company.",
        ], [
            "The smelting is done. The Brotherhood grunted, which is approval.",
            "Thorium poured and tempered. My eyebrows will grow back.",
            "Done. Dwarves measure trust in furnace hours.",
        ]),
        2929: ([
            "An old betrayal, and it still has consequences walking about.",
            "Nothing ages worse than treachery. Let us go and see.",
            "This one goes back generations. Grudges keep better than wine.",
        ], [
            "The old betrayal is answered. Late, but answered.",
            "Done. Some debts wait a very long time to be paid.",
            "Finished. History is heavier than it looks on a page.",
        ]),
        4061: ([
            "Machines rising up. Somebody built them and then stopped watching.",
            "Constructs running with no hand on them. That is never accidental.",
            "Gears, and no gnome in charge of them. Troubling.",
        ], [
            "The machines are stopped. Somebody will rebuild them.",
            "Done. Whoever wound them up is still out there.",
            "Scrap now. It was walking an hour ago.",
        ]),
        4182: ([
            "Blackrock dragonkin, and far too many of them.",
            "The whelps grow fast, and the flights notice us eventually.",
            "Dragonkin on the road. Nothing about that scales in our favour.",
        ], [
            "The dragonkin are thinned. Their mothers will remember.",
            "Done. I have burns in places I will not describe.",
            "Fewer whelps. That is all this ever achieves.",
        ]),
        4787: ([
            "An ancient egg, and everyone wants it intact. Of course they do.",
            "I am to carry an egg. Through that. Wonderful.",
            "Something very old laid it. Something very large may want it back.",
        ], [
            "The egg is delivered, unbroken, and I am still shaking.",
            "Done. The mother was exactly as large as I feared.",
            "It is in learned hands now. I hope they deserve it.",
        ]),
        4904: ([
            "Prisoners to free, and quietly. The loud way gets them killed.",
            "Cages. I have never once walked past a cage.",
            "Someone is held who should not be. That is reason enough.",
        ], [
            "They are free. Some of them did not thank me, and fair enough.",
            "The cages are empty. Whoever filled them will answer later.",
            "Done. Freeing is quicker than the healing afterwards.",
        ]),
        4921: ([
            "Someone is missing after the fighting. Missing is not dead.",
            "I will look for them. The field is large and the light is going.",
            "They went down out there somewhere. I intend to find out where.",
        ], [
            "Found. Not in the state anyone hoped for.",
            "The missing are accounted for. That is the kindest word for it.",
            "It is done. At least there is an answer to give.",
        ]),
        5217: ([
            "Back to Chillwind Camp, with the Plaguelands at my heels the whole way.",
            "Chillwind is the last warm thing in this country.",
            "I carry word back. The road is Scourge from end to end.",
        ], [
            "Chillwind Camp has the report. They did not like it.",
            "Delivered. Andorhal is worse than they were told.",
            "Done. The camp holds, and nobody there believes it will.",
        ]),
        5241: ([
            "Carlin Redpath. I carry news of his brother, and it is bad news.",
            "The Redpath family lost more than most. I bring the proof of it.",
            "Uncle Carlin deserves to know. Nobody wants to be the one to tell him.",
        ], [
            "Carlin knows now. He took it like a man who had already guessed.",
            "Told. There is no good way to hand someone that.",
            "Done. The Redpaths have their answer, and no comfort in it.",
        ]),
        5762: ([
            "The son of Nesingwary, hunting his father's shadow through Stranglethorn.",
            "Hemet junior wants the hunt, not the name. Good for him.",
            "A Nesingwary is hunting. Somebody always gets shot.",
        ], [
            "The young Nesingwary has his trophies. And his father's temper.",
            "Done. He will write a memoir of his own, mark me.",
            "The hunt is finished. The jungle has plenty more.",
        ]),
        6145: ([
            "A Scarlet courier rides the Plaguelands road with orders worth reading.",
            "The Crimson Courier. Ambush work, and against fanatics.",
            "The Crusade writes everything down. That is their weakness.",
        ], [
            "The courier is down and the orders are mine.",
            "The Crusade will miss that letter more than that rider.",
            "Done. Scarlet blood on a Scarlet road.",
        ]),
        8306: ([
            "Into the maw, they said, as though it were a figure of speech.",
            "Madness has a location now, and I am walking towards it.",
            "Whatever is in there has already ruined better than me.",
        ], [
            "I came out of it. I am not certain all of me did.",
            "It is done. Do not ask what the inside looked like.",
            "Finished. I will hear that place for the rest of my life.",
        ]),
        1393: ([
            "A man in an ogre cage, waiting on me. Ogres do not keep prisoners long.",
            "I am to walk a prisoner out of a camp. Simply put, impossible.",
            "Galen wants out of there. So would I.",
        ], [
            "Galen is out and walking. The ogres are slower than their reputation.",
            "Escaped, both of us, and only one of us bleeding.",
            "Done. He talked the entire way, which is how I knew he would live.",
        ]),
        465: ([
            "Nek'rosh is Rend's son, and just as ambitious. Rather less clever.",
            "Dragonmaw orcs in the Wetlands, with a chieftain's son leading them.",
            "Nek'rosh has made his move. Somebody must answer it.",
        ], [
            "Nek'rosh's gambit has failed. His father will not be pleased.",
            "The Dragonmaw are broken here. Not gone. Broken.",
            "Done. His ambition ran well ahead of his warband.",
        ]),
        204: ([
            "Bad medicine in the jungle. Witch doctors, and worse than witch doctors.",
            "Someone is brewing what should not be brewed.",
            "Troll medicine, misused. That is a very old story.",
        ], [
            "The bad medicine is destroyed. The brewer with it.",
            "Done. I do not want to know what was in it.",
            "It is finished. The jungle keeps its recipes, though.",
        ]),
    }

    for quest_id, (openings, closings) in SPECIFIC_QUESTS.items():
        for text in openings:
            line("quest_accept", text, quest=quest_id, weight=3,
                 comment=f"quest {quest_id}")
            for archetype, tails in QUEST_ACCEPT_TAIL.items():
                body = join(text, tails[0])
                if len(body) <= 255:
                    line("quest_accept", body, quest=quest_id,
                         personality=archetype, weight=3,
                         comment=f"quest {quest_id} "
                                 f"{PERSONALITY_NAMES[archetype]}")
        for text in closings:
            line("quest_complete", text, quest=quest_id, weight=3,
                 comment=f"quest {quest_id}")
            for archetype, tails in QUEST_DONE_TAIL.items():
                body = join(text, tails[0])
                if len(body) <= 255:
                    line("quest_complete", body, quest=quest_id,
                         personality=archetype, weight=3,
                         comment=f"quest {quest_id} "
                                 f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Named items, ids checked against item_template. Class filters only
    # where the item is genuinely class-locked.
    # ======================================================================
    SPECIFIC_ITEMS = {
        870:   (0, ["A Fiery War Axe. Every warrior in Azeroth has wanted one of these.",
                    "The head glows even cold. Dark Iron work, or very close to it.",
                    "A Fiery War Axe. I have known men trade a farm for this."]),
        2244:  (0, ["The Krol Blade. Stranglethorn's finest export, and the pirates know it.",
                    "A Krol Blade. Heavy, cruel, and beautifully balanced.",
                    "Krol steel. Every corsair on that coast wants one."]),
        1982:  (0, ["A Nightblade. Shadow bound into the edge, and it sings when it lands.",
                    "Nightblade. Two hands, and the dark does half the cutting."]),
        12784: (0, ["An Arcanite Reaper. Forty pounds of arcanite and bad intentions.",
                    "Arcanite, forged whole. There are not many smiths who could.",
                    "An Arcanite Reaper. Subtlety was never the commission."]),
        11684: (0, ["Ironfoe. The Grim Guzzler's worst kept secret.",
                    "Ironfoe, out of Blackrock Depths. The dwarves will want it back."]),
        1168:  (0, ["A Skullflame Shield. It burns, and it screams. Dwarven taste.",
                    "Skullflame. I can feel it deciding whether to like me."]),
        6953:  (PALADIN, ["Verigan's Fist. The order forges one for each of us who earns it.",
                          "Verigan's Fist, and I have the scars from earning it."]),
        6975:  (0, ["A Whirlwind Axe. The elements were bound into this one properly.",
                    "Whirlwind steel. The air moves before the edge does."]),
        1728:  (0, ["Teebu's Blazing Longsword. Nobody knows who Teebu was. The sword outlived him.",
                    "Teebu's blade, still burning. Fame is a strange inheritance."]),
        2243:  (0, ["The Hand of Edward the Odd. Edward was, by all accounts, extremely odd.",
                    "Edward's Hand. It does something different every time it strikes."]),
        873:   (0, ["The Staff of Jordan. Older than the kingdom that named it.",
                    "Jordan's staff. The carving is not in any alphabet I know."]),
        942:   (0, ["A Freezing Band. Small, cold, and it has saved better than me.",
                    "A Freezing Band. The ice comes out of it unasked."]),
        809:   (0, ["Bloodrazor. The name is not decoration.",
                    "Bloodrazor. It opens a wound that stays open."]),
        1263:  (0, ["A Brain Hacker. Whoever named it was being entirely literal.",
                    "Brain Hacker. Ogres name things exactly as they mean them."]),
        869:   (0, ["A Dazzling Longsword. Pretty, and it still opens armour.",
                    "Dazzling, they call it. The arcane in the steel does that."]),
        2824:  (0, ["Hurricane. A bow that draws faster than the arm should allow.",
                    "Hurricane. The string hums after the arrow has gone."]),
        6687:  (0, ["Corpsemaker. Orcish work, and honest about its purpose.",
                    "Corpsemaker. No orc ever named a weapon hopefully."]),
        7960:  (0, ["A Truesilver Champion. Silver against the undead. The smiths knew.",
                    "Truesilver, and well tempered. The Scourge dislike this one."]),
        12940: (0, ["Dal'Rend's Sacred Charge. Rend's own guard carried the pair.",
                    "Blackrock steel out of Rend's household. It remembers orders."]),
        13036: (0, ["An Assassination Blade. No pretence whatsoever in the name.",
                    "Assassination Blade. Balanced for one purpose only."]),
        13361: (0, ["A Skullforge Reaver. Scholomance steel, and it drinks.",
                    "Skullforge. Necromancers made this, and it shows in the weight."]),
        15806: (0, ["Mirah's Song. Light and quick, and it was a gift once.",
                    "Mirah's Song. Someone loved the person this was made for."]),
        17705: (0, ["A Thrash Blade. It strikes twice when it feels like it.",
                    "Thrash Blade. The second cut arrives before you expect it."]),
        17076: (0, ["Bonereaver's Edge. Out of Ragnaros' own hall.",
                    "Bonereaver. The Core does not give these up cheaply."]),
        17105: (0, ["An Aurastone Hammer. Molten Core work, blessed after the fact.",
                    "Aurastone. Fire forged it and the Light claimed it."]),
        18348: (0, ["Quel'Serrar. Quenched in a dragon's skull. The elves do not exaggerate.",
                    "Quel'Serrar, reforged. Ten thousand years and it is still the finest thing here."]),
        18608: (PRIEST, ["Benediction. The staff changes its nature to match the hand.",
                         "Benediction, and Anathema on the other side of it. Faith is a choice."]),
        19169: (0, ["Nightfall. It calls the dark down on whatever it strikes.",
                    "Nightfall. The axe dims the air around it."]),
        19019: (0, ["Thunderfury. The Windseeker's blade, and I am not worthy of holding it.",
                    "Thunderfury. My arm goes numb and I do not care."]),
        17182: (0, ["Sulfuras, the hand of Ragnaros himself. The air bends around it.",
                    "Sulfuras. I am holding a piece of an elemental lord."]),
        13262: (0, ["The Ashbringer. Even corrupted, it remembers what it was for.",
                    "Ashbringer. Mograine's blade, and it grieves in the hand."]),
        13335: (0, ["The Deathcharger's Reins. Rivendare's own mount, and it still answers.",
                    "Rivendare's charger. It does not need to breathe and neither does it stop."]),
        16900: (DRUID, ["Stormrage Cover. Named for Malfurion, worn by the presumptuous.",
                        "Stormrage work. I will try to deserve the name on it."]),
        19106: (0, ["An Ice Barbed Spear. Scourge work, and it never warms.",
                    "Ice Barbed. The cold in this was put there on purpose."]),
        25192: (0, ["Gutrippers. Fist weapons with no sense of decorum whatsoever.",
                    "Gutrippers. Crude, cheap, and terribly effective."]),
    }

    for item_id, (cls_lock, texts) in SPECIFIC_ITEMS.items():
        for text in texts:
            line("loot_rare", text, item=item_id, cls=cls_lock, weight=4,
                 comment=f"item {item_id}")
            for archetype, reactions in REACT.items():
                if cls_lock and not (cls_lock & classes_with(archetype)):
                    continue
                body = join(text, reactions[0])
                if len(body) <= 255:
                    line("loot_rare", body, item=item_id, cls=cls_lock,
                         personality=archetype, weight=4,
                         comment=f"item {item_id} "
                                 f"{PERSONALITY_NAMES[archetype]}")

    # ======================================================================
    # Dying words. Bots die constantly, so this needs the same depth as the
    # rest of it - class for what they were doing, archetype for how they
    # take it, and the race layer above for what they believe comes next.
    # ======================================================================
    CLASS_DEATH = {
        WARRIOR: [
            "The line breaks here.",
            "I stood. Tell them I stood.",
            "Not one step back, and still.",
        ],
        PALADIN: [
            "The Light does not fail. I did.",
            "Into the Light, if it will have me.",
            "My shield. Someone take up my shield.",
        ],
        HUNTER: [
            "My beast. Run. Run.",
            "I should have heard it coming.",
            "The wild takes everything back eventually.",
        ],
        ROGUE: [
            "Careless. I was careless.",
            "Nobody saw. Nobody ever does.",
            "I should have taken the other door.",
        ],
        PRIEST: [
            "The Light is very bright now.",
            "I have nothing left to give. It was enough.",
            "I can hear them all singing.",
        ],
        DEATH_KNIGHT: [
            "Death again. We are old friends by now.",
            "The runes go cold. So do I.",
            "I have died worse than this.",
        ],
        SHAMAN: [
            "The elements call me home.",
            "Ancestors. Make room.",
            "The earth takes me back, as agreed.",
        ],
        MAGE: [
            "A miscalculation. A fatal one.",
            "The mana is gone. That was all of it.",
            "I had a counterspell for this.",
        ],
        WARLOCK: [
            "The contract comes due.",
            "Something is collecting. I knew it would.",
            "It always wanted this part.",
        ],
        DRUID: [
            "Back to the earth, as it should be.",
            "The Dream. I will wake in the Dream.",
            "Nature reclaims. Even me.",
        ],
    }

    DEATH_TAIL = {
        DEVOUT: [
            "Do not grieve. This was always the arrangement.",
            "Say the words over me. Just the short ones.",
        ],
        GRIM: [
            "I told you how this ends.",
            "Nobody is surprised. Least of all me.",
        ],
        SCHOLAR: [
            "Write down what killed me. It matters.",
            "Fascinating, from this angle.",
        ],
        BOASTFUL: [
            "Tell it well. Tell it loudly.",
            "That was still a better fight than you will ever have.",
        ],
        WRY: [
            "Well. That is embarrassing.",
            "I would like to file a complaint.",
        ],
        HAUNTED: [
            "Finally quiet.",
            "I have been waiting for this a long time.",
        ],
        SAVAGE: [
            "I took enough of them with me.",
            "Not done. Not nearly done.",
        ],
        SINISTER: [
            "This changes very little.",
            "I will be owed for this.",
        ],
    }

    for cls, archetypes in CLASS_ARCHETYPES.items():
        for text in CLASS_DEATH[cls]:
            line("death", text, cls=cls, weight=2,
                 comment=f"{CLASS_NAMES[cls]} death")
            for archetype in archetypes:
                for tail in DEATH_TAIL[archetype]:
                    body = join(text, tail)
                    if len(body) > 255:
                        continue
                    line("death", body, cls=cls, personality=archetype,
                         weight=2,
                         comment=f"{CLASS_NAMES[cls]} death "
                                 f"{PERSONALITY_NAMES[archetype]}")

    for race, texts in RACE_DEATH.items():
        for archetype, tails in DEATH_TAIL.items():
            for first in texts:
                for second in tails:
                    body = join(first, second)
                    if len(body) > 255:
                        continue
                    line("death", body, race=race, personality=archetype,
                         weight=2,
                         comment=f"{RACE_NAMES[race]} death "
                                 f"{PERSONALITY_NAMES[archetype]}")
