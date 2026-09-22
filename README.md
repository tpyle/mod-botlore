# mod-botlore

Lore-flavoured local chatter for playerbots, driven by a world database
table.

mod-playerbots' own chatter is almost entirely channel broadcasts ("Wanna
party in Duskwood.", "WTS [item] for 5g."), and its local `/say` flavour is
dead code: `SayStrategy` is never registered, so those text buckets never
fire. This module fills the gap - bots comment on what they are doing and
where they are, in `/say`, `/emote`, party and guild, from an SQL-editable
line table that can be reloaded in game.

## The table

`bot_lore_text` in the world database: a trigger name, the line, and filter
columns that are all "any" when left at 0 - zone, area, creature entry, race
mask, class mask, team, level range, item class/subclass, gender, spec mask.
A specific match suppresses generic candidates, so hand-written Duskwood
lines actually show up in Duskwood. Placeholders `%zone`, `%area`, `%target`,
`%quest`, `%item`, `%level`, `%name` are substituted at emit time.

Triggers: `zone_enter`, `quest_accept`, `quest_complete`, `kill`,
`kill_boss`, `death`, `level_up`, `loot_rare`, `combat_start`, `idle`.

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

    .botlore reload                       re-read the table, no restart
    .botlore list [trigger]               print the loaded lines and filters
    .botlore test <bot> <trigger> [entry] resolve and emit one line

## Requirements

The `bot_lore_text` table and its content (see the server project's
`sql/` directory). The table is loaded in `OnStartup`, not
`OnAfterConfigLoad`, because the DBC and object stores do not exist yet at
config-load time and every row would be discarded.
