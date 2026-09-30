# mod-botlore

Lore-flavoured local chatter for playerbots, driven by a world database
table.

mod-playerbots' own chatter is almost entirely channel broadcasts ("Wanna
party in Duskwood.", "WTS [item] for 5g."), and its local `/say` flavour is
dead code: `SayStrategy` is never registered, so those text buckets never
fire. This module fills the gap - bots comment on what they are doing and
where they are, in `/say`, `/emote`, party and guild, from an SQL-editable
line table that can be reloaded in game.

## Bundled SQL

The table and its content both ship with the module. `data/sql/db-world/base/botlore_lore_text.sql`
creates the table and fills it with 11,868 lines across the ten triggers, and
the core's database updater applies it at startup for every enabled module:
`UpdateFetcher::ReceiveIncludedDirectories` walks
`modules/<name>/data/sql/db-world`, and a `MODULE` file whose hash has changed
is re-applied, so regenerating the corpus and restarting is enough to publish
it. Nothing has to be applied by hand.

That file is generated. The corpus itself is kept in two shapes:

    data/lines/*.txt               most of it - plain text, a header naming the
                                   filters and the lines under it inheriting
                                   them. Fifty files, 2,568 lines, each a slice
                                   of the filter space
    tools/gen_bot_lore.py          the lines that need code beside them: a loop,
                                   or a table of creature and quest ids. Also
                                   the loader for data/lines and the schema
    tools/gen_bot_lore_combos.py   retired. Fragments multiplied out into joined
                                   pairs; it supplied nine lines in ten until
                                   the joins turned out to be why the corpus
                                   read as machine-made. AUTHORED_ONLY lists
                                   every trigger now, which switches it off.
                                   Dropping a trigger from that set puts its
                                   joined lines back

A line file looks like this, and a bad filter value stops the build rather than
silently reading as "any":

    @ trigger=combat_start rank=elite archetype=savage
    Big one. Finally something that will not fall over when I look at it.
    %target has real weight to it. Good. I want to feel the swing land.

Talent trees are named per class rather than numbered, and resolved inside the
class, because the names collide: protection belongs to the warrior and the
paladin, frost to the death knight and the mage, restoration to the shaman and
the druid. A `spec=` without a `class=` is a build error, and so is
`spec=arms` on a mage. Career stage is `minlevel=`/`maxlevel=`, so a character
three weeks out of their village does not sound like one who has walked
Northrend, and `team=alliance` or `team=horde` carries the war.

`rank=normal` is the workhorse of that vocabulary. Most combat lines are written
for the common case, where the enemy is a small animal, and `%target`
substitutes the real creature name - so understatement aimed at a named rare
reads as farce. Those lines are gated on `rank=normal` and cannot fire on
anything notable. Item kinds are named rather than numbered for the same reason
of legibility: `weapon=two_hand_axe` and `armour=trinket` rather than
`iclass=2 isub=1`.

Run `python3 tools/gen_bot_lore.py` to rewrite the SQL file; it loads
`data/lines` itself and prints the per-trigger counts. To publish without a
restart, apply the regenerated file by hand and run `.botlore reload` - the
corpus is data, so it needs no rebuild.

## The table

`bot_lore_text` in the world database: a trigger name, the line, and filter
columns that are all "any" when left at their default - zone, area, creature
entry, creature rank, race mask, class mask, team, level range, item quality
range, item class/subclass, gender, spec mask, group state. A more specific
line outweighs a generic one rather than suppressing it, so hand-written
Duskwood lines show up in Duskwood without the rest of the corpus going
unheard. Placeholders `%zone`, `%area`, `%target`, `%quest`, `%item`, `%name`
are substituted at emit time.

Triggers: `zone_enter`, `quest_accept`, `quest_complete`, `kill`,
`kill_boss`, `death`, `level_up`, `loot_rare`, `combat_start`, `idle`.

Three of the filters are about *how notable* the thing is rather than which
thing it is, which is what lets one line cover every elite instead of naming
each one:

* `CreatureRank` - `-1` any, then `CreatureTemplate::rank`: 0 ordinary,
  1 elite, 2 rare elite, 3 world boss, 4 rare. `-1` rather than 0 is the
  wildcard because 0 is a real rank. Set on `kill`, `kill_boss`, `death` and
  `combat_start`; left at `-1` when the other party is a player.
* `MinQuality` / `MaxQuality` - an item quality range in the style of
  `MinLevel`/`MaxLevel`, where 0 at either end means no bound: 2 uncommon,
  3 rare, 4 epic, 5 legendary. An epic-only line is `MinQuality` 4; a rare
  line that must not fire on epics is 3 and 3.
* `GroupState` - 0 any, 1 alone, 2 in a group, 3 in a group holding a real
  player. The last exists because lines like "stay close to me" and "watch my
  left" need somebody there to hear them, and a group of nothing but bots is
  not somebody.

`%level` is deliberately absent from the corpus. A character who announces a
number is describing a game statistic; one who notices their hands are
steadier than yesterday is not.

## Keeping it quiet

With hundreds of bots the gating matters more than the lines. In order:
feature and trigger enabled, any real player online at all (a cached GUID
set, so an empty realm costs one branch), bot-ness, a real player within
`RangeYards`, a per-bot cooldown, then the chance roll. No grid searches.

## Configuration (`mod_botlore.conf`)

`BotLore.Enable`, `.Chance`, `.CooldownSeconds`, `.RangeYards`,
`.IdleSeconds`, `.LoginGraceSeconds`, `.AvoidRepeats`, `.SpecificityWeight`,
per-trigger chances (`.Chance.KillBoss`, `.Chance.LevelUp`, `.Chance.Death`)
and per-trigger switches (`.Trigger.*`). Read in `OnAfterConfigLoad`, so
`reload config` applies them live.

## Commands

    .botlore reload                        re-read the table, no restart
    .botlore list [trigger]                print the loaded lines and filters
    .botlore test <bot> [trigger] [options...]   resolve and emit one line

`test` takes any number of trailing options. A bare number is an entry id, as
it always was; the rest are `key=value`, in any order:

    entry=<id>       a creature, item or quest, depending on the trigger
    rank=<kind>      any, normal, elite, rare_elite, world_boss, rare, or 0-4
    quality=<grade>  poor, common, uncommon, rare, epic, legendary, or 0-5
                     (colours work too: grey, white, green, blue, purple,
                     orange; `rarity=` is accepted as a synonym)

So:

    .botlore test Fyraes combat_start rank=elite
    .botlore test Fyraes loot_rare quality=legendary
    .botlore test Fyraes kill_boss entry=448

`rank` and `quality` exist because without them the rank- and quality-gated
lines were **unreachable from the console**. The command supplies no creature
and no item, so the context carried rank -1 and quality 0, and every line gated
on either was silently excluded from the draw - they could only be seen by
finding a real elite or waiting for a real epic to drop. An entry id now also
carries its own rank or quality from the template, and an explicit option
overrides it, so a kobold can be tested as though it were a world boss.

An unrecognised option is an error rather than being ignored, because a
silently dropped filter would make the command lie about what it tested. The
command also prints the bot's group state, since that filter comes from the
real group and cannot be forced.

## Requirements

Nothing external: the table and its content are bundled, as above. The table
is loaded in `OnStartup`, not
`OnAfterConfigLoad`, because the DBC and object stores do not exist yet at
config-load time and every row would be discarded.

## Licence

GNU Affero General Public License v3.0, the licence AzerothCore and its
modules use. See [LICENSE](LICENSE).
