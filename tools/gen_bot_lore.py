#!/usr/bin/env python3
"""Build the lore chatter corpus for mod-botlore.

Writes data/sql/db-world/base/botlore_lore_text.sql, which the module ships
and the core's database updater applies at startup for every enabled module
(UpdateFetcher::ReceiveIncludedDirectories walks
modules/<name>/data/sql/db-world). Re-running this after editing the corpus
changes the file's hash, and the updater re-applies a MODULE file whose hash
changed, so a restart is enough to publish new lines - or ".botlore reload"
after applying the file by hand, with no restart at all.

The corpus lives here rather than in SQL because it is prose: it needs to be
readable and editable. This script turns it into an idempotent SQL file.

Filters on a line are all "0 means any", and mod-botlore prefers the most
specific line that matches, so a Duskwood line beats a generic one in Duskwood
and a Hogger line beats both when Hogger dies.

Placeholders substituted at speak time: %zone %area %target %quest %item
%name. Text must stay under 255 characters and must not contain a vertical bar
(the direct Player::Say path skips the hyperlink validation the chat opcode
would have done).

There is deliberately no %level. A character who announces a number is
describing a game statistic, which breaks the fiction the corpus exists to
support; one who notices their hands are steadier than yesterday does not. The
module still substitutes the token if it ever meets one, but line() refuses it,
so it cannot come back by accident.
"""

import glob
import os
import re

# ---------------------------------------------------------------- personalities
# Must match the Personality enum in mod_botlore.cpp.
DEVOUT, GRIM, SCHOLAR, BOASTFUL, WRY, HAUNTED, SAVAGE, SINISTER = (
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80)

PERSONALITY_NAMES = {
    DEVOUT: "devout", GRIM: "grim", SCHOLAR: "scholar", BOASTFUL: "boastful",
    WRY: "wry", HAUNTED: "haunted", SAVAGE: "savage", SINISTER: "sinister",
}

# ---------------------------------------------------------------------- classes
WARRIOR, PALADIN, HUNTER, ROGUE, PRIEST = 1, 2, 4, 8, 16
DEATH_KNIGHT, SHAMAN, MAGE, WARLOCK, DRUID = 32, 64, 128, 256, 1024

CLASS_NAMES = {
    WARRIOR: "warrior", PALADIN: "paladin", HUNTER: "hunter", ROGUE: "rogue",
    PRIEST: "priest", DEATH_KNIGHT: "death knight", SHAMAN: "shaman",
    MAGE: "mage", WARLOCK: "warlock", DRUID: "druid",
}

# --------------------------------------------------------------------- channels
SAY, EMOTE, PARTY, GUILD = 0, 1, 2, 3

# ------------------------------------------------------------- creature ranks
# CreatureTemplate::rank. -1 is "any"; 0 is a real rank so it cannot be the
# wildcard the way the masks are.
RANK_ANY, RANK_NORMAL, RANK_ELITE, RANK_RARE_ELITE, RANK_WORLD_BOSS, RANK_RARE = -1, 0, 1, 2, 3, 4

# ------------------------------------------------------------- item qualities
# 0 means "no bound at that end", so an epic-only line is minq=EPIC and a line
# that must not fire on epics is maxq=RARE.
POOR, COMMON, UNCOMMON, RARE, EPIC, LEGENDARY = 0, 1, 2, 3, 4, 5

# ---------------------------------------------------------------- group state
# Must match BotLoreSelection::GroupState.
GROUP_ANY, GROUP_ALONE, GROUP_GROUPED, GROUP_WITH_PLAYER = 0, 1, 2, 3

ALLIANCE, HORDE = 0, 1

rows = []


def line(trigger, text, zone=0, area=0, creature=0, race=0, cls=0,
         personality=0, quest=0, item=0, iclass=-1, isub=-1, gender=-1,
         spec=0, team=-1, minlvl=0, maxlvl=0, rank=-1, minq=0, maxq=0,
         group=GROUP_ANY, channel=SAY, weight=1, comment=None):
    assert len(text) <= 255, f"too long ({len(text)}): {text}"
    assert "|" not in text, f"contains a bar: {text}"
    # Bots do not name their level. Say what changed in the body instead.
    assert "%level" not in text, f"names the level: {text}"
    rows.append(dict(trigger=trigger, text=text, zone=zone, area=area,
                     creature=creature, race=race, cls=cls,
                     personality=personality, quest=quest, item=item,
                     iclass=iclass, isub=isub, gender=gender, spec=spec,
                     team=team, minlvl=minlvl, maxlvl=maxlvl, rank=rank,
                     minq=minq, maxq=maxq, group=group, channel=channel,
                     weight=weight, comment=comment))


def many(trigger, texts, **kw):
    for t in texts:
        line(trigger, t, **kw)

# =============================================================================
# Generic fallbacks. Deliberately sparse and plain - these only surface when
# nothing more specific matches, so they must never sound out of place.
# =============================================================================

many("zone_enter", [
    "So this is %zone.",
    "%zone. I have heard the name often enough.",
    "Keep your eyes open. %zone does not forgive the careless.",
    "%area. We are further from help than I would like.",
])

many("quest_accept", [
    "%quest. It will be done.",
    "I have given my word on %quest. That is enough.",
    "They asked for help. I do not intend to refuse.",
])

many("quest_complete", [
    "%quest is finished. Let the word go back.",
    "Done, and no worse for it.",
    "That is one debt settled.",
])

many("kill_boss", [
    "%target falls. Remember the name, and why it ended here.",
    "It is over. %target will trouble no one else.",
])

many("death", [
    "Not... yet...",
    "%target. Remember that name for me.",
])

many("level_up", [
    "Stronger than I was. Not yet what I must be.",
    "Stronger than I was. The road does not get shorter.",
])

many("loot_rare", [
    "%item. Someone carried this a long way before I did.",
    "%item. Better in my hands than rusting out here.",
])

many("combat_start", [
    "Weapons. Now.",
    "%target has made its choice.",
])

many("idle", [
    "A moment's rest. No more than that.",
])

# =============================================================================
# By archetype. This is the layer that gives two warriors standing in the same
# field different voices.
# =============================================================================

PERSONALITY_LINES = {
    DEVOUT: {
        "zone_enter": [
            "The Light reaches even into %zone. It only needs someone to carry it.",
            "There is suffering here. That is reason enough to have come.",
            "%zone. I will walk it as a servant, not a conqueror.",
            "Whatever waits in %area, it does not stand above the Light.",
        ],
        "quest_accept": [
            "%quest. Service asked for is service given.",
            "I did not come this far to weigh whether a thing is convenient.",
            "If it spares one life, %quest is worth the walking.",
        ],
        "quest_complete": [
            "It is done, and not by my strength alone.",
            "%quest is finished. May it hold longer than I do.",
        ],
        "kill_boss": [
            "%target is judged. I take no pleasure in it.",
            "Rest now, %target. Whatever you were before this, rest.",
        ],
        "death": [
            "Into the Light...",
            "I have no regrets. Only things left undone.",
        ],
        "level_up": [
            "Strength is only a loan. I mean to spend it well.",
        ],
        "combat_start": [
            "Stand down, %target. I would rather you lived.",
            "By the Light, then. Let it be quick.",
        ],
        "idle": [
            "I should pray. I always mean to, and the day always fills.",
        ],
    },

    GRIM: {
        "zone_enter": [
            "%zone. Another place that will not remember us.",
            "I have seen the maps. They do not show how much of %zone is graves.",
            "Nothing good has come out of %area in a long time.",
            "We are not the first to walk into %zone hoping. Look how that ended.",
        ],
        "quest_accept": [
            "%quest. It will cost more than they said. They always do.",
            "I will take it. Someone has to, and the others have families.",
        ],
        "quest_complete": [
            "%quest is done. It changes less than you would hope.",
            "Finished. Next week there will be another just like it.",
        ],
        "kill_boss": [
            "%target is dead. Something worse is already learning the road here.",
            "One down. The list does not get shorter, it only changes names.",
        ],
        "death": [
            "I knew how this ended. I came anyway.",
            "Tell them... it was quick. Lie if you have to.",
        ],
        "level_up": [
            "Stronger. It has never once been enough before.",
        ],
        "combat_start": [
            "Here we are again, then.",
            "%target. Come on. Get it over with.",
        ],
        "idle": [
            "Every road out here goes somewhere worse.",
        ],
    },

    SCHOLAR: {
        "zone_enter": [
            "%zone. I have read three accounts of this place and none of them agree.",
            "Look at the stonework in %area. Someone built that to last, and failed.",
            "There are things recorded about %zone that I had hoped were exaggeration.",
            "I should be taking notes. I am always saying that.",
        ],
        "quest_accept": [
            "%quest. I would like to know why it needs doing, not only that it does.",
            "Curious. I will take it, if only to see the shape of the answer.",
        ],
        "quest_complete": [
            "%quest is resolved. The explanation was stranger than the task.",
            "Done. I have more questions than when I started, which is usually a good sign.",
        ],
        "kill_boss": [
            "%target. I will write this down properly, while the details are fresh.",
            "Remarkable. I would have liked to study %target rather than kill it.",
        ],
        "death": [
            "I had almost... worked it out...",
            "Someone should record this. Properly.",
        ],
        "level_up": [
            "Understanding and strength are not the same thing. I am told they help each other.",
        ],
        "combat_start": [
            "I would rather have asked it questions.",
            "%target. Interesting. Unfortunate.",
        ],
        "idle": [
            "There is a library somewhere with the answer to all this, and I am standing in a field.",
        ],
    },

    BOASTFUL: {
        "zone_enter": [
            "%zone at last. They will tell stories about what I do here.",
            "So this is %zone. Smaller than the songs make it sound.",
            "Let %area take a good look. It will not forget me.",
        ],
        "quest_accept": [
            "%quest. Finally, something worth my time.",
            "They came to me for this. Naturally.",
        ],
        "quest_complete": [
            "%quest. Done, and done well, and I will be telling it that way.",
            "Another one. Someone really ought to be writing these down.",
        ],
        "kill_boss": [
            "%target! Let it be known who did this.",
            "They said %target could not be beaten. They say a great many things.",
        ],
        "death": [
            "This... is not how the song goes...",
            "Do not tell them it ended like this.",
        ],
        "level_up": [
            "Stronger again, and I am only getting started.",
        ],
        "combat_start": [
            "Good. I was getting bored.",
            "%target. You have picked the wrong fight and the wrong opponent.",
        ],
        "idle": [
            "I could be famous by now if the roads were shorter.",
        ],
    },

    WRY: {
        "zone_enter": [
            "%zone. Somehow even worse than advertised.",
            "Lovely. Who picked %area? I want a word.",
            "%zone. Every third thing here wants to eat me, and the rest are just rude.",
            "I am told %zone has charm. I am told a lot of things.",
        ],
        "quest_accept": [
            "%quest. Of course. Why would anyone do their own work.",
            "Let me guess - it is further than they said and pays less.",
        ],
        "quest_complete": [
            "%quest. Done. I would like it noted that nobody thanked me properly.",
            "Finished. I will send the bill to whoever thought this was simple.",
        ],
        "kill_boss": [
            "%target. Terrifying reputation, disappointing in person.",
            "Well. %target will not be doing that again.",
        ],
        "death": [
            "Oh, that is just typical.",
            "Fine. Fine. I did not want to live forever anyway.",
        ],
        "level_up": [
            "Stronger, and still nobody sends a horse.",
        ],
        "combat_start": [
            "Right. Let us all do something stupid together.",
            "%target, I was having a perfectly reasonable day.",
        ],
        "idle": [
            "Nobody ever mentions how much of heroism is walking.",
        ],
    },

    HAUNTED: {
        "zone_enter": [
            "I have been in %zone before. I would rather not have come back.",
            "%zone smells the same as it did. That is the worst of it.",
            "I knew people who died in %area. Nobody ever came for them.",
            "Do not ask me about %zone. Not tonight.",
        ],
        "quest_accept": [
            "%quest. I have done work like this before. It did not help then either.",
            "I will do it. Perhaps this one will stay done.",
        ],
        "quest_complete": [
            "%quest is finished. It does not give anything back.",
            "Done. I thought I would feel something.",
        ],
        "kill_boss": [
            "%target is dead. It is too late for the ones I wanted it to be for.",
            "There. Is that enough? It never is.",
        ],
        "death": [
            "I am sorry. I am so sorry.",
            "At last...",
        ],
        "level_up": [
            "Stronger now. I was not strong enough then.",
        ],
        "combat_start": [
            "I have fought your kind before.",
            "Not again. Not this time.",
        ],
        "idle": [
            "I keep expecting to see a face I know out here.",
        ],
    },

    SAVAGE: {
        "zone_enter": [
            "%zone. I can smell the hunting from here.",
            "Good ground. Things die well in %area.",
            "%zone is honest, at least. Everything here wants something.",
        ],
        "quest_accept": [
            "%quest. Point me at it.",
            "Enough talk. Where is the thing that needs killing?",
        ],
        "quest_complete": [
            "It is done. The blood has dried already.",
            "%quest. Easy meat.",
        ],
        "kill_boss": [
            "%target was strong. Good. The weak ones teach nothing.",
            "%target fought. I will remember that much of it.",
        ],
        "death": [
            "A better death than most get...",
            "Tell them I did not run.",
        ],
        "level_up": [
            "The hunt makes me. Nothing else does.",
        ],
        "combat_start": [
            "Yes. Come on.",
            "%target. Run, and it lasts longer.",
        ],
        "idle": [
            "Too quiet. Quiet means something is waiting.",
        ],
    },

    SINISTER: {
        "zone_enter": [
            "%zone. So much power here, and no one with the wit to take it.",
            "%area is riddled with old wounds. Wounds can be opened.",
            "They fear %zone. Fear is only unclaimed advantage.",
        ],
        "quest_accept": [
            "%quest. And what do they imagine I will do with what I find?",
            "I accept. They never ask what it costs me. Or anyone.",
        ],
        "quest_complete": [
            "%quest. Done, and I kept the interesting part.",
            "They have what they asked for. I have what I wanted.",
        ],
        "kill_boss": [
            "%target. Such a waste, to die without being useful.",
            "There is still something left in %target worth taking.",
        ],
        "death": [
            "This is not... the arrangement...",
            "I will be back. One way or another.",
        ],
        "level_up": [
            "Power comes to those who do not flinch from it.",
        ],
        "combat_start": [
            "You will regret being interesting.",
            "%target. Hold still. This is worth watching.",
        ],
        "idle": [
            "Everyone out here is a resource. Most of them do not know it yet.",
        ],
    },
}

for _p, _triggers in PERSONALITY_LINES.items():
    for _trigger, _texts in _triggers.items():
        many(_trigger, _texts, personality=_p,
             comment=f"{PERSONALITY_NAMES[_p]}")

# =============================================================================
# By class. Identity rather than mood - what this character *is*, as opposed to
# how they take it.
# =============================================================================

CLASS_LINES = {
    WARRIOR: {
        "zone_enter": [
            "No spells, no omens. Just ground to hold and something on it worth hitting.",
            "I will take the front. I always take the front.",
        ],
        "combat_start": ["Steel settles this.", "Get behind me."],
        "kill_boss": ["It came down to arms and footing, the way it always does."],
        "level_up": ["Heavier armour, longer reach. That is all progress means to me."],
    },
    PALADIN: {
        "zone_enter": [
            "I swore an oath that did not name a place. It counts here too.",
            "The Light is not thinner this far from a chapel. Only lonelier.",
        ],
        "combat_start": ["The Light gives me leave.", "You will not pass me."],
        "kill_boss": ["Judgement, not vengeance. I have to keep saying it."],
        "death": ["My oath held. That is what matters."],
    },
    HUNTER: {
        "zone_enter": [
            "Fresh tracks. Two days old, maybe three, and heavier than a man.",
            "Wind is wrong here. Everything will smell us coming.",
        ],
        "combat_start": ["Range first. Always range first.", "Mark it. Take it."],
        "kill_boss": ["It was a better hunt than most. I will grant it that."],
        "idle": ["Out here you eat what you track. Suits me."],
    },
    ROGUE: {
        "zone_enter": [
            "Too much open ground. I do not like being seen coming.",
            "Somebody in %zone is paying somebody else. There always is.",
        ],
        "combat_start": ["From behind, ideally.", "This will be over before you place me."],
        "kill_boss": ["Quick, quiet, and nobody has to hear about it."],
        "loot_rare": ["%item. Nobody will miss what nobody knows about."],
    },
    PRIEST: {
        "zone_enter": [
            "There are unquiet dead here. I can feel them pressing.",
            "So many buried without rites. Someone should have come sooner.",
        ],
        "combat_start": ["I would rather mend than break. Rather, not always.", "Be still."],
        "kill_boss": ["I will say the words over it. Even for this one."],
        "death": ["The Light does not abandon. Not even now."],
    },
    DEATH_KNIGHT: {
        "zone_enter": [
            "I have marched through %zone before, under another's will. I remember the cold.",
            "The living flinch from me here. They are not wrong to.",
        ],
        "combat_start": ["Your death is already written.", "Come. I am used to cold work."],
        "kill_boss": ["Another thing that should have stayed dead. I know the feeling."],
        "death": ["I have died before. It was worse the first time."],
    },
    SHAMAN: {
        "zone_enter": [
            "The elements are restless in %zone. Something here was done badly.",
            "The ancestors have little to say about %zone. That worries me more.",
        ],
        "combat_start": ["The elements lend me their anger.", "Earth and storm, with me."],
        "kill_boss": ["Its spirit is loose now. I hope something takes it in hand."],
        "idle": ["Listen. The wind changes its mind constantly out here."],
    },
    MAGE: {
        "zone_enter": [
            "The ley lines run strangely under %zone. I can feel them tugging.",
            "I could have stepped here in an instant. Instead, we walk. Marvellous.",
        ],
        "combat_start": ["Let us see how it handles frost.", "Stand clear. This gets bright."],
        "kill_boss": ["Reduced to its components. Crudely, but effectively."],
        "loot_rare": ["%item. There is enchantment worked into this, and clumsily."],
    },
    WARLOCK: {
        "zone_enter": [
            "Something in %zone is thin. The Nether presses closer here.",
            "My companion is uneasy. It does not like %zone, and it does not like much.",
        ],
        "combat_start": ["Burn, then.", "I have worse things than me on a leash."],
        "kill_boss": ["Its soul had weight. Most do not."],
        "death": ["The bargain... was not... this..."],
    },
    DRUID: {
        "zone_enter": [
            "The balance is off in %zone. Something takes more than it returns.",
            "The Dream shows %zone greener than this. It is always kinder than waking.",
        ],
        "combat_start": ["Nature does not negotiate.", "You have taken too much."],
        "kill_boss": ["It will feed the soil. That is more use than it was alive."],
        "idle": ["Everything here is growing or rotting. Usually both."],
    },
}

for _c, _triggers in CLASS_LINES.items():
    for _trigger, _texts in _triggers.items():
        many(_trigger, _texts, cls=_c, comment=f"{CLASS_NAMES[_c]}")

# =============================================================================
# Zones. The layer players actually notice, so it carries the most weight.
# Zone ids are the real AreaTable.dbc values for top-level zones.
# =============================================================================

ZONE_LINES = {
    # ---- Eastern Kingdoms ------------------------------------------------
    12: [  # Elwynn Forest
        "Elwynn. Every farm here feeds Stormwind, and every farmer knows it.",
        "Quiet fields, and Hogger's kin in the treeline. It never lasts long.",
        "The Abbey bells carry a long way in %zone.",
        "Peaceful, they call it. Ask the Westbrook garrison about peaceful.",
    ],
    40: [  # Westfall
        "Westfall was the breadbasket once. Now it grows scarecrows and harvest golems.",
        "The Defias took these farms and nobody in Stormwind came. People remember.",
        "Sentinel Hill still flies the flag. Barely.",
        "Dust and broken ploughs. This land was betrayed before it was abandoned.",
    ],
    44: [  # Redridge Mountains
        "Lake Everstill is clean water and bad company. Gnolls on both shores.",
        "Redridge holds because Lakeshire refuses to move. Stubbornness as strategy.",
        "Blackrock orcs in the hills. This close to Stormwind, and nobody marches.",
    ],
    10: [  # Duskwood
        "They say Morbent Fel still walks these woods.",
        "Duskwood was Brightwood before the night settled in and stayed.",
        "Darkshire bars its doors at dusk and no one calls them cowards.",
        "Do not follow the lights off the road. That is how Raven Hill filled up.",
        "Something worse than worgen came through here. The trees remember it.",
    ],
    33: [  # Stranglethorn Vale
        "Booty Bay pays no king and answers no flag. It works, somehow.",
        "Zul'Gurub is up there through the canopy, and the Gurubashi still serve it.",
        "Everything in Stranglethorn is bigger than it has any right to be.",
        "Tigers, trolls, and pirates. Pick which one kills you.",
    ],
    8: [  # Swamp of Sorrows
        "The Dark Portal is close. You can taste it in the water.",
        "Stonard sits in this muck on purpose. That should tell you something.",
        "The Temple of Atal'Hakkar is sunk out there, and still not finished with us.",
    ],
    4: [  # Blasted Lands
        "The Dark Portal broke this land and left it broken. Nothing has healed.",
        "Nethergarde still stands watch. Someone has to.",
        "Red earth, red sky. The Horde came through here the first time.",
    ],
    41: [  # Deadwind Pass
        "Karazhan looms over %zone and nobody talks about who lived there.",
        "Deadwind. Not one living thing on this road, and it is not quiet.",
    ],
    46: [  # Burning Steppes
        "Blackrock above, Dark Iron below, and the Dragonmaw were here before both.",
        "The ash never settles in the Steppes. It just moves around.",
    ],
    51: [  # Searing Gorge
        "The Dark Irons dug too greedily and Ragnaros answered. This is the answer.",
        "Thorium Point makes a living off a wound in the world.",
    ],
    3: [  # Badlands
        "The Badlands are old. Titan-old. Uldaman is down there under all this rock.",
        "Nothing grows here and something still eats. Work that out.",
    ],
    38: [  # Loch Modan
        "The dam holds the Loch and the dwarves hold the dam. Both have been tested.",
        "Ironband is digging up Titan stone at Ironband's Excavation. It will end badly.",
        "Troggs in the hills again. There are always troggs in the hills.",
    ],
    1: [  # Dun Morogh
        "Cold, and the forge-smoke from Ironforge keeps it bearable.",
        "Gnomeregan is sealed and irradiated and full of its own people. A tragedy nobody solved.",
        "Kharanos brews better than it has any right to at this altitude.",
    ],
    11: [  # Wetlands
        "Dragonmaw ruins and Grim Batol behind them. That mountain is not empty.",
        "Menethil Harbour is the last friendly roof before the Wetlands swallow you.",
        "Half of %zone is under water and the other half wishes it were.",
    ],
    45: [  # Arathi Highlands
        "Stromgarde is a ruin fought over by its own heirs. Arathor deserved better.",
        "These highlands were the first human kingdom. Look at them now.",
    ],
    267: [  # Hillsbrad Foothills
        "Southshore and Tarren Mill, close enough to shout across. They do more than shout.",
        "Durnholde is rubble. Thrall broke his chains there and nothing has been the same.",
    ],
    36: [  # Alterac Mountains
        "Alterac betrayed the Alliance and then fell apart on its own. Poetic, in a way.",
        "The Syndicate picks over what is left of a kingdom up here.",
    ],
    130: [  # Silverpine Forest
        "Silverpine belongs to the Forsaken now, and to the worgen who do not care.",
        "Shadowfang Keep is up that hill. Arugal's work is still walking around inside.",
        "The trees here have been dying for years and never quite finish.",
    ],
    85: [  # Tirisfal Glades
        "Lordaeron's soil. The Forsaken farm it now, after a fashion.",
        "The Scarlet Crusade holds the monastery and calls it holy. Zealots and corpses.",
        "The Undercity is beneath the ruins of the old capital. The symbolism is not subtle.",
    ],
    28: [  # Western Plaguelands
        "Andorhal. The plague came out of the granaries there and ended a kingdom.",
        "The Cenarion Circle is trying to heal this. It is going slowly.",
        "Even the grass here comes up wrong.",
    ],
    139: [  # Eastern Plaguelands
        "Stratholme. Do not ask what Arthas did there. Everyone already knows.",
        "The Scourge still holds most of %zone. The Argent Dawn holds the rest by will alone.",
        "Naxxramas hung over this land once. The shadow of it has not lifted.",
    ],
    47: [  # The Hinterlands
        "Vilebranch trolls and Wildhammer gryphon riders. An old quarrel, still warm.",
        "Aerie Peak is the last good ale for a long way in any direction.",
    ],
    25: [  # Blackrock Mountain
        "Blackrock. Orcs above, Dark Iron below, and something older in the deep.",
        "Nefarian and Ragnaros share a mountain and hate each other. We benefit.",
    ],
    1519: [  # Stormwind City
        "Stormwind. Rebuilt by stonemasons who were never paid. That debt started a war.",
        "The Cathedral district is the only quiet part of this city.",
    ],
    1537: [  # Ironforge
        "The Great Forge never goes out. Neither does the argument about the Three Hammers.",
        "Ironforge smells of coal and old stone. It smells like safety.",
    ],
    1497: [  # Undercity
        "The Undercity. Built under a king's grave by the people he failed.",
        "Apothecary work in the Royal Quarter. Best not to ask what for.",
    ],

    # ---- Kalimdor --------------------------------------------------------
    14: [  # Durotar
        "Durotar is hard ground. Thrall chose it anyway, and that was the point.",
        "Orgrimmar rises out of this canyon like a fist. Fitting.",
        "Red dust, scorpids, and the sea to the east. It is ours, and it was earned.",
    ],
    215: [  # Mulgore
        "Mulgore is the kindest land in Kalimdor and the tauren nearly lost it.",
        "Thunder Bluff sits on the mesas above. You can see it from anywhere here.",
        "The Venture Company would strip all this for ore if they were let.",
    ],
    17: [  # The Barrens
        "Water is worth more than gold out here in %zone.",
        "The Crossroads holds because caravans need somewhere to stop.",
        "Quilboar in the thickets, centaur on the plains. Neither negotiates.",
        "The Barrens go on and on. Halfway across, you stop believing in the other side.",
    ],
    141: [  # Teldrassil
        "Teldrassil grew out of the sea in a night. The night elves have not stopped paying for it.",
        "Darnassus is up through the branches. The whole city is a tree's idea of architecture.",
        "The furbolgs here were peaceful once. Something turned them.",
    ],
    148: [  # Darkshore
        "Auberdine clings to this coast. The sea keeps trying to take it back.",
        "There are ruins under the water here older than any empire still standing.",
        "The Twilight Lovers dig at things on this shore that should be left buried.",
    ],
    331: [  # Ashenvale
        "The Warsong cut these trees for war machines. The Sentinels have not forgiven it.",
        "Ashenvale is old growth. You can feel the age of it pressing down.",
        "Every road in %zone has a Sentinel watching it, whether you see her or not.",
    ],
    406: [  # Stonetalon Mountains
        "The Venture Company is logging Stonetalon flat and calling it commerce.",
        "Windshear Crag is a wound with a mine in the middle of it.",
    ],
    405: [  # Desolace
        "Desolace earned the name. The centaur khans finished what the land started.",
        "Even the Cenarion Circle mostly gave up on %zone.",
    ],
    15: [  # Dustwallow Marsh
        "Theramore stands alone out here, and Jaina holds it together by herself.",
        "Onyxia's lair is somewhere in this marsh. People have stopped looking.",
        "Dustwallow is mud, dragonkin and bad decisions.",
    ],
    400: [  # Thousand Needles
        "Mesas and wind. The Shimmering Flats were a salt pan before the racers came.",
        "Everything in %zone is either climbing or falling.",
    ],
    357: [  # Feralas
        "Feralas is green enough to forget yourself in. Do not. The yeti are patient.",
        "Dire Maul was a night elf citadel. The ogres redecorated.",
    ],
    440: [  # Tanaris
        "Gadgetzan sells water at a markup and nobody argues, because nobody else has any.",
        "The Caverns of Time are out here. The bronze flight guards them and explains nothing.",
        "Tanaris is one long argument between the sun and everything else.",
    ],
    490: [  # Un'Goro Crater
        "Un'Goro should not exist. A jungle in a crater in a desert, full of devilsaurs.",
        "The Marshal's Refuge studies %zone from inside a cave, which tells you plenty.",
    ],
    1377: [  # Silithus
        "Silithus is a hive with a desert on top. The qiraji are still down there.",
        "The Scarab Wall still stands. The war behind it is not finished, only paused.",
    ],
    361: [  # Felwood
        "Felwood is what happens when fel taint sinks into old forest. Nothing here is clean.",
        "The Timbermaw hold their pass against the corruption and trust nobody. Wisely.",
    ],
    618: [  # Winterspring
        "Winterspring is cold enough to be honest. Everestiff Owl Wing Tea Company notwithstanding.",
        "Everlook trades with anyone who can reach it. Few can.",
        "The frostsabers here were hunted almost to nothing. Almost.",
    ],
    16: [  # Azshara
        "Azshara was the queen's own land. The ruins still have her taste in them.",
        "Highborne ghosts and naga on the shore. Ten thousand years and they are still here.",
    ],
    493: [  # Moonglade
        "Moonglade. No weapons drawn here, by very old agreement.",
        "The Cenarion Circle keeps this place green while the rest of the world burns.",
    ],
    616: [  # Hyjal
        "Nordrassil is up there, wounded. The Aspects gave everything at this mountain.",
        "Archimonde died on this slope. That is not a thing you stand on lightly.",
    ],
    1637: [  # Orgrimmar
        "Orgrimmar. Thrall built a capital out of a canyon and sheer will.",
        "The Valley of Wisdom smells of leather and smoke. Home, for most of us.",
    ],
    1638: [  # Thunder Bluff
        "Thunder Bluff is peaceful in a way no other capital manages.",
        "Cairne's word carries further up here than any king's decree.",
    ],
    1657: [  # Darnassus
        "Darnassus is quiet on purpose. Ten thousand years teaches you patience.",
        "The Temple of the Moon. Even the arguments here are whispered.",
    ],
}

ZONE_LINES.update({
    # ---- Outland ---------------------------------------------------------
    3483: [  # Hellfire Peninsula
        "Through the Portal at last. Outland is a corpse of a world and we are standing on it.",
        "Hellfire Citadel dominates this whole plain. Everything here orbits that fortress.",
        "The sky is wrong. You can see the Nether through the cracks in it.",
        "Thrallmar and Honor Hold, glaring at each other across a dead world. Old habits.",
    ],
    3521: [  # Zangarmarsh
        "Giant mushrooms instead of trees. Draenor did not survive, but it got strange.",
        "The naga are draining the marsh from Coilfang and the broken have nowhere to go.",
        "Everything here glows faintly. I have stopped finding that reassuring.",
    ],
    3519: [  # Terokkar Forest
        "Auchindoun blew open under this forest and the bone wastes are what came out.",
        "The arakkoa remember being something greater. They are not wrong.",
        "Shattrath is close. The only place in Outland where nobody is fighting.",
    ],
    3518: [  # Nagrand
        "Nagrand. This is what Draenor looked like before. The orcs came from here.",
        "Garadar still stands, and Greatmother Geyah with it.",
        "Clefthoof on the plains and floating rock overhead. Beautiful, and it hurts to look at.",
    ],
    3522: [  # Blade's Edge Mountains
        "Gruul's sons broke these ridges. The ogres have not improved them.",
        "Dragon bones the size of buildings out on the spires. The Dragonmaw did that.",
    ],
    3523: [  # Netherstorm
        "Netherstorm is where Outland is actively coming apart. Kael'thas is mining the pieces.",
        "Manaforges pulling raw Nether out of the sky. Nothing about this is safe.",
    ],
    3520: [  # Shadowmoon Valley
        "Black Temple ahead. Illidan is in there, and he was not always the enemy.",
        "The ground bleeds fel here. Shadowmoon has been burning for a very long time.",
    ],
    3703: [  # Shattrath City
        "Shattrath. Aldor and Scryer, one city, two grudges, no bloodshed. Mostly.",
        "The Naaru hold this place together. You can feel A'dal from the Terrace.",
    ],
    3430: [  # Eversong Woods
        "Eversong stayed golden. The Scourge came within a mile of this and the trees kept their colour.",
        "Silvermoon is close. The quel'dorei became sin'dorei and the woods did not object.",
    ],
    3433: [  # Ghostlands
        "This is where the Scourge walked to Quel'Thalas. Deatholme is still theirs.",
        "The Ghostlands were Eversong once. That is the whole tragedy in one sentence.",
    ],
    3524: [  # Azuremyst Isle
        "The Exodar crashed here and the draenei are still picking up the pieces.",
        "Nothing on this island asked for us. We landed on it anyway.",
    ],
    3525: [  # Bloodmyst Isle
        "The crash bled fel into this whole island. Look what it did to the wildlife.",
        "Bloodmyst was green before we fell out of the sky onto it.",
    ],
    4080: [  # Isle of Quel'Danas
        "The Sunwell. Kil'jaeden is coming through it, and we are the ones standing here.",
        "Every faction sent their best to this island. That should frighten you.",
    ],
    3487: [  # Silvermoon City
        "Silvermoon repaired itself in gold and denial. It is still beautiful.",
        "The Sunfury rebuilt this city while grieving. Do not mistake the polish for peace.",
    ],
    3557: [  # The Exodar
        "The Exodar is a broken ship we live inside. We call it a city because we must.",
        "Velen is here somewhere, older than any of this, still patient.",
    ],

    # ---- Northrend -------------------------------------------------------
    3537: [  # Borean Tundra
        "Northrend at last. Cold enough that the cold is the enemy before anything else.",
        "Warsong Hold drilled straight into the tundra. Subtle as ever.",
        "The blue flight is at war with magic itself out here. Malygos has lost his reason.",
    ],
    495: [  # Howling Fjord
        "The vrykul built these halls. Look at the doorways - they were never our size.",
        "Utgarde Keep is up that cliff, and the vrykul in it are waking.",
        "Valgarde holds the harbour by stubbornness and steep walls.",
    ],
    65: [  # Dragonblight
        "Dragonblight. Every dragon that can reach it comes here to die.",
        "Wyrmrest Temple stands over an entire plain of dragon bones.",
        "Naxxramas hangs over this land now. It followed us north.",
        "The Wrathgate is that way. Whatever happens there will be remembered.",
    ],
    394: [  # Grizzly Hills
        "Good timber, good water, and a war between furbolg, worgen and the Horde over it.",
        "Drak'Tharon Keep sits on the border, changed hands more times than anyone counts.",
    ],
    66: [  # Zul'Drak
        "The Drakkari are killing their own gods for power. It is working, and it is horrifying.",
        "Gundrak is up there. An empire eating itself to survive the Scourge.",
    ],
    3711: [  # Sholazar Basin
        "A warm valley in the middle of Northrend. The Titans left machinery running here.",
        "Sholazar is the only green thing for a thousand miles. Both Cults want it.",
    ],
    67: [  # The Storm Peaks
        "Ulduar is up here, and the Titans did not build it to be opened.",
        "The iron dwarves were made, not born. That is a worse thought the longer you hold it.",
        "Thorim and Hodir, and whatever is under the mountain giving them orders.",
    ],
    210: [  # Icecrown
        "Icecrown. The Lich King is up there on his throne, and he knows we came.",
        "The Argent Crusade and the Knights of the Ebon Blade, side by side. It took this to manage it.",
        "Saronite in the ground, whispering. Do not listen to it for long.",
        "Everything in %zone is his. The sky, the stone, the cold. We are trespassing.",
    ],
    2817: [  # Crystalsong Forest
        "Crystalsong. The trees turned to crystal when Dalaran tore itself loose above.",
        "Beautiful, and it rings when the wind moves. Nothing lives here for long.",
    ],
    4197: [  # Wintergrasp
        "Wintergrasp Fortress changes hands every few hours and the titan relics underneath never move.",
        "This whole valley is a siege that nobody wins and nobody can afford to leave.",
    ],
    4395: [  # Dalaran
        "Dalaran flies now. The Kirin Tor decided the ground was optional.",
        "A city in the sky above Icecrown. Rhonin means it as a statement.",
    ],
})

for _zone, _texts in ZONE_LINES.items():
    many("zone_enter", _texts, zone=_zone, comment=f"zone {_zone}")

# Zone crossed with archetype - the densest layer, kept to the zones players
# spend the most time in so the effort shows.
ZONE_PERSONALITY = {
    10: {  # Duskwood
        GRIM: ["Duskwood is honest about what it is. I respect that in a place."],
        DEVOUT: ["So many unconsecrated graves at Raven Hill. I will do what I can."],
        WRY: ["Perpetual night, worgen, and a town called Darkshire. Nobody was being subtle."],
        HAUNTED: ["I lost someone on this road. The trees have not moved since."],
        SCHOLAR: ["The night here is unnatural. Something is sustaining it, and I want to know what."],
    },
    40: {  # Westfall
        GRIM: ["Westfall starved because nobody in the keep cared. That is how kingdoms rot."],
        WRY: ["Nothing but dust, gnolls and a vague sense of political grievance."],
        DEVOUT: ["These people were abandoned. I will not add to it."],
        BOASTFUL: ["The Defias made their name out here. I will make a better one."],
    },
    17: {  # The Barrens
        WRY: ["Everyone warns you about the Barrens. Nobody mentions how long they are."],
        SAVAGE: ["Good hunting in %zone. Everything out here is lean and mean and fast."],
        SCHOLAR: ["The Barrens were fertile once. Something changed the rainfall and nobody wrote it down."],
        BOASTFUL: ["I will cross the Barrens end to end and make it sound heroic afterwards."],
    },
    85: {  # Tirisfal Glades
        HAUNTED: ["I remember Lordaeron. Not all of us were allowed to forget."],
        GRIM: ["Tirisfal is where a kingdom was buried. We live in the hole it left."],
        SINISTER: ["The apothecaries here are doing useful work. Distasteful, but useful."],
        DEVOUT: ["The Scarlet Crusade calls this holy ground. Zeal is not the same as faith."],
    },
    139: {  # Eastern Plaguelands
        GRIM: ["The Scourge held %zone for years. Some of it will never come back."],
        DEVOUT: ["The Argent Dawn stands here on almost nothing. I will stand with them."],
        HAUNTED: ["Stratholme is that way. I do not intend to look at it."],
        SINISTER: ["So much death worked into this soil, and all of it going to waste."],
    },
    33: {  # Stranglethorn Vale
        SAVAGE: ["Stranglethorn is one long hunt. I could stay here."],
        WRY: ["Jungle, pirates, trolls, and a tiger for every tree. Restful."],
        SCHOLAR: ["The Gurubashi ruins here predate every kingdom on this continent."],
    },
    3483: {  # Hellfire Peninsula
        SCHOLAR: ["A world torn apart and still holding together. I could study this for a lifetime."],
        GRIM: ["Draenor died and we walked into the corpse looking for advantage."],
        HAUNTED: ["My people came from here. There is nothing left worth recognising."],
        BOASTFUL: ["A whole new world to make a name in. About time."],
    },
    210: {  # Icecrown
        GRIM: ["This is where it ends, one way or the other. I have made my peace."],
        DEVOUT: ["The Light reaches even here. It has to. Everything else has failed."],
        HAUNTED: ["He took people I knew. I have come a very long way for this."],
        BOASTFUL: ["The Lich King. Now that is a name worth putting mine next to."],
        SINISTER: ["All that power on one throne. Someone will inherit it."],
    },
    65: {  # Dragonblight
        SCHOLAR: ["An entire plain of dragon remains. There is more history in this ground than in any library."],
        HAUNTED: ["Everything comes here to die. I understand the impulse."],
        DEVOUT: ["Wyrmrest still holds. While the Aspects stand, so do we."],
    },
    331: {  # Ashenvale
        SAVAGE: ["Old forest, old prey. The hunting here has not changed in an age."],
        HAUNTED: ["I have fought over these trees before. Both sides lost."],
        SCHOLAR: ["These groves are older than recorded history and we are felling them for siege engines."],
    },
    130: {  # Silverpine Forest
        GRIM: ["Silverpine has been dying for so long it has made a habit of it."],
        SINISTER: ["Arugal's work is still loose in Shadowfang. Ambitious, for a madman."],
        WRY: ["Worgen, ghouls and a haunted keep. Lovely spot for a walk."],
    },
    490: {  # Un'Goro Crater
        SCHOLAR: ["A crater full of living fossils. Nothing about %zone makes sense and I love it."],
        SAVAGE: ["Devilsaurs. Finally, something worth being afraid of."],
        WRY: ["A jungle. In a crater. In a desert. Full of dinosaurs. Of course."],
    },
}

for _zone, _byp in ZONE_PERSONALITY.items():
    for _p, _texts in _byp.items():
        many("zone_enter", _texts, zone=_zone, personality=_p, weight=2,
             comment=f"zone {_zone} {PERSONALITY_NAMES[_p]}")

# =============================================================================
# Named kills. Creature entries are the real creature_template values.
# =============================================================================

BOSS_LINES = {
    448: [  # Hogger
        "Hogger falls. Elwynn sleeps easier, and half of Stormwind will not believe it.",
        "That is the last of Hogger. More trouble than his size deserved.",
    ],
    522: [  # Mor'Ladim
        "Mor'Ladim is at rest. He was a father once, before Raven Hill took him.",
        "Whatever raised Mor'Ladim, it has lost its hold. Let him lie with his daughter.",
    ],
    639: [  # Edwin VanCleef
        "VanCleef is dead. He built Stormwind and they refused to pay him. Remember that part.",
        "The Brotherhood ends with VanCleef. The grievance that made it does not.",
    ],
    3975: [  # Herod
        "Herod called himself the Scarlet Champion. He was not wrong, only outnumbered.",
        "The Champion falls. The Crusade will find another and call him holy too.",
    ],
    4543: [  # Bloodmage Thalnos
        "Thalnos traded his life for necromancy and got neither back.",
        "Blood magic in a monastery. The Crusade stopped asking questions long ago.",
    ],
    4275: [  # Archmage Arugal
        "Arugal is dead, and the worgen he called are still in Silverpine.",
        "He summoned them to save Dalaran. That is the part nobody tells.",
    ],
    3654: [  # Mutanus the Devourer
        "Mutanus is dead. The Wailing Caverns can go back to only being strange.",
        "Naralex can wake now, if anything in that dream lets him.",
    ],
    10440: [  # Baron Rivendare
        "Rivendare falls. One of the four horsemen, and he chose it freely.",
        "Naxxramas will notice this. Good.",
    ],
    11583: [  # Nefarian
        "Nefarian is dead. Deathwing's son, and every bit as careful with other people's lives.",
        "The experiments in Blackwing end here. Somebody should burn the notes.",
    ],
    14834: [  # Hakkar
        "Hakkar the Soulflayer is unmade. The Gurubashi called him and could not hold him.",
        "That is what happens when a people summon a god for leverage.",
    ],
    15990: [  # Kel'Thuzad
        "Kel'Thuzad falls again. He came back the first time. Watch the ashes.",
        "He betrayed the Kirin Tor for this. I hope it was worth the second death.",
    ],
    15952: [  # Maexxna
        "Maexxna is dead. Nothing in Naxxramas was alive in any sense I recognise.",
    ],
    15953: [  # Grand Widow Faerlina
        "Faerlina served the Cult of the Damned by choice. That is the part that chills me.",
    ],
    15956: [  # Anub'Rekhan
        "Anub'Rekhan was a king of Azjol-Nerub before the Scourge took him. Even he was a victim.",
    ],
    16011: [  # Loatheb
        "Loatheb is destroyed. Whatever it was grown from, it was grown on purpose.",
    ],
    16061: [  # Instructor Razuvious
        "Razuvious trained the Lich King's knights. Some of us remember his voice too well.",
    ],
    19044: [  # Gruul the Dragonkiller
        "Gruul is down. He broke Blade's Edge with his sons and his hands.",
    ],
    22917: [  # Illidan Stormrage
        "Illidan falls. He was not prepared. He said so himself, in the end.",
        "He gave up everything to fight the Legion and became something worse. Remember that order.",
    ],
}

for _entry, _texts in BOSS_LINES.items():
    many("kill_boss", _texts, creature=_entry, weight=3,
         comment=f"creature {_entry}")

# =============================================================================
# Specific quests. The narrowest filter there is, so these always win when they
# apply. Ids verified against quest_template.
# =============================================================================

QUEST_LINES = {
    65: {  # The Defias Brotherhood
        "accept": ["The Defias Brotherhood. Following this thread tends to end badly for the one holding it."],
        "complete": ["So it runs all the way back to the stonemasons. Of course it does."],
    },
    66: {  # The Legend of Stalvan
        "accept": ["Stalvan Mistmantle. Every letter in this trail is worse than the last."],
        "complete": ["Stalvan's story is finished. I wish I had not read all of it."],
    },
    149: {  # Ghost Hair Thread
        "accept": ["Hair from a ghost. Raven Hill will have plenty, which is the trouble."],
    },
    169: {  # Wanted: Gath'Ilzogg
        "accept": ["Gath'Ilzogg, warlord of the Blackrock. Redridge has wanted this a long time."],
        "complete": ["Gath'Ilzogg is dealt with. Lakeshire can breathe."],
    },
    214: {  # Red Silk Bandanas
        "accept": ["Red bandanas. You can count the Defias by the laundry."],
    },
    228: {  # Mor'Ladim
        "accept": ["Mor'Ladim. They say he was a father before the Hill took him."],
        "complete": ["It is done. Let him rest beside his daughter now."],
    },
    270: {  # The Doomed Fleet
        "accept": ["A drowned fleet that will not stay drowned. Westfall's coast is cursed ground."],
    },
}

for _qid, _parts in QUEST_LINES.items():
    for _texts in [_parts.get("accept", [])]:
        many("quest_accept", _texts, quest=_qid, weight=3, comment=f"quest {_qid}")
    for _texts in [_parts.get("complete", [])]:
        many("quest_complete", _texts, quest=_qid, weight=3, comment=f"quest {_qid}")

# =============================================================================
# Emotes. No text reaches the opposite faction on this channel (Player.cpp
# blanks the body), so these carry atmosphere only, never information.
# =============================================================================

EMOTE_LINES = {
    None: {
        "zone_enter": ["scans the horizon and says nothing.", "checks a worn map, then the sky."],
        "death": ["goes still."],
        "level_up": ["rolls a shoulder, testing the weight of it."],
        "idle": ["watches the treeline.", "cleans a blade that is already clean."],
        "combat_start": ["sets their feet."],
    },
    DEVOUT: {"idle": ["bows their head for a moment."], "kill_boss": ["traces a sign over the body."]},
    GRIM: {"idle": ["stares at nothing in particular."], "kill_boss": ["spits, and says nothing."]},
    SCHOLAR: {"idle": ["scratches a note onto a much-abused scrap of parchment."],
              "loot_rare": ["turns %item over, examining the maker's mark."]},
    BOASTFUL: {"level_up": ["straightens up, visibly pleased with themselves."],
               "kill_boss": ["plants a boot on the corpse and looks around for witnesses."]},
    WRY: {"idle": ["sighs at the distance still to walk."], "death": ["looks genuinely put out about it."]},
    HAUNTED: {"idle": ["turns at a sound that was not there."], "kill_boss": ["closes the body's eyes."]},
    SAVAGE: {"idle": ["tests the wind."], "combat_start": ["bares their teeth."]},
    SINISTER: {"idle": ["smiles at nothing."], "kill_boss": ["crouches, examining the remains with interest."]},
}

for _p, _triggers in EMOTE_LINES.items():
    for _trigger, _texts in _triggers.items():
        many(_trigger, _texts, personality=(_p or 0), channel=EMOTE, weight=1,
             comment="emote" + (f" {PERSONALITY_NAMES[_p]}" if _p else ""))

# =============================================================================
# Party talk. Only the group hears these, so they can be more conversational.
# =============================================================================

many("kill_boss", [
    "Well fought. All of you.",
    "That could have gone badly. It did not, and that is down to the group.",
    "Loot it and let us move before something answers the noise.",
], channel=PARTY)

many("death", [
    "I am down. Do not throw yourselves after me.",
    "Sorry. Finish it without me.",
], channel=PARTY)

many("combat_start", [
    "Incoming. Mind the flanks.",
    "I have the first one. Somebody watch the second.",
], channel=PARTY)

many("level_up", ["That is another one. Thanks for the pull.",], channel=PARTY)

# =============================================================================
# Ambient depth. These triggers fire most often once idle chatter is on, so
# they need the most variety or the repetition shows immediately.
# =============================================================================

IDLE_EXTRA = {
    DEVOUT: [
        "I have walked further for worse reasons.",
        "There is always someone who needs help within a day's walk. Always.",
        "My order taught patience. The road teaches it harder.",
    ],
    GRIM: [
        "Everyone I started out with is dead or gone home.",
        "This will not end well. It rarely does. Still here, though.",
        "I have stopped counting the graves I have dug.",
    ],
    SCHOLAR: [
        "Half of what I was taught turns out to be wrong out here.",
        "I would give a great deal for one properly indexed library.",
        "Somebody should be recording all this. Properly, with dates.",
    ],
    BOASTFUL: [
        "One day there will be a statue. I have picked the pose already.",
        "I have done things out here that would empty a tavern to hear.",
        "Modesty is for people with less to be immodest about.",
    ],
    WRY: [
        "Adventuring. Ninety parts walking, one part screaming.",
        "I could have been a baker. My mother still mentions it.",
        "Whoever writes the songs leaves out the blisters.",
    ],
    HAUNTED: [
        "I still set two places out of habit. Old habits die last.",
        "Some nights I can still hear it. Most nights, now.",
        "I came out here to stop thinking. It has not worked.",
    ],
    SAVAGE: [
        "Too long between kills. My hands get restless.",
        "Everything alive out here is either hunting or being hunted. No third option.",
        "I sleep better on hard ground with something to fight in the morning.",
    ],
    SINISTER: [
        "Everyone has a price. Most of them are insultingly low.",
        "There is power lying about everywhere out here, unguarded.",
        "They would not thank me for what I have learned. They will use it anyway.",
    ],
}
for _p, _texts in IDLE_EXTRA.items():
    many("idle", _texts, personality=_p, comment=f"idle {PERSONALITY_NAMES[_p]}")

LOOT_EXTRA = {
    DEVOUT: ["%item. I will see it goes where it is needed."],
    GRIM: ["%item. Somebody died owning this. They always have."],
    SCHOLAR: ["%item. Older than it looks, and the workmanship is not local."],
    BOASTFUL: ["%item! Now that is a prize worth the telling."],
    WRY: ["%item. Finally, something to show for all the walking."],
    HAUNTED: ["%item. I knew someone who carried one like this."],
    SAVAGE: ["%item. Took it off something that wanted to keep it."],
    SINISTER: ["%item. There is more in this than its owner realised."],
}
for _p, _texts in LOOT_EXTRA.items():
    many("loot_rare", _texts, personality=_p, comment=f"loot {PERSONALITY_NAMES[_p]}")

LEVEL_EXTRA = {
    DEVOUT: ["Let it be spent in service, not on myself."],
    GRIM: ["Stronger. Still not enough for what is coming."],
    SCHOLAR: ["Curious how much of this is practice and how little is theory."],
    BOASTFUL: ["Another step, and they will have to start writing faster."],
    WRY: ["Stronger. Do I get a horse yet? No? Splendid."],
    HAUNTED: ["If I had been this strong then, perhaps..."],
    SAVAGE: ["The hunt sharpens me."],
    SINISTER: ["Every step closer to not needing anyone's permission."],
}
for _p, _texts in LEVEL_EXTRA.items():
    many("level_up", _texts, personality=_p, comment=f"level {PERSONALITY_NAMES[_p]}")

# =============================================================================
# Authored archetype lines for death and level_up.
#
# The combat_start half of this table moved to data/lines/combat-archetype.txt,
# because a good many of those lines only work against a small animal and the
# rank gate that fixes them is expressible in a line file, not here.
#
# combat_start, death and level_up used to get most of their volume from the
# combinatorial layer, which joined an object or situation fragment to an
# archetype reaction. That layer is switched off for these three triggers now
# (AUTHORED_ONLY in gen_bot_lore_combos.py) because the joins were never
# checked for coherence and produced the lines that read as machine-made.
# These are written as whole utterances instead.
#
# Two constraints shaped them. The enemy is usually a trivial animal, so a line
# that only works against a great foe reads as farce against a Mangy Wolf; and
# no line names a level, because a character who announces a number is
# describing a game statistic.
# =============================================================================

AUTHORED = {
    DEVOUT: {
        "death": [
            "Do not carry me far. Lay me where the Light can find me.",
            "Tend the others first. I have had my share of care.",
            "I am not afraid. I only wanted more hours.",
            "Be at peace, %target. I forgive you the whole of it.",
            "Say nothing over me that I did not earn.",
            "The Light never needed my hands. It only borrowed them.",
            "Go on. There are still people waiting on you.",
            "I kept faith. Let that be enough.",
        ],
        "level_up": [
            "A little more strength. I will find someone who needs it.",
            "Steadier hands than yesterday. Good.",
            "Stronger than I was, and the need has not shrunk.",
            "More reach today than yesterday, and more to answer for.",
            "Whatever I am given, I am given to spend.",
            "The burden sits better on me today.",
        ],
    },
    GRIM: {
        "death": [
            "There. Done, and no surprises in it.",
            "%target. Of all the things that could have had me.",
            "Keep moving. Standing over me changes nothing.",
            "I always knew the ground would win.",
            "Cold. That is all it turns out to be.",
            "Take what I carried. It is no use to me now.",
            "No last words worth keeping. Go on.",
            "I told myself I would see this coming. I did. It did not help.",
        ],
        "level_up": [
            "I am harder than I was. The ground is no softer.",
            "Stronger today. It buys another day, no more.",
            "Harder to kill. Not impossible. Never that.",
            "A little more in me, and I will need every bit of it before long.",
            "Something in me grew. It will be spent by evening.",
            "I feel it settle. Another thin layer between me and the dirt.",
        ],
    },
    SCHOLAR: {
        "death": [
            "Ah. So that is what that feels like.",
            "%target. Write the name down correctly, whoever is listening.",
            "I was wrong about something. I wish I knew which thing.",
            "Do not move me yet. I want to notice this properly.",
            "The notes in my pack are nearly finished. Someone finish them.",
            "%target, and not even an unusual specimen. That is the part that stings.",
            "I have no conclusion. Only the observation.",
            "Keep the pages dry. That is all I ask.",
        ],
        "level_up": [
            "Something settled. I could not tell you the mechanism.",
            "My hands are steadier than they were last week. Noted.",
            "Stronger. I would like to know what was exchanged for it.",
            "Growth. Inconvenient that it requires so much hitting.",
            "I feel the change and cannot name it, which will bother me all day.",
            "The body learns faster than I can describe it.",
        ],
    },
    BOASTFUL: {
        "death": [
            "Tell them I was magnificent. Tell them nothing else.",
            "%target. Of all the endings I rehearsed, never this one.",
            "Remember the good parts. There were so many good parts.",
            "This verse was meant to come much later.",
            "Do not let anyone write this one down.",
            "I had a far better line ready than this.",
            "Carry on without me. You will find it harder than I made it look.",
            "Even the great ones fall. I am simply more graceful about it.",
        ],
        "level_up": [
            "The stories are barely keeping pace with me.",
            "Stronger again. I do make it look easy.",
            "Stronger, and nobody is surprised, least of all me.",
            "Another step up. I will save the celebrating for something worth it.",
            "Stronger than yesterday, and yesterday was impressive enough.",
            "My sword feels lighter than it did this morning.",
        ],
    },
    WRY: {
        "death": [
            "Well. That was not the plan, but it was certainly a plan.",
            "%target. Truly. Of all the things.",
            "When you tell this, make it sound better than it was.",
            "I am going to lie down now, and I would rather nobody watched.",
            "Well. I suppose that answers that.",
            "Do not blame yourselves. Blame me, I clearly earned it.",
            "I always assumed I would see it coming.",
            "If anyone is keeping count, I would like this one struck from the record.",
        ],
        "level_up": [
            "Stronger, apparently. My knees have not been informed.",
            "Stronger than I was yesterday. Yesterday set a low bar.",
            "Harder to kill, and the same boots.",
            "I notice I am harder to kill. Good. That was becoming an issue.",
            "Something in me improved. It declined to say which part.",
            "Stronger, and the road is exactly as long as it was.",
        ],
    },
    HAUNTED: {
        "death": [
            "I am sorry. I could not do it a second time.",
            "I am coming. You waited long enough.",
            "It is quiet. I had forgotten quiet.",
            "Go on without me. I know how that is done.",
            "I held on to it as long as I could.",
            "%target, then. It hardly matters who.",
            "Do not carry this. I carried mine too long.",
        ],
        "level_up": [
            "Stronger now. I did not expect to get this far.",
            "I will be enough one day. Not yet.",
            "Steadier hands. I have wanted steady hands a long time.",
            "Something came back to me today. Not all of it.",
            "Still walking, and stronger for it. That is all I ask.",
            "Stronger, yes. It does not undo anything.",
        ],
    },
    SAVAGE: {
        "death": [
            "Ha. You had it in you after all.",
            "Not clean, but mine.",
            "%target earned this. Say so when you tell it.",
            "I go down facing it. That is the whole of it.",
            "Leave me here and finish what I started.",
            "My blood is out, and so is the fight in me.",
            "Put me where I fell. I like the ground here.",
            "Good. I would have hated a slow ending.",
        ],
        "level_up": [
            "Stronger. The killing taught me that.",
            "Sharper than the day I started.",
            "My grip is better than it was this morning.",
            "Send me something that can hurt me now.",
            "I eat, I fight, I grow. Simple enough.",
            "Another notch in me. I will use it tonight.",
        ],
    },
    SINISTER: {
        "death": [
            "A poor return on everything I put in.",
            "I knew the price. I had hoped to pay it much later.",
            "Take what I carry. I will want it back.",
            "Do not mourn. Collect.",
            "The bargain holds. Only the terms have moved.",
            "%target. Remember what you took from me. Someone will come asking.",
            "Leave me here and say nothing. I prefer to be underestimated.",
            "I am owed too much for this to be... the end of it.",
        ],
        "level_up": [
            "Something in me has settled. Useful.",
            "Fewer things in this world can refuse me now.",
            "Stronger. I will not say by how much.",
            "Another step, and no one saw me take it.",
            "Patience pays better than courage. I am the proof.",
            "Whatever this cost me, it was a fair trade.",
        ],
    },
}

for _p, _triggers in AUTHORED.items():
    for _trigger, _texts in _triggers.items():
        many(_trigger, _texts, personality=_p, weight=3,
             comment=f"authored {_trigger} {PERSONALITY_NAMES[_p]}")

# Lines addressed to somebody standing there. Said alone they read as a bot
# talking to an empty field, so they need a real player in the group - other
# bots are not an audience. This is what the GroupState column is for.
AUTHORED_TO_COMPANIONS = {
    HAUNTED: [
        "Keep your eyes open. I was not, once.",
        "Stay close to me. I have lost people who wandered off.",
        "Do not let it get behind you. That is how it happens.",
        "Watch my left. I am slow on my left now.",
    ],
}

for _p, _texts in AUTHORED_TO_COMPANIONS.items():
    many("combat_start", _texts, personality=_p, group=GROUP_WITH_PLAYER, weight=3,
         comment=f"authored combat_start {PERSONALITY_NAMES[_p]} to companions")

DEATH_EXTRA = {
    DEVOUT: ["The Light... take me..."],
    GRIM: ["Told you."],
    SCHOLAR: ["Fascinating. Unhelpful."],
    BOASTFUL: ["Impossible... I am... I was..."],
    WRY: ["Well. That is my afternoon ruined."],
    HAUNTED: ["I am coming. I am finally coming."],
    SAVAGE: ["It bested me. Good."],
    SINISTER: ["No. No, I had plans."],
}
for _p, _texts in DEATH_EXTRA.items():
    many("death", _texts, personality=_p, comment=f"death {PERSONALITY_NAMES[_p]}")

# =============================================================================
# Race, in their own homelands. A small layer, but it lands when it hits.
# =============================================================================
HUMAN, ORC, DWARF, NIGHTELF, UNDEAD, TAUREN, GNOME, TROLL = 1, 2, 4, 8, 16, 32, 64, 128
BLOODELF, DRAENEI = 512, 1024
# mod-worgoblin's two races, 9 and 12, so the masks are 1 << (race - 1).
GOBLIN, WORGEN = 256, 2048

RACE_HOME = [
    (HUMAN, 12, "Elwynn raised me. Strange, how small it looks now."),
    (HUMAN, 1519, "Stormwind. I know every street of this city and it still surprises me."),
    (DWARF, 1, "Dun Morogh. Cold, stubborn and mine."),
    (DWARF, 1537, "Ironforge. The Forge has never gone out, not once, not ever."),
    (GNOME, 1, "Gnomeregan is down there full of our own people. We do not talk about it enough."),
    (NIGHTELF, 141, "Teldrassil. I was born under these branches, after the Sundering and long before you."),
    (NIGHTELF, 1657, "Darnassus. Ten thousand years of us, and still we whisper indoors."),
    (DRAENEI, 3557, "The Exodar. We have been refugees for so long that the word stopped stinging."),
    (DRAENEI, 3524, "Azuremyst. We fell out of the sky onto this island and called it fortune."),
    (ORC, 14, "Durotar. Thrall chose hard ground on purpose. We needed to earn something."),
    (ORC, 1637, "Orgrimmar. Built by free orcs, and I will not hear otherwise."),
    (TAUREN, 215, "Mulgore. The earth mother is close here. You can feel her in the grass."),
    (TAUREN, 1638, "Thunder Bluff. My people came a long way to stand this high."),
    (TROLL, 14, "Sen'jin village be down the coast. The Darkspear owe Thrall more than blood."),
    (UNDEAD, 85, "Tirisfal. I was alive here, once. I try not to dwell on which house."),
    (UNDEAD, 1497, "The Undercity. We built a nation under a dead king's palace. Fitting."),
    (BLOODELF, 3430, "Eversong. The trees kept their gold while everything else burned."),
    (BLOODELF, 3487, "Silvermoon. Rebuilt beautiful, and hollow in places you cannot see."),
]
for _race, _zone, _text in RACE_HOME:
    line("zone_enter", _text, zone=_zone, race=_race, weight=3,
         comment=f"race {_race} home zone {_zone}")

# =============================================================================
# Ordinary kills. Off by default because it fires constantly, so if it is ever
# switched on it needs the widest variety of anything here.
# =============================================================================

KILL_LINES = {
    DEVOUT: ["May it find more peace than it had.", "One less thing preying on the weak."],
    GRIM: ["That is one. There is no end of them.", "Dead. Next."],
    SCHOLAR: ["Interesting musculature. Not what the field guide claimed.",
              "I should collect a sample. I never do."],
    BOASTFUL: ["Barely worth drawing for.", "Another for the tally."],
    WRY: ["It started it.", "Well, it will not do that again."],
    HAUNTED: ["I take no pleasure in this any more.", "Another one. They blur together."],
    SAVAGE: ["Clean kill.", "Still warm. Good."],
    SINISTER: ["Waste. There was use left in it.", "Its end was more useful than its life."],
}
for _p, _texts in KILL_LINES.items():
    many("kill", _texts, personality=_p, comment=f"kill {PERSONALITY_NAMES[_p]}")

many("kill", ["Down.", "That is dealt with.", "%target is finished."])

many("loot_rare", [
    "%item. That will serve better than what I carry.",
    "%item. Whoever made this knew their craft.",
    "%item. Worth the trouble getting here.",
    "%item. I will not be selling this one.",
])

many("quest_accept", [
    "%quest. Someone has to, and I am standing here.",
    "Tell them it is in hand.",
    "%quest. I have done stranger things for less.",
])

many("quest_complete", [
    "%quest. They can sleep tonight, at least.",
    "Settled. On to whatever is next.",
    "%quest is behind us. Do not expect a parade.",
])

# =============================================================================
# Archetype depth. Idle, combat_start and zone_enter fire far more often than
# anything else, so they get the most variety - this is what buys hours of
# listening without a repeat.
# =============================================================================

DEEP_IDLE = {
    DEVOUT: [
        "The road is a kind of prayer, if you let it be.",
        "I have buried strangers with full rites. It costs nothing but time.",
        "Doubt is not the opposite of faith. Idleness is.",
        "There are chapels out here with no priest and no roof. I stop at all of them.",
        "I was told service would feel heavier than this. Some days it does.",
        "Whatever the Light is, it is not in a hurry.",
        "I keep a list of names to pray for. It only ever gets longer.",
    ],
    GRIM: [
        "Nobody out here is coming to save anybody.",
        "I have outlived three companies. That is not a boast.",
        "Give it a year and this road will have a new name and the same bones under it.",
        "The ones who talk about glory have not done much of the work.",
        "Sooner or later something out here is faster than me.",
        "I stopped making plans past the next week.",
        "Every village says it is safe. Every village is wrong eventually.",
    ],
    SCHOLAR: [
        "The Kirin Tor would pay for half of what I have seen and dismiss the other half.",
        "Nothing out here matches the maps. Nothing.",
        "I have three theories and no way to test any of them.",
        "There are ruins under half this continent and nobody is counting them.",
        "Facts are cheap. Somebody has to arrange them.",
        "I have started writing in the margins of my own notes. Poor sign.",
        "If I survive this I intend to write it all down badly and let others correct me.",
    ],
    BOASTFUL: [
        "There are three taverns between here and the coast that would not charge me.",
        "I have been called a lot of things. Several of them were accurate.",
        "The trick is doing something impressive where people can see it.",
        "I do not brag. I report, accurately, at length.",
        "Somebody will write this down eventually. I may have to do it myself.",
        "I have a speech prepared. It has never once been the right moment.",
        "Half the heroes in the songs did less than I did last Tuesday.",
    ],
    WRY: [
        "So far today: two ambushes, no lunch.",
        "Everybody wants six of something. Never five. Never seven.",
        "I have walked past four signposts and none of them agreed.",
        "The pay is terrible and the hours are worse and here I am.",
        "Whoever designed these roads had a grudge against feet.",
        "I once got paid in stew. Actual stew.",
        "They always say it is just over the next hill. It is never just over the next hill.",
    ],
    HAUNTED: [
        "I do not sleep much. You get used to it.",
        "I carry a letter I will never be able to deliver.",
        "Some days I forget, and that is worse than remembering.",
        "There is a road I will not walk again. Not for any money.",
        "I keep doing this because stopping means thinking.",
        "The ones who did not come back are better company than most of the living.",
        "I have made peace with a great many things I have not forgiven.",
    ],
    SAVAGE: [
        "Rain coming. You can smell it before you see it.",
        "I eat what I kill. It keeps the accounting simple.",
        "The soft ones do not last out here and that is not cruelty, it is weather.",
        "My hands are quiet. I do not like it when my hands are quiet.",
        "Everything out here is meat or it is a threat. Often both.",
        "I have tracked things for three days without sleeping. It was worth it.",
        "Cities smell wrong. Too many people, not enough sky.",
    ],
    SINISTER: [
        "People hand me their secrets and call it conversation.",
        "Every locked door in the world was built by someone who could be bribed.",
        "I have never needed to threaten anyone who was paying attention.",
        "There is knowledge out here they burned books to bury. Badly.",
        "Loyalty is just a price nobody has met yet.",
        "I am very patient. It is my least appreciated quality.",
        "They will need what I know before they are finished despising me for knowing it.",
    ],
}
for _p, _texts in DEEP_IDLE.items():
    many("idle", _texts, personality=_p, comment=f"idle {PERSONALITY_NAMES[_p]}")

DEEP_COMBAT = {
    DEVOUT: ["The Light forgive me for what this takes.", "You chose this. I did not.",
             "Stand aside or be put aside.", "I will make it quick. That is the mercy I have."],
    GRIM: ["Another one.", "Fine. Let us get it done.", "I have no speech for this.",
           "You will not be the one that gets me."],
    SCHOLAR: ["Regrettable. Necessary.", "Let us see what you are made of. Literally.",
              "I did warn it.", "I would note the technique if I had a free hand."],
    BOASTFUL: ["You have no idea who you have picked.", "Finally, an audience.",
               "This will look very good later.", "Watch closely. You will want the details."],
    WRY: ["Of course. Why not.", "I had almost finished my sandwich.",
          "Everyone out here wants a fight and nobody wants a conversation.",
          "Right. Violence. My favourite."],
    HAUNTED: ["I have done this too many times.", "Do not make me remember this one.",
              "Come on, then. Get it over with.", "I am so tired of this."],
    SAVAGE: ["Good. Blood.", "Run. I prefer it when they run.",
             "Come closer. Closer.", "Now we find out which of us is hungrier."],
    SINISTER: ["Oh, do struggle. It is more interesting.", "You will be useful shortly.",
               "Let us find out where your limit is.", "This is the part I enjoy."],
}
for _p, _texts in DEEP_COMBAT.items():
    many("combat_start", _texts, personality=_p, comment=f"combat {PERSONALITY_NAMES[_p]}")

DEEP_ZONE = {
    DEVOUT: [
        "Somewhere in %zone there is someone who has given up. That is who I came for.",
        "No shrine here, no bells. The Light does not require either.",
        "I will ask at the nearest holding what they need. They always need something.",
        "%zone has been prayed over by people who never got an answer. I will try again.",
    ],
    GRIM: [
        "%zone. I give it a year before it needs saving again.",
        "Look at the roadside. Cairns, all the way along.",
        "Somebody drew a border through %zone and got a lot of people killed over it.",
        "I have been in worse. That is not the same as this being good.",
    ],
    SCHOLAR: [
        "%zone is older than the records that mention it. That should trouble more people.",
        "The place names here are corruptions of something. I would love to know what.",
        "I would give a month of my life for a proper survey of %zone.",
        "Note the ruins. Nobody builds like that any more, and nobody remembers how.",
    ],
    BOASTFUL: [
        "%zone. Add it to the list of places that have seen me work.",
        "I will be remembered in %zone long after the locals are not.",
        "They will name an inn after me here. Give it time.",
    ],
    WRY: [
        "%zone. Charming. Is there anywhere to sit.",
        "Ah, %zone, where the wildlife is rabid and the hospitality is theoretical.",
        "I am told %zone has a thriving local economy. I am told many things.",
        "Whoever wrote the guidebook for %zone has never been to %zone.",
    ],
    HAUNTED: [
        "%zone. Of all the places to come back to.",
        "I know these roads better than I want to.",
        "There is a house in %zone I will not walk past.",
        "Every place looks like somewhere I have already lost something.",
    ],
    SAVAGE: [
        "%zone smells of prey.",
        "Good ground. Cover, water, and something big moving in it.",
        "I could live out here. I have, before.",
    ],
    SINISTER: [
        "%zone is full of people who would never notice what I took.",
        "Old power sunk into this ground, and a lot of shallow graves on top of it.",
        "Somebody here knows something worth having.",
    ],
}
for _p, _texts in DEEP_ZONE.items():
    many("zone_enter", _texts, personality=_p, comment=f"zone {PERSONALITY_NAMES[_p]}")

# =============================================================================
# Specific quests. Ids verified against quest_template. These are the narrowest
# filter there is after items, so they win heavily when they apply.
# =============================================================================

MORE_QUESTS = {
    7:   ("Kobolds in the Jasperlode again. They breed faster than we clear them.", None),
    8:   ("A rogue's deal. Nothing about that phrase has ever ended well.", None),
    9:   ("The killing fields. They called them wheat fields once.", "Westfall is a little less lost than it was."),
    19:  ("Tharil'zun leads them. Cut the head off and the Riverpaw scatter.", None),
    22:  ("Goretusk liver. For a pie. I did not come to Westfall for the cuisine.", None),
    36:  ("Westfall stew, and half the ingredients still running around.", None),
    39:  ("Thomas' report. Paper moves slower than trouble does.", None),
    46:  ("Murlocs on the coast. Nobody knows where they keep coming from.", None),
    56:  ("The Night Watch guards Darkshire with lanterns and nerve. Mostly nerve.", None),
    65:  ("The Defias Brotherhood. Follow this thread far enough and it reaches the throne.",
          "So it runs back to the stonemasons and an unpaid bill. Of course it does."),
    66:  ("Stalvan Mistmantle. Every letter in this trail is worse than the last.",
          "Stalvan's story is finished. I wish I had not read all of it."),
    86:  ("A pie for a boy in Westfall. Small things still count.", None),
    120: ("A message to Stormwind. They will read it and do nothing, but it must be sent.", None),
    128: ("Blackrock orcs, this close to Lakeshire. Somebody in the capital should care.", None),
    149: ("Hair from a ghost. Raven Hill has plenty, which is exactly the trouble.", None),
    151: ("Old Blanchy. A horse should not have to work that hard for people that poor.", None),
    152: ("The coast is not clear and has not been for years.", None),
    158: ("Zombie juice. I have stopped asking what things are for.", None),
    168: ("Collecting the belongings of the dead. Somebody should.", None),
    169: ("Gath'Ilzogg, warlord of the Blackrock. Redridge has wanted this a long time.",
          "Gath'Ilzogg is dealt with. Lakeshire can breathe."),
    173: ("Worgen in the woods. Arugal's gift to Duskwood, and it keeps giving.", None),
    174: ("Look to the stars, they said. In Duskwood you cannot see them.", None),
    184: ("Furlbrow's deed. A farm on paper, and nothing left standing on the ground.", None),
    214: ("Red bandanas. You can count the Defias by the laundry.", None),
    217: ("In defence of the king's lands. There is a king in that sentence somewhere.", None),
    225: ("A weathered grave. Somebody was buried in a hurry and not by friends.", None),
    228: ("Mor'Ladim. They say he was a father, before the Hill took him.",
          "It is done. Let him rest beside his daughter now."),
    244: ("Gnolls at the gates again. Elwynn's oldest complaint.", None),
    262: ("A shadowy figure in Duskwood. That describes most of Duskwood.", None),
    270: ("A drowned fleet that will not stay drowned. Westfall's coast is cursed ground.", None),

    2:   ("Sharptalon's claw. The Warsong will know what it means when they see it.", None),
    363: ("Waking up in Deathknell with your own grave behind you. No one is ready for that.", None),
    365: ("The fields of grief. Lordaeron's farmland, and what is farming it now.", None),
    376: ("The damned. Our own people, too far gone to bring back.", None),
    380: ("Night Web's Hollow. Spiders the size of dogs, and worse deeper in.", None),
    745: ("Sharing the land. The tauren mean that literally, which is why I respect them.", None),
    757: ("The Rite of Strength. Every tauren walks it. I intend to walk it well.",
          "The Rite of Strength is completed. Cairne's people have long memories for this."),
    764: ("The Venture Company again. Ore before everything, including people.", None),
    765: ("Supervisor Fizsprocket. Goblin management, orcish response.", None),
    767: ("The Rite of Vision. I am told it shows you what you need, not what you want.", None),
    773: ("The Rite of Wisdom. The last of them, and the one that frightens me.",
          "The Rite of Wisdom is done. I am not the same as when I started it."),
    783: ("A threat within. The rot in the Undercity is not always outside the walls.", None),
    788: ("Cutting teeth on scorpids. Durotar raises its own hard.", None),
    790: ("Sarkoth. A scorpid big enough to have a name. That is never good.", None),
    791: ("Carry your weight. The Horde has no use for anyone who will not.", None),
    792: ("Vile familiars. The Burning Blade brought demons into Durotar itself.", None),
    794: ("A Burning Blade medallion. Proof, if anyone in Orgrimmar still needs it.", None),
    806: ("Dark storms over the Barrens. The elements are not doing that on their own.", None),
    815: ("Breaking raptor eggs. Unpleasant, and better than what hatches.", None),
    827: ("Skull Rock. The Burning Blade have made themselves a home of it.", None),
    829: ("Neeru Fireblade. A Burning Blade agent inside Orgrimmar, and tolerated. Ask why.", None),
    834: ("Winds in the desert. Tanaris keeps its own counsel.", None),
    845: ("Zhevra. Beautiful animals. The centaur hunt them to nothing.", None),
    868: ("Egg hunt. Half of the Barrens is trying to eat the other half's young.", None),
    869: ("Raptor thieves. The Razormane take what they like and the caravans pay for it.", None),
    871: ("Disrupt the attacks. The Barrens is one long supply line under constant raid.", None),
    876: ("Serena Bloodfeather leads the harpies. Cut the leader and the raids stop.", None),
    894: ("The samophlange. Goblin engineering, which means nobody knows what it does.", None),
    899: ("Consumed by hatred. It happens out here. It happens quietly.", None),
    1069:("Deepmoss spider eggs. Stonetalon grows everything too large.", None),
    1487:("Deviate eradication. Whatever is in those caverns should not breed.", None),
}

for _qid, (_accept, _complete) in MORE_QUESTS.items():
    if _accept:
        line("quest_accept", _accept, quest=_qid, weight=2, comment=f"quest {_qid}")
    if _complete:
        line("quest_complete", _complete, quest=_qid, weight=2, comment=f"quest {_qid}")

# =============================================================================
# Specific items. loot_rare only fires at rare quality and above, so these are
# the pieces worth a reaction. Entries verified against item_template.
# =============================================================================

ITEM_LINES = {
    19019: ["Thunderfury. The wind is inside the metal. I can hear it.",
            "Thunderfury, blessed blade of the Windseeker. Thunderaan is in here, and he is not pleased."],
    17182: ["Sulfuras. Ragnaros left something of himself in this and it has not cooled.",
            "The hand of Ragnaros. It is still burning. I do not think it stops."],
    13262: ["The Ashbringer. Do not say the name loudly. It still answers to it."],
    22691: ["The Ashbringer, corrupted. Something in this blade is grieving, and it is not me."],
    19364: ["Ashkandi. The Brotherhood carried this before Nefarian took the mountain."],
    18348: ["Quel'Serrar. Night elf work, quenched in dragonfire. Both halves of that matter."],
    18608: ["Benediction. A staff should not feel like an argument you have already won."],
    18609: ["Anathema. The same wood as Benediction, turned the other way. That choice is mine."],
    12784: ["An Arcanite Reaper. Every smith in Azeroth wants to claim they made one."],
    2244:  ["A Krol Blade. Old steel, honest weight. It has cut before."],
    12940: ["Dal'Rend's Sacred Charge. Rend Blackhand carried its twin. Remember whose it was."],
    19334: ["The Untamed Blade. It pulls when you swing it, as though it has an opinion."],
    18816: ["Perdition's Blade. Drawn out of the fire itself. It never quite goes cold."],
    17076: ["Bonereaver's Edge. Molten Core gives nothing away kindly."],
    18842: ["A Staff of Dominance. The name is not a boast, it is a warning label."],
    18422: ["The head of Onyxia. She sat in Stormwind's court and advised a king. Remember that."],
    19002: ["The head of Nefarian. Deathwing's son, and every bit as careless with other lives."],
    17204: ["The Eye of Sulfuras. There is a firelord's attention in this. I can feel it looking."],
    19017: ["The Essence of the Firelord. Ragnaros is not finished. This is proof of it."],
    18563: ["Bindings of the Windseeker. Half of a prison. Somebody wants the other half badly."],
    13335: ["Deathcharger's Reins. Rivendare rode this thing. It is still not quite alive."],
    36942: ["Frostmourne. No. I will not carry this. Nobody should carry this."],
    40384: ["Betrayer of Humanity. An honest name, at least. That is rare in a weapon."],
    49623: ["Shadowmourne. Forged against the Scourge out of the Scourge. There is a lesson in that."],
    40684: ["A Mirror of Truth. It shows what is there. People rarely want that."],
}

for _iid, _texts in ITEM_LINES.items():
    many("loot_rare", _texts, item=_iid, weight=4, comment=f"item {_iid}")

# =============================================================================
# Second archetype pass. These apply in every zone, so each line added here is
# worth far more to variety than one written for a single place.
# =============================================================================

WIDE_ZONE = {
    DEVOUT: [
        "Whoever holds the nearest chapel, I will offer them my arm before my opinion.",
        "There is always work here. There is always work everywhere.",
        "I have never yet arrived somewhere and found nothing that needed doing.",
        "Bless this ground. It has had worse visitors than me.",
        "I did not take my vows to stand in comfortable places.",
    ],
    GRIM: [
        "New country, same trouble wearing a different name.",
        "Count the watchtowers. Now count the ones still manned.",
        "Somebody died making this road safe and it is still not safe.",
        "I will be glad to leave and I have only just arrived.",
        "Every step further out is a step further from a healer.",
    ],
    SCHOLAR: [
        "The local dialect here has words for things I have never seen. That is a clue.",
        "Somebody should be cataloguing all this before it is lost.",
        "I can date that wall to within a century, and it disagrees with every account I have read.",
        "Three different peoples have held this ground. You can see all three in the stonework.",
        "I would stay a season if anyone would let me.",
    ],
    BOASTFUL: [
        "New ground, new stories. Try to keep up.",
        "I do hope something here is difficult. It has been a dull week.",
        "Announce me or do not, it makes little difference to the outcome.",
        "Somebody here is about to have a very good day, because I have arrived.",
    ],
    WRY: [
        "Another beautiful place full of things that bite.",
        "I have developed strong opinions about local signage.",
        "So. More walking, then.",
        "I am beginning to suspect nowhere in this world is actually finished.",
        "Every settlement out here has one inn, one guard, and one enormous problem.",
    ],
    HAUNTED: [
        "I do not remember choosing to come this way.",
        "Everywhere starts to look like the place it happened.",
        "I will keep moving. It is the only thing that works.",
        "New ground. Same weight.",
        "I used to travel with people. That was a long time ago.",
    ],
    SAVAGE: [
        "Tracks everywhere. Something big passed through not long ago.",
        "I will know this ground by dark. That is how you stay alive on it.",
        "Good country. Hard country. The two go together.",
        "Whatever rules here has not met me.",
    ],
    SINISTER: [
        "Every place has a door somebody forgot to lock.",
        "New faces, new weaknesses. It is almost too easy.",
        "There is always someone here who wants something badly enough.",
        "Power leaks out of old places like this. Somebody should collect it.",
    ],
}
for _p, _texts in WIDE_ZONE.items():
    many("zone_enter", _texts, personality=_p, comment=f"zone wide {PERSONALITY_NAMES[_p]}")

WIDE_IDLE = {
    DEVOUT: [
        "I have given the last of my bandages away twice this week. I would do it again.",
        "Faith is mostly turning up.",
        "The Light does not ask whether it is convenient.",
        "I will rest when the road does.",
        "Someone taught me these prayers. I hope they are still alive to hear them used.",
    ],
    GRIM: [
        "Do not get attached to anyone out here.",
        "I have a list of things that nearly killed me. It is long and it is boring.",
        "Hope is a supply you run out of quietly.",
        "Talk if you like. It changes nothing.",
        "I have seen what is coming. You would not sleep either.",
    ],
    SCHOLAR: [
        "I have been wrong four times this month and learned something each time.",
        "The trouble with field work is the field.",
        "I would trade a great deal for an hour with a proper archive.",
        "Somebody wrote all this down once and then we lost the book.",
        "Ask me again in a week. I will have a better answer and a worse theory.",
    ],
    BOASTFUL: [
        "I have a list of my own achievements. It is illuminated.",
        "They will ask you, later, whether you were there when I did it. Say yes.",
        "Modesty has never once got anybody a statue.",
        "I have turned down offers you would not believe.",
    ],
    WRY: [
        "I have been paid in cheese, in promises, and once in a chicken.",
        "Everyone wants a hero until the hero wants dinner.",
        "I could have been a scribe. Warm room. Chair.",
        "Do you know how much of this job is inventory management.",
        "One of these days somebody will hand me a map that is right.",
    ],
    HAUNTED: [
        "I still wake up reaching for a sword that is already in my hand.",
        "Do not ask me why I do this. I have stopped having an answer.",
        "There were four of us. Then three. You can do the rest.",
        "Grief is just love with nowhere to go, somebody told me. They died too.",
        "I keep walking because the alternative is sitting still.",
    ],
    SAVAGE: [
        "I have not slept indoors in a season and I feel better for it.",
        "My hands know the work. My head can rest.",
        "Everything out here is simple. Cities are what is complicated.",
        "I do not hunt for sport. I hunt because it is what I am for.",
        "When the birds go quiet, look up.",
    ],
    SINISTER: [
        "I have never once had to raise my voice to get what I wanted.",
        "They will call it a favour when I ask for it back.",
        "Knowledge is only dangerous to whoever does not have it.",
        "I keep careful notes on people. It is astonishing how rarely anyone checks.",
        "Everyone is one bad night away from being useful to me.",
    ],
}
for _p, _texts in WIDE_IDLE.items():
    many("idle", _texts, personality=_p, comment=f"idle wide {PERSONALITY_NAMES[_p]}")

# =============================================================================
# More named kills.
# =============================================================================

# Entries checked against creature_template - eight of these were originally
# written against the wrong creature and would have attached the wrong lore.
MORE_BOSSES = {
    3654:  ["Mutanus is dead. The Wailing Caverns can go back to only being strange."],
    9019:  ["Emperor Thaurissan falls. The Dark Iron will not forgive this, and I do not need them to.",
            "Dagran Thaurissan is dead, and Moira is still down there. That is the harder problem."],
    4421:  ["Charlga Razorflank. The Razorfen matriarch, and every quilboar in the Kraul answered to her."],
    6487:  ["Arcanist Doan. The Scarlet Crusade let him keep the library. Look what he did with it."],
    11486: ["Prince Tortheldrin. Dire Maul was a night elf seat of learning. He sold it for power."],
    8983:  ["Golem Lord Argelmach. Dark Iron engineering, and it nearly held."],
    10184: ["Onyxia. She wore a human face in Stormwind's court for years and advised a king.",
            "Onyxia falls. How many of the orders we followed were hers?"],
    12118: ["Lucifron. The first of Ragnaros' lieutenants, and not the worst of them."],
    1720:  ["Bruegal Ironknuckle. The Defias kept harder company in the Deadmines than anyone admits."],
    6109:  ["Azuregos. Blue flight, and he was only ever half interested in us."],
    14020: ["Chromaggus. Five breaths, one body. Nefarian was proud of that one."],
    15956: ["Anub'Rekhan was a king of Azjol-Nerub before the Scourge took him. Even he was a victim."],
    15928: ["Thaddius. Stitched out of the people Naxxramas took. Do not look too closely."],
    15989: ["Sapphiron. A blue dragon raised as a weapon. Malygos lost more than pride to the Scourge."],
    15954: ["Noth the Plaguebringer. He taught the plague like a subject."],
    16060: ["Gothik the Harvester. He trained the necromancers. Every one of them."],
    15931: ["Grobbulus is destroyed. Whatever was in that tank was intended for a city."],
    15932: ["Gluth. They fed it the ones that did not rise properly."],
}
for _entry, _texts in MORE_BOSSES.items():
    many("kill_boss", _texts, creature=_entry, weight=3, comment=f"creature {_entry}")

# =============================================================================
# More of the short reactions, where repetition shows fastest.
# =============================================================================

many("level_up", [
    "That is another step. I can feel the difference in my arms.",
    "Stronger. The next one always takes longer.",
    "Stronger. Whether it is strong enough is another question.",
    "I will put it to use before I celebrate it.",
    "I remember being too weak for this road. I do not intend to be again.",
    "Harder won than it looks. Nobody hands you these.",
])

many("death", [
    "Ah. That was careless.",
    "Go on without me. Go on.",
    "I can still... no. No, I cannot.",
    "Somebody remember where this happened.",
    "That is the one that had my name on it.",
])

many("kill_boss", [
    "Down, and it took all of us to do it.",
    "That is the end of that one. Strip it and move.",
    "%target is finished. I want to be a long way from here before dark.",
    "There. Whatever it was guarding is ours now.",
])

many("combat_start", [
    "On me. Now.",
    "Here it comes.",
    "%target has decided. Oblige it.",
    "Blades out.",
])

# =============================================================================
# Emit
# =============================================================================

HEADER = """-- ---------------------------------------------------------------------------
-- Lore chatter corpus for mod-botlore
--
-- GENERATED by the module's tools/gen_bot_lore.py - edit the corpus there, not
-- here, then re-run it.
--
-- The core's database updater applies this for you at startup, because it is
-- part of an enabled module: UpdateFetcher::ReceiveIncludedDirectories picks up
-- modules/<name>/data/sql/db-world, and a MODULE file whose hash has changed is
-- re-applied. Applying it by hand and then running ".botlore reload" publishes
-- new lines without a restart.
--
-- Every filter column is "0 means any", and mod-botlore prefers the most
-- specific matching line, so a line written for one quest beats one written
-- for a zone, which beats a generic one.
--
-- PersonalityMask matches the archetype mod-botlore derives from the bot's
-- name (FNV-1a over the lowercased name, modulo the archetypes its class is
-- allowed): 0x01 devout, 0x02 grim, 0x04 scholar, 0x08 boastful, 0x10 wry,
-- 0x20 haunted, 0x40 savage, 0x80 sinister. It is stable for the life of the
-- character, so a given bot always has the same voice.
--
-- Channel: 0 say, 1 emote, 2 party, 3 guild. Emote bodies are blanked for the
-- opposite faction by the core, so emote lines carry atmosphere only.
--
-- Idempotent: safe to run more than once.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS `bot_lore_text`;
CREATE TABLE `bot_lore_text` (
  `Id`              int unsigned NOT NULL AUTO_INCREMENT,
  `Trigger`         varchar(32)  NOT NULL COMMENT 'zone_enter, quest_accept, quest_complete, kill, kill_boss, death, level_up, loot_rare, combat_start, idle',
  `ZoneId`          int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any zone',
  `AreaId`          int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any area',
  `CreatureEntry`   int unsigned NOT NULL DEFAULT '0' COMMENT 'kill triggers only; 0 = any',
  `RaceMask`        int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any race',
  `ClassMask`       int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any class',
  `PersonalityMask` int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any archetype',
  `QuestId`         int unsigned NOT NULL DEFAULT '0' COMMENT 'quest triggers only; 0 = any',
  `ItemId`          int unsigned NOT NULL DEFAULT '0' COMMENT 'loot triggers only; 0 = any',
  `ItemClass`       int          NOT NULL DEFAULT '-1' COMMENT 'loot triggers; -1 = any item class',
  `ItemSubClass`    int          NOT NULL DEFAULT '-1' COMMENT 'loot triggers; -1 = any subclass',
  `Gender`          tinyint      NOT NULL DEFAULT '-1' COMMENT '-1 any, 0 male, 1 female',
  `SpecMask`        int unsigned NOT NULL DEFAULT '0' COMMENT '0 = any; bit per talent tree, 1/2/4',
  `CreatureRank`    int          NOT NULL DEFAULT '-1' COMMENT '-1 any; 0 normal, 1 elite, 2 rare elite, 3 world boss, 4 rare',
  `MinQuality`      tinyint unsigned NOT NULL DEFAULT '0' COMMENT 'loot triggers; 0 = no lower bound. 2 uncommon, 3 rare, 4 epic, 5 legendary',
  `MaxQuality`      tinyint unsigned NOT NULL DEFAULT '0' COMMENT 'loot triggers; 0 = no upper bound',
  `GroupState`      tinyint unsigned NOT NULL DEFAULT '0' COMMENT '0 any, 1 alone, 2 in a group, 3 in a group with a real player',
  `TeamId`          tinyint      NOT NULL DEFAULT '-1' COMMENT '-1 any, 0 Alliance, 1 Horde',
  `MinLevel`        tinyint unsigned NOT NULL DEFAULT '0',
  `MaxLevel`        tinyint unsigned NOT NULL DEFAULT '0' COMMENT '0 = no upper bound',
  `Channel`         tinyint unsigned NOT NULL DEFAULT '0' COMMENT '0 say, 1 emote, 2 party, 3 guild',
  `Weight`          tinyint unsigned NOT NULL DEFAULT '1' COMMENT 'relative pick weight',
  `Text`            varchar(255) NOT NULL,
  `Comment`         varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `idx_trigger` (`Trigger`,`ZoneId`,`AreaId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

"""


def q(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


# =============================================================================
# The combinatorial half of the corpus. Lives in its own file because it is a
# different kind of writing: fragments along the axes mod-botlore can filter
# on (class, archetype, race, gender, spec, item category), multiplied out.
# It is driven from here so both halves append to the same row list.
# =============================================================================
import gen_bot_lore_combos

gen_bot_lore_combos.build(globals())



# =============================================================================
# The plain-text line files, data/lines/*.txt.
#
# Everything above is prose held in Python, which is right for lines that need
# a loop or a table of creature ids beside them. It is the wrong shape for five
# hundred hand-written lines whose only metadata is which filters they carry,
# so those live in text files instead, one section per filter combination:
#
#     @ trigger=combat_start rank=elite archetype=savage
#     Big one. Finally something that will not fall over when I look at it.
#
# A header names the filters, the lines under it inherit them, and a blank line
# means nothing. Editing the corpus is then editing prose, with no Python
# syntax to get wrong, and the files diff one line at a time.
#
# Every value is checked against the tables below and an unknown one stops the
# build, because the alternative is a filter silently reading as "any" and a
# line escaping into situations it was never written for.
# =============================================================================

_CLASS_BY_NAME = {
    "warrior": WARRIOR, "paladin": PALADIN, "hunter": HUNTER, "rogue": ROGUE,
    "priest": PRIEST, "death_knight": DEATH_KNIGHT, "shaman": SHAMAN,
    "mage": MAGE, "warlock": WARLOCK, "druid": DRUID,
}
_RACE_BY_NAME = {
    "human": HUMAN, "orc": ORC, "dwarf": DWARF, "nightelf": NIGHTELF,
    "undead": UNDEAD, "tauren": TAUREN, "gnome": GNOME, "troll": TROLL,
    "goblin": GOBLIN, "bloodelf": BLOODELF, "draenei": DRAENEI, "worgen": WORGEN,
}
_ARCH_BY_NAME = {
    "devout": DEVOUT, "grim": GRIM, "scholar": SCHOLAR, "boastful": BOASTFUL,
    "wry": WRY, "haunted": HAUNTED, "savage": SAVAGE, "sinister": SINISTER,
}
_RANK_BY_NAME = {
    "normal": RANK_NORMAL, "elite": RANK_ELITE, "rare_elite": RANK_RARE_ELITE,
    "world_boss": RANK_WORLD_BOSS, "rare": RANK_RARE,
}
# An exact grade, not a floor: a line written for a good find should not also
# fire on a legendary, which has its own lines and its own register.
_QUALITY_BY_NAME = {
    "uncommon": UNCOMMON, "rare": RARE, "epic": EPIC, "legendary": LEGENDARY,
}
_GROUP_BY_NAME = {
    "alone": GROUP_ALONE, "grouped": GROUP_GROUPED, "with_player": GROUP_WITH_PLAYER,
}
# Talent trees, as a mask of 1 << tree index. Resolved within the class because
# the names repeat: protection belongs to the warrior and the paladin, holy to
# the paladin and the priest, frost to the death knight and the mage, and
# restoration to the shaman and the druid. A spec= without a class= is an error.
_SPEC_BY_CLASS = {
    WARRIOR:      {"arms": 1, "fury": 2, "protection": 4},
    PALADIN:      {"holy": 1, "protection": 2, "retribution": 4},
    HUNTER:       {"beast_mastery": 1, "marksmanship": 2, "survival": 4},
    ROGUE:        {"assassination": 1, "combat": 2, "subtlety": 4},
    PRIEST:       {"discipline": 1, "holy": 2, "shadow": 4},
    DEATH_KNIGHT: {"blood": 1, "frost": 2, "unholy": 4},
    SHAMAN:       {"elemental": 1, "enhancement": 2, "restoration": 4},
    MAGE:         {"arcane": 1, "fire": 2, "frost": 4},
    WARLOCK:      {"affliction": 1, "demonology": 2, "destruction": 4},
    DRUID:        {"balance": 1, "feral": 2, "restoration": 4},
}

_TEAM_BY_NAME = {"alliance": ALLIANCE, "horde": HORDE}

_GENDER_BY_NAME = {"male": 0, "female": 1}

# ItemTemplate::Class, and the subclasses from ItemTemplate.h. Named rather
# than numbered in the line files, because "weapon=two_hand_axe" is legible in
# a diff and "iclass=2 isub=1" is not.
_ITEM_CLASS_WEAPON, _ITEM_CLASS_ARMOR = 2, 4

_WEAPON_BY_NAME = {
    "one_hand_axe": 0, "two_hand_axe": 1, "bow": 2, "gun": 3,
    "one_hand_mace": 4, "two_hand_mace": 5, "polearm": 6,
    "one_hand_sword": 7, "two_hand_sword": 8, "staff": 10, "fist": 13,
    "dagger": 15, "thrown": 16, "crossbow": 18, "wand": 19,
}

# ITEM_SUBCLASS_ARMOR_MISC is 0 and covers rings, necklaces and trinkets,
# which the filters cannot tell apart - only InventoryType distinguishes them
# and the corpus does not read it. Lines using it stay vague about the form.
_ARMOUR_BY_NAME = {
    "trinket": 0, "cloth": 1, "leather": 2, "mail": 3, "plate": 4, "shield": 6,
}

_TRIGGERS = {
    "zone_enter", "quest_accept", "quest_complete", "kill", "kill_boss",
    "death", "level_up", "loot_rare", "combat_start", "idle",
}

# Which placeholders the module actually fills for each trigger. A %item in a
# kill line would substitute to nothing and leave a hole in the sentence.
_ALLOWED_TOKENS = {
    "combat_start":   {"%target", "%zone", "%area", "%name"},
    "death":          {"%target", "%killer", "%zone", "%area", "%name"},
    "kill":           {"%target", "%zone", "%area", "%name"},
    "kill_boss":      {"%target", "%zone", "%area", "%name"},
    "level_up":       {"%zone", "%area", "%name"},
    "loot_rare":      {"%item", "%zone", "%area", "%name"},
    "zone_enter":     {"%zone", "%area", "%name"},
    "idle":           {"%zone", "%area", "%name"},
    "quest_accept":   {"%quest", "%zone", "%area", "%name"},
    "quest_complete": {"%quest", "%zone", "%area", "%name"},
}


def _filters_from_header(header, where):
    """Turn 'trigger=x rank=elite' into keyword arguments for line()."""
    spec = {}
    for token in header.split():
        assert "=" in token, f"{where}: header token without '=': {token!r}"
        key, value = token.split("=", 1)
        spec[key] = value

    trigger = spec.pop("trigger", None)
    assert trigger in _TRIGGERS, f"{where}: unknown trigger {trigger!r}"

    kw = {}
    for key, value in spec.items():
        if key == "class":
            kw["cls"] = _CLASS_BY_NAME[value] if value in _CLASS_BY_NAME else _fail(where, key, value)
        elif key == "race":
            kw["race"] = _RACE_BY_NAME[value] if value in _RACE_BY_NAME else _fail(where, key, value)
        elif key == "archetype":
            kw["personality"] = _ARCH_BY_NAME[value] if value in _ARCH_BY_NAME else _fail(where, key, value)
        elif key == "rank":
            kw["rank"] = _RANK_BY_NAME[value] if value in _RANK_BY_NAME else _fail(where, key, value)
        elif key == "quality":
            grade = _QUALITY_BY_NAME[value] if value in _QUALITY_BY_NAME else _fail(where, key, value)
            kw["minq"] = kw["maxq"] = grade
        elif key == "group":
            kw["group"] = _GROUP_BY_NAME[value] if value in _GROUP_BY_NAME else _fail(where, key, value)
        elif key == "gender":
            kw["gender"] = _GENDER_BY_NAME[value] if value in _GENDER_BY_NAME else _fail(where, key, value)
        elif key == "spec":
            pass    # resolved below, once the class is known
        elif key == "team":
            kw["team"] = _TEAM_BY_NAME[value] if value in _TEAM_BY_NAME else _fail(where, key, value)
        elif key == "minlevel":
            assert value.isdigit(), f"{where}: minlevel must be a number, got {value!r}"
            kw["minlvl"] = int(value)
        elif key == "maxlevel":
            assert value.isdigit(), f"{where}: maxlevel must be a number, got {value!r}"
            kw["maxlvl"] = int(value)
        elif key == "weapon":
            kw["iclass"] = _ITEM_CLASS_WEAPON
            kw["isub"] = _WEAPON_BY_NAME[value] if value in _WEAPON_BY_NAME else _fail(where, key, value)
        elif key == "armour":
            kw["iclass"] = _ITEM_CLASS_ARMOR
            kw["isub"] = _ARMOUR_BY_NAME[value] if value in _ARMOUR_BY_NAME else _fail(where, key, value)
        elif key == "zone":
            assert value.isdigit(), f"{where}: zone must be a number, got {value!r}"
            kw["zone"] = int(value)
        elif key == "area":
            assert value.isdigit(), f"{where}: area must be a number, got {value!r}"
            kw["area"] = int(value)
        elif key == "weight":
            kw["weight"] = int(value)
        else:
            raise AssertionError(f"{where}: unknown filter {key!r}")

    if "spec" in spec:
        assert "cls" in kw, f"{where}: spec= needs a class=, because spec names repeat across classes"
        trees = _SPEC_BY_CLASS[kw["cls"]]
        name = spec["spec"]
        assert name in trees, \
            f"{where}: spec={name!r} is not one of {sorted(trees)} for that class"
        kw["spec"] = trees[name]

    if "minlvl" in kw and "maxlvl" in kw:
        assert kw["minlvl"] <= kw["maxlvl"], \
            f"{where}: minlevel {kw['minlvl']} is above maxlevel {kw['maxlvl']}, so nothing can match"

    return trigger, kw


def _fail(where, key, value):
    raise AssertionError(f"{where}: {key}={value!r} is not a known value")


def load_line_files():
    here = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(here, "..", "data", "lines")
    loaded = 0

    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        name = os.path.basename(path)
        trigger, kw = None, None
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                text = raw.rstrip("\n")
                where = f"{name}:{lineno}"
                if not text.strip() or text.lstrip().startswith("#"):
                    continue
                if text.startswith("@ "):
                    trigger, kw = _filters_from_header(text[2:], where)
                    continue
                assert trigger, f"{where}: a line before any @ header"
                for token in set(re.findall(r"%\w+", text)):
                    assert token in _ALLOWED_TOKENS[trigger], \
                        f"{where}: {token} is not substituted on {trigger}"
                # Weight 3, matching the other authored lines: specificity does
                # most of the work, this keeps a hand-written line ahead of a
                # generic one of equal specificity.
                line(trigger, text, weight=kw.get("weight", 3),
                     comment=f"{name} line {lineno}",
                     **{k: v for k, v in kw.items() if k != "weight"})
                loaded += 1

    return loaded

def dedupe():
    seen = set()
    kept = []
    for r in rows:
        key = (r["trigger"], r["text"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)
    dropped = len(rows) - len(kept)
    rows[:] = kept
    return dropped


def main():
    from_files = load_line_files()
    dropped = dedupe()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "data", "sql", "db-world", "base", "botlore_lore_text.sql")

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(HEADER)
        fh.write("INSERT INTO `bot_lore_text` (`Trigger`, ZoneId, AreaId, CreatureEntry, "
                 "RaceMask, ClassMask, PersonalityMask, QuestId, ItemId, ItemClass, "
                 "ItemSubClass, Gender, SpecMask, TeamId, MinLevel, MaxLevel, CreatureRank, "
                 "MinQuality, MaxQuality, GroupState, Channel, Weight, Text, Comment) VALUES\n")
        parts = []
        for r in rows:
            parts.append("({})".format(", ".join(str(v) for v in (
                q(r["trigger"]), r["zone"], r["area"], r["creature"], r["race"], r["cls"],
                r["personality"], r["quest"], r["item"], r["iclass"], r["isub"], r["gender"],
                r["spec"], r["team"], r["minlvl"], r["maxlvl"], r["rank"], r["minq"],
                r["maxq"], r["group"], r["channel"], r["weight"],
                q(r["text"]), q(r["comment"])))))
        fh.write(",\n".join(parts) + ";\n")

    triggers = {}
    for r in rows:
        triggers[r["trigger"]] = triggers.get(r["trigger"], 0) + 1

    print(f"wrote {os.path.normpath(out)}: {len(rows)} lines "
          f"({from_files} from data/lines, {dropped} duplicates dropped)")
    for t, n in sorted(triggers.items(), key=lambda kv: -kv[1]):
        print(f"  {t:<16}{n:>5}")


if __name__ == "__main__":
    main()
