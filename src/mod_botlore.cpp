/*
 * mod-botlore - lore-flavoured chatter for playerbots
 *
 * The bots that ship with mod-playerbots barely speak in the world. What they
 * do say goes to the World/General/Guild *channels* (BroadcastHelper.cpp) and
 * reads like trade chat: "Wanna party in Duskwood.", "WTS [item]". Their local
 * flavour is dead code - SayStrategy is never registered in StrategyContext.h,
 * so the taunt/aoe/low health/loot text buckets never fire, and the texts
 * themselves load once at startup with no reload command.
 *
 * So rather than patch the playerbots fork, this module adds the missing layer:
 * hand-written lines, held in the world database table `bot_lore_text`, chosen
 * by what the bot is doing and where it is standing, spoken locally with /say
 * and /emote (and in party or guild where a line asks for it).
 *
 * Bots are identified by WorldSession::IsBot(), which is exactly the set of
 * fabricated sessions mod-playerbots creates for its random population. That
 * keeps this module free of any playerbots header - nothing here breaks when
 * the fork moves. The trade-off is that a player's own alt bots ("selfbots")
 * run on real sessions and are left alone.
 *
 * Restraint is the whole design problem with 500 bots, so a line needs to pass,
 * in this order: the trigger is enabled, a real player is logged in at all, the
 * speaker is a bot, a real player is within earshot, the bot's own cooldown has
 * expired, and a chance roll succeeds. With nobody logged in the cost is a
 * single branch, because the real-player set is empty.
 */

#include "Chat.h"
#include "Config.h"
#include "Creature.h"
#include "DBCStores.h"
#include "DBCStructure.h"
#include "DatabaseEnv.h"
#include "GameTime.h"
#include "Group.h"
#include "Guild.h"
#include "GuildMgr.h"
#include "Item.h"
#include "ItemTemplate.h"
#include "Log.h"
#include "ObjectAccessor.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "QuestDef.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"
#include "StringFormat.h"
#include "World.h"
#include "WorldSession.h"

#include <algorithm>
#include <cctype>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace Acore::ChatCommands;

namespace
{
    constexpr char const* DATA_KEY = "BotLoreData";

    // Trigger names as they appear in bot_lore_text.Trigger
    constexpr char const* TRIGGER_ZONE_ENTER     = "zone_enter";
    constexpr char const* TRIGGER_QUEST_ACCEPT   = "quest_accept";
    constexpr char const* TRIGGER_QUEST_COMPLETE = "quest_complete";
    constexpr char const* TRIGGER_KILL           = "kill";
    constexpr char const* TRIGGER_KILL_BOSS      = "kill_boss";
    constexpr char const* TRIGGER_DEATH          = "death";
    constexpr char const* TRIGGER_LEVEL_UP       = "level_up";
    constexpr char const* TRIGGER_LOOT_RARE      = "loot_rare";
    constexpr char const* TRIGGER_COMBAT_START   = "combat_start";
    constexpr char const* TRIGGER_IDLE           = "idle";

    enum LoreChannel : uint8
    {
        CHANNEL_SAY   = 0,
        CHANNEL_EMOTE = 1,
        CHANNEL_PARTY = 2,
        CHANNEL_GUILD = 3
    };

    // Eight archetypes. A bot's own one is derived from its name, so it never
    // changes, and each class may only draw from archetypes that suit it - a
    // Warlock is never Devout, a Paladin is never Sinister.
    enum Personality : uint32
    {
        PERSONALITY_DEVOUT   = 0x01,
        PERSONALITY_GRIM     = 0x02,
        PERSONALITY_SCHOLAR  = 0x04,
        PERSONALITY_BOASTFUL = 0x08,
        PERSONALITY_WRY      = 0x10,
        PERSONALITY_HAUNTED  = 0x20,
        PERSONALITY_SAVAGE   = 0x40,
        PERSONALITY_SINISTER = 0x80
    };

    char const* PersonalityName(uint32 personality)
    {
        switch (personality)
        {
            case PERSONALITY_DEVOUT:   return "devout";
            case PERSONALITY_GRIM:     return "grim";
            case PERSONALITY_SCHOLAR:  return "scholar";
            case PERSONALITY_BOASTFUL: return "boastful";
            case PERSONALITY_WRY:      return "wry";
            case PERSONALITY_HAUNTED:  return "haunted";
            case PERSONALITY_SAVAGE:   return "savage";
            case PERSONALITY_SINISTER: return "sinister";
            default:                   return "none";
        }
    }

    std::vector<uint32> const& PersonalitiesForClass(uint8 classId)
    {
        static std::vector<uint32> const none;
        static std::unordered_map<uint8, std::vector<uint32>> const byClass =
        {
            { CLASS_WARRIOR,      { PERSONALITY_BOASTFUL, PERSONALITY_GRIM,    PERSONALITY_SAVAGE,  PERSONALITY_WRY      } },
            { CLASS_PALADIN,      { PERSONALITY_DEVOUT,   PERSONALITY_BOASTFUL, PERSONALITY_GRIM,   PERSONALITY_HAUNTED  } },
            { CLASS_HUNTER,       { PERSONALITY_SAVAGE,   PERSONALITY_WRY,     PERSONALITY_SCHOLAR, PERSONALITY_GRIM     } },
            { CLASS_ROGUE,        { PERSONALITY_WRY,      PERSONALITY_SINISTER, PERSONALITY_GRIM,   PERSONALITY_SAVAGE   } },
            { CLASS_PRIEST,       { PERSONALITY_DEVOUT,   PERSONALITY_HAUNTED, PERSONALITY_SCHOLAR, PERSONALITY_GRIM     } },
            { CLASS_DEATH_KNIGHT, { PERSONALITY_GRIM,     PERSONALITY_HAUNTED, PERSONALITY_SINISTER, PERSONALITY_SAVAGE  } },
            { CLASS_SHAMAN,       { PERSONALITY_SCHOLAR,  PERSONALITY_DEVOUT,  PERSONALITY_SAVAGE,  PERSONALITY_HAUNTED  } },
            { CLASS_MAGE,         { PERSONALITY_SCHOLAR,  PERSONALITY_WRY,     PERSONALITY_BOASTFUL, PERSONALITY_SINISTER } },
            { CLASS_WARLOCK,      { PERSONALITY_SINISTER, PERSONALITY_SCHOLAR, PERSONALITY_WRY,     PERSONALITY_GRIM     } },
            { CLASS_DRUID,        { PERSONALITY_SCHOLAR,  PERSONALITY_SAVAGE,  PERSONALITY_DEVOUT,  PERSONALITY_HAUNTED  } }
        };

        auto const itr = byClass.find(classId);
        return itr != byClass.end() ? itr->second : none;
    }

    // Stable for the life of the character: same name, same class, same
    // archetype, every login and across restarts. FNV-1a over the name so the
    // spread does not depend on the standard library's hash.
    uint32 PersonalityFor(Player* bot)
    {
        std::vector<uint32> const& allowed = PersonalitiesForClass(bot->getClass());
        if (allowed.empty())
            return 0;

        uint32 hash = 2166136261u;
        for (char const c : bot->GetName())
        {
            hash ^= uint32(uint8(std::tolower(uint8(c))));
            hash *= 16777619u;
        }

        return allowed[hash % allowed.size()];
    }

    struct LoreLine
    {
        uint32      id = 0;
        uint32      zoneId = 0;
        uint32      areaId = 0;
        uint32      creatureEntry = 0;
        uint32      raceMask = 0;
        uint32      classMask = 0;
        uint32      personalityMask = 0;
        uint32      questId = 0;
        uint32      itemId = 0;
        int32       itemClass = -1;
        int32       itemSubClass = -1;
        int8        gender = -1;
        uint32      specMask = 0;
        int8        teamId = -1;
        uint8       minLevel = 0;
        uint8       maxLevel = 0;
        uint8       channel = CHANNEL_SAY;
        uint8       weight = 1;
        std::string text;

        // How specific this line is. A line written for one zone, or for one
        // creature, beats a generic one so hand-written Duskwood lines
        // actually turn up in Duskwood.
        uint32 Specificity() const
        {
            uint32 score = 0;
            if (zoneId)
                score += 1;
            if (areaId)
                score += 2;
            if (creatureEntry)
                score += 2;
            if (questId)
                score += 3;
            if (itemId)
                score += 3;
            if (itemSubClass >= 0)
                score += 2;
            else if (itemClass >= 0)
                score += 1;
            if (gender >= 0)
                score += 1;
            if (specMask)
                score += 1;
            if (classMask)
                score += 1;
            if (personalityMask)
                score += 1;
            return score;
        }
    };

    // trigger -> lines
    std::unordered_map<std::string, std::vector<LoreLine>> lines;

    // Real (non-bot) players currently online. Bots only talk when one of
    // these is within earshot, so an empty set short-circuits everything.
    std::unordered_set<ObjectGuid> listeners;

    struct BotLoreConfig
    {
        bool   Enable = true;
        uint32 Chance = 25;
        uint32 CooldownSeconds = 240;
        float  RangeYards = 40.0f;
        uint32 IdleSeconds = 600;
        uint32 LoginGraceSeconds = 60;
        bool   AvoidRepeats = true;
        uint32 SpecificityWeight = 6;

        bool ZoneEnter = true;
        bool QuestAccept = true;
        bool QuestComplete = true;
        bool KillBoss = true;
        bool Kill = false;
        bool Death = true;
        bool LevelUp = true;
        bool LootRare = true;
        bool CombatStart = false;
        bool Idle = false;

        int32 ChanceKillBoss = 75;
        int32 ChanceLevelUp = 60;
        int32 ChanceDeath = -1;
    };

    BotLoreConfig cfg;

    struct BotLoreData : public DataMap::Base
    {
        time_t nextLine = 0;    // cooldown expiry
        time_t graceUntil = 0;  // silent window after login
        uint32 idleTimer = 0;   // counts down to the next idle line
        uint32 lastLineId = 0;  // so a bot does not repeat itself
    };

    // Everything a line might want to talk about.
    struct LoreContext
    {
        uint32      zoneId = 0;
        uint32      areaId = 0;
        uint32      creatureEntry = 0;
        uint32      questId = 0;
        uint32      itemId = 0;
        int32       itemClass = -1;
        int32       itemSubClass = -1;
        uint32      personality = 0;
        std::string target;
        std::string quest;
        std::string item;
    };

    void LoadConfig()
    {
        cfg.Enable          = sConfigMgr->GetOption<bool>("BotLore.Enable", true);
        cfg.Chance          = std::min<uint32>(sConfigMgr->GetOption<uint32>("BotLore.Chance", 25), 100);
        cfg.CooldownSeconds = sConfigMgr->GetOption<uint32>("BotLore.CooldownSeconds", 240);
        cfg.RangeYards      = sConfigMgr->GetOption<float>("BotLore.RangeYards", 40.0f);
        cfg.IdleSeconds     = sConfigMgr->GetOption<uint32>("BotLore.IdleSeconds", 600);
        cfg.LoginGraceSeconds = sConfigMgr->GetOption<uint32>("BotLore.LoginGraceSeconds", 60);
        cfg.AvoidRepeats      = sConfigMgr->GetOption<bool>("BotLore.AvoidRepeats", true);
        cfg.SpecificityWeight = sConfigMgr->GetOption<uint32>("BotLore.SpecificityWeight", 6);

        // -1 keeps the global chance. A boss kill deserves remarking on nearly
        // every time; walking into a zone does not.
        cfg.ChanceKillBoss = sConfigMgr->GetOption<int32>("BotLore.Chance.KillBoss", 75);
        cfg.ChanceLevelUp  = sConfigMgr->GetOption<int32>("BotLore.Chance.LevelUp", 60);
        cfg.ChanceDeath    = sConfigMgr->GetOption<int32>("BotLore.Chance.Death", -1);

        cfg.ZoneEnter     = sConfigMgr->GetOption<bool>("BotLore.Trigger.ZoneEnter", true);
        cfg.QuestAccept   = sConfigMgr->GetOption<bool>("BotLore.Trigger.QuestAccept", true);
        cfg.QuestComplete = sConfigMgr->GetOption<bool>("BotLore.Trigger.QuestComplete", true);
        cfg.KillBoss      = sConfigMgr->GetOption<bool>("BotLore.Trigger.KillBoss", true);
        cfg.Kill          = sConfigMgr->GetOption<bool>("BotLore.Trigger.Kill", false);
        cfg.Death         = sConfigMgr->GetOption<bool>("BotLore.Trigger.Death", true);
        cfg.LevelUp       = sConfigMgr->GetOption<bool>("BotLore.Trigger.LevelUp", true);
        cfg.LootRare      = sConfigMgr->GetOption<bool>("BotLore.Trigger.LootRare", true);
        cfg.CombatStart   = sConfigMgr->GetOption<bool>("BotLore.Trigger.CombatStart", false);
        cfg.Idle          = sConfigMgr->GetOption<bool>("BotLore.Trigger.Idle", false);

        if (cfg.RangeYards <= 0.0f)
            cfg.RangeYards = 40.0f;
    }

    uint32 LoadLines()
    {
        lines.clear();

        QueryResult result = WorldDatabase.Query(
            "SELECT `Trigger`, ZoneId, AreaId, CreatureEntry, RaceMask, ClassMask, TeamId, "
            "MinLevel, MaxLevel, Channel, Weight, Text, Id, PersonalityMask, QuestId, ItemId, "
            "ItemClass, ItemSubClass, Gender, SpecMask FROM bot_lore_text");

        if (!result)
        {
            LOG_WARN("module", "mod-botlore: table `bot_lore_text` is missing or empty, bots will stay quiet. "
                               "Apply sql/13_bot_lore.sql.");
            return 0;
        }

        uint32 count = 0;
        do
        {
            Field* fields = result->Fetch();

            std::string const trigger = fields[0].Get<std::string>();
            std::string const text = fields[11].Get<std::string>();

            if (trigger.empty() || text.empty())
            {
                LOG_ERROR("sql.sql", "mod-botlore: `bot_lore_text` row with an empty trigger or text, skipped.");
                continue;
            }

            // The direct Player::Say path skips the length trim and the
            // hyperlink validation the chat opcode would have done, so bad
            // rows have to be caught here.
            if (text.size() > 255 || text.find('|') != std::string::npos)
            {
                LOG_ERROR("sql.sql", "mod-botlore: `bot_lore_text` text for trigger '{}' is too long or contains '|', skipped: {}",
                    trigger, text);
                continue;
            }

            LoreLine line;
            line.zoneId        = fields[1].Get<uint32>();
            line.areaId        = fields[2].Get<uint32>();
            line.creatureEntry = fields[3].Get<uint32>();
            line.raceMask      = fields[4].Get<uint32>();
            line.classMask     = fields[5].Get<uint32>();
            line.teamId        = fields[6].Get<int8>();
            line.minLevel      = fields[7].Get<uint8>();
            line.maxLevel      = fields[8].Get<uint8>();
            line.channel       = fields[9].Get<uint8>();
            line.weight        = std::max<uint8>(fields[10].Get<uint8>(), 1);
            line.text          = text;
            line.id            = fields[12].Get<uint32>();
            line.personalityMask = fields[13].Get<uint32>();
            line.questId       = fields[14].Get<uint32>();
            line.itemId        = fields[15].Get<uint32>();
            line.itemClass     = fields[16].Get<int32>();
            line.itemSubClass  = fields[17].Get<int32>();
            line.gender        = fields[18].Get<int8>();
            line.specMask      = fields[19].Get<uint32>();

            if (line.channel > CHANNEL_GUILD)
            {
                LOG_ERROR("sql.sql", "mod-botlore: `bot_lore_text` row for trigger '{}' has unknown Channel {}, using say.",
                    trigger, line.channel);
                line.channel = CHANNEL_SAY;
            }

            lines[trigger].push_back(std::move(line));
            ++count;
        } while (result->NextRow());

        LOG_INFO("module", "mod-botlore: loaded {} lore line(s) across {} trigger(s)", count, lines.size());
        return count;
    }

    bool IsBot(Player* player)
    {
        return player && player->GetSession() && player->GetSession()->IsBot();
    }

    // Mirrors PlayerbotAI::GetLocalizedAreaName: several AreaTable locale slots
    // are empty, so fall back to enUS rather than printing nothing.
    std::string AreaName(uint32 areaId)
    {
        AreaTableEntry const* area = sAreaTableStore.LookupEntry(areaId);
        if (!area)
            return "";

        if (char const* name = area->area_name[sWorld->GetDefaultDbcLocale()])
            if (*name)
                return name;

        if (char const* name = area->area_name[LOCALE_enUS])
            return name;

        return "";
    }

    bool HasListenerNearby(Player* bot)
    {
        // Walking the handful of real players is far cheaper than a grid
        // search per bot per trigger.
        for (ObjectGuid const& guid : listeners)
            if (Player* listener = ObjectAccessor::FindPlayer(guid))
                if (bot->IsWithinDistInMap(listener, cfg.RangeYards))
                    return true;

        return false;
    }

    bool MatchesFilters(LoreLine const& line, Player* bot, LoreContext const& context)
    {
        if (line.zoneId && line.zoneId != context.zoneId)
            return false;
        if (line.areaId && line.areaId != context.areaId)
            return false;
        if (line.creatureEntry && line.creatureEntry != context.creatureEntry)
            return false;
        if (line.raceMask && !(line.raceMask & bot->getRaceMask()))
            return false;
        if (line.classMask && !(line.classMask & bot->getClassMask()))
            return false;
        if (line.personalityMask && !(line.personalityMask & context.personality))
            return false;
        if (line.questId && line.questId != context.questId)
            return false;
        if (line.itemId && line.itemId != context.itemId)
            return false;
        if (line.itemClass >= 0 && line.itemClass != context.itemClass)
            return false;
        if (line.itemSubClass >= 0 && line.itemSubClass != context.itemSubClass)
            return false;
        if (line.gender >= 0 && line.gender != int8(bot->getGender()))
            return false;
        // Talent tree with the most points spent, as a bit. The core's
        // GetMostPointsTalentTree weighs three counters and returns the index
        // of the largest, so with nothing spent it returns 0 rather than
        // "no spec" - every fresh character would read as Arms, Holy, Beast
        // Mastery and so on. An empty talent map is the honest test, and it
        // keeps spec lines silent until the bot has actually chosen.
        if (line.specMask)
        {
            if (bot->GetTalentMap().empty())
                return false;

            uint8 const tree = bot->GetMostPointsTalentTree();
            if (tree > 2 || !(line.specMask & (1u << tree)))
                return false;
        }
        if (line.teamId >= 0 && line.teamId != int8(bot->GetTeamId()))
            return false;
        if (line.minLevel && bot->GetLevel() < line.minLevel)
            return false;
        if (line.maxLevel && bot->GetLevel() > line.maxLevel)
            return false;

        return true;
    }

    LoreLine const* PickLine(std::string const& trigger, Player* bot, LoreContext const& context, uint32 avoidId)
    {
        auto const itr = lines.find(trigger);
        if (itr == lines.end())
            return nullptr;

        // Specificity used to be a hard filter: the most specific matching
        // lines were kept and everything else thrown away. That made the pool
        // in any given situation tiny - standing in Duskwood, the handful of
        // Duskwood lines were the *only* candidates and several hundred
        // archetype and generic lines could never be heard, so a player in one
        // zone heard the same few lines over and over.
        //
        // It is a weight multiplier instead. A line written for one quest or
        // one item still overwhelmingly wins, but the whole matching corpus
        // stays in the draw, which is what keeps a long session from
        // repeating.
        std::vector<LoreLine const*> candidates;
        std::vector<uint32> weights;

        for (LoreLine const& line : itr->second)
        {
            if (!MatchesFilters(line, bot, context))
                continue;

            candidates.push_back(&line);
            weights.push_back(uint32(line.weight) * (1 + line.Specificity() * cfg.SpecificityWeight));
        }

        if (candidates.empty())
            return nullptr;

        // Drop the line this bot said last time, unless it was the only one.
        if (cfg.AvoidRepeats && avoidId && candidates.size() > 1)
            for (std::size_t i = 0; i < candidates.size(); ++i)
                if (candidates[i]->id == avoidId)
                {
                    candidates.erase(candidates.begin() + i);
                    weights.erase(weights.begin() + i);
                    break;
                }

        if (candidates.empty())
            return nullptr;

        uint32 total = 0;
        for (uint32 const weight : weights)
            total += weight;

        if (!total)
            return candidates.front();

        uint32 roll = urand(0, total - 1);
        for (std::size_t i = 0; i < candidates.size(); ++i)
        {
            if (roll < weights[i])
                return candidates[i];

            roll -= weights[i];
        }

        return candidates.back();
    }

    std::string Substitute(std::string text, Player* bot, LoreContext const& context)
    {
        auto replace = [&text](std::string const& token, std::string const& value)
        {
            for (std::size_t at = text.find(token); at != std::string::npos; at = text.find(token, at))
                text.replace(at, token.size(), value);
        };

        replace("%zone", AreaName(context.zoneId));
        replace("%area", AreaName(context.areaId ? context.areaId : context.zoneId));
        replace("%target", context.target);
        replace("%killer", context.target);   // friendlier name for death lines
        replace("%quest", context.quest);
        replace("%item", context.item);
        replace("%level", std::to_string(bot->GetLevel()));
        replace("%name", bot->GetName());
        replace("%faction", bot->GetTeamId() == TEAM_ALLIANCE ? "Alliance" : "Horde");

        if (text.find("%class") != std::string::npos)
            if (ChrClassesEntry const* entry = sChrClassesStore.LookupEntry(bot->getClass()))
                replace("%class", entry->name[sWorld->GetDefaultDbcLocale()] ? entry->name[sWorld->GetDefaultDbcLocale()]
                                                                            : entry->name[LOCALE_enUS]);

        if (text.find("%race") != std::string::npos)
            if (ChrRacesEntry const* entry = sChrRacesStore.LookupEntry(bot->getRace(true)))
                replace("%race", entry->name[sWorld->GetDefaultDbcLocale()] ? entry->name[sWorld->GetDefaultDbcLocale()]
                                                                           : entry->name[LOCALE_enUS]);

        return text;
    }

    void Emit(Player* bot, LoreLine const& line, std::string const& text)
    {
        Language const language = bot->GetTeamId() == TEAM_ALLIANCE ? LANG_COMMON : LANG_ORCISH;

        switch (line.channel)
        {
            case CHANNEL_EMOTE:
                // Always universal, and the opposite faction sees an empty
                // body - emote lines carry atmosphere, not information.
                bot->TextEmote(text);
                break;

            case CHANNEL_PARTY:
                if (Group* group = bot->GetGroup())
                {
                    WorldPacket data;
                    ChatHandler::BuildChatPacket(data, CHAT_MSG_PARTY, LANG_UNIVERSAL, bot, bot, text);
                    group->BroadcastPacket(&data, false);
                }
                else
                    bot->Say(text, language);   // nobody to tell, say it out loud instead
                break;

            case CHANNEL_GUILD:
                if (Guild* guild = sGuildMgr->GetGuildById(bot->GetGuildId()))
                    guild->BroadcastToGuild(bot->GetSession(), false, text, language);
                break;

            case CHANNEL_SAY:
            default:
                bot->Say(text, language);
                break;
        }
    }

    enum class Refusal
    {
        Spoke,
        Disabled,
        NotABot,
        NoListener,
        InGrace,
        OnCooldown,
        ChanceRoll,
        NoLine
    };

    uint32 ChanceFor(std::string const& trigger)
    {
        int32 chance = -1;

        if (trigger == TRIGGER_KILL_BOSS)
            chance = cfg.ChanceKillBoss;
        else if (trigger == TRIGGER_LEVEL_UP)
            chance = cfg.ChanceLevelUp;
        else if (trigger == TRIGGER_DEATH)
            chance = cfg.ChanceDeath;

        return chance < 0 ? cfg.Chance : std::min<uint32>(uint32(chance), 100);
    }

    // The whole gating chain, cheapest check first. `forced` is what the
    // .botlore test command uses: it skips the earshot and chance gates but
    // still respects the cooldown, so the throttle stays testable.
    Refusal Speak(Player* bot, std::string const& trigger, LoreContext const& context, bool forced = false,
                  std::string* spoken = nullptr)
    {
        if (!cfg.Enable)
            return Refusal::Disabled;

        if (!IsBot(bot))
            return Refusal::NotABot;

        if (!forced && (listeners.empty() || !HasListenerNearby(bot)))
            return Refusal::NoListener;

        BotLoreData* data = bot->CustomData.GetDefault<BotLoreData>(DATA_KEY);
        time_t const now = GameTime::GetGameTime().count();

        // Entering the world counts as a zone change, so without this a
        // restart would have 500 bots greeting their own login at once.
        if (!forced && data->graceUntil > now)
            return Refusal::InGrace;

        if (data->nextLine > now)
            return Refusal::OnCooldown;

        if (!forced && urand(0, 99) >= ChanceFor(trigger))
            return Refusal::ChanceRoll;

        LoreLine const* line = PickLine(trigger, bot, context, data->lastLineId);
        if (!line)
            return Refusal::NoLine;

        std::string const text = Substitute(line->text, bot, context);
        Emit(bot, *line, text);

        data->nextLine = now + cfg.CooldownSeconds;
        data->lastLineId = line->id;

        if (spoken)
            *spoken = text;

        LOG_DEBUG("module", "mod-botlore: {} ({}) said '{}' for trigger {}",
            bot->GetName(), bot->GetLevel(), text, trigger);

        return Refusal::Spoke;
    }

    // Fills in where the bot is standing; every trigger wants this.
    LoreContext ContextFor(Player* bot)
    {
        LoreContext context;
        bot->GetZoneAndAreaId(context.zoneId, context.areaId);
        context.personality = PersonalityFor(bot);
        return context;
    }

    char const* RefusalText(Refusal refusal)
    {
        switch (refusal)
        {
            case Refusal::Spoke:      return "spoke";
            case Refusal::Disabled:   return "the module is disabled";
            case Refusal::NotABot:    return "that character is not a bot";
            case Refusal::NoListener: return "no real player is within earshot";
            case Refusal::InGrace:    return "the bot only just logged in";
            case Refusal::OnCooldown: return "the bot is still on cooldown";
            case Refusal::ChanceRoll: return "the chance roll failed";
            case Refusal::NoLine:     return "no line matches that bot and place";
            default:                  return "unknown";
        }
    }
}

class BotLore_WorldScript : public WorldScript
{
public:
    BotLore_WorldScript() : WorldScript("BotLore_WorldScript",
        { WORLDHOOK_ON_AFTER_CONFIG_LOAD, WORLDHOOK_ON_STARTUP }) { }

    void OnAfterConfigLoad(bool reload) override
    {
        LoadConfig();

        // At startup the DBC stores are not up yet, so the table is read from
        // OnStartup instead; on a reload everything is already loaded.
        if (reload)
            LoadLines();
    }

    void OnStartup() override
    {
        LoadLines();
    }
};

class BotLore_PlayerScript : public PlayerScript
{
public:
    BotLore_PlayerScript() : PlayerScript("BotLore_PlayerScript",
        {
            PLAYERHOOK_ON_LOGIN,
            PLAYERHOOK_ON_LOGOUT,
            PLAYERHOOK_ON_UPDATE,
            PLAYERHOOK_ON_UPDATE_ZONE,
            PLAYERHOOK_ON_PLAYER_QUEST_ACCEPT,
            PLAYERHOOK_ON_PLAYER_COMPLETE_QUEST,
            PLAYERHOOK_ON_CREATURE_KILL,
            PLAYERHOOK_ON_PLAYER_KILLED_BY_CREATURE,
            PLAYERHOOK_ON_LEVEL_CHANGED,
            PLAYERHOOK_ON_LOOT_ITEM,
            PLAYERHOOK_ON_PLAYER_ENTER_COMBAT
        }) { }

    void OnPlayerLogin(Player* player) override
    {
        if (!IsBot(player))
        {
            listeners.insert(player->GetGUID());
            return;
        }

        // Stay quiet for a moment, and stagger the first line across the
        // population so 500 cooldowns do not expire in the same second.
        BotLoreData* data = player->CustomData.GetDefault<BotLoreData>(DATA_KEY);
        time_t const now = GameTime::GetGameTime().count();
        data->graceUntil = now + cfg.LoginGraceSeconds;
        data->nextLine = now + urand(0, std::max<uint32>(cfg.CooldownSeconds, 1));
    }

    void OnPlayerLogout(Player* player) override
    {
        listeners.erase(player->GetGUID());
    }

    void OnPlayerUpdateZone(Player* player, uint32 newZone, uint32 newArea) override
    {
        if (!cfg.ZoneEnter)
            return;

        LoreContext context;
        context.zoneId = newZone;
        context.areaId = newArea;
        context.personality = PersonalityFor(player);
        Speak(player, TRIGGER_ZONE_ENTER, context);
    }

    void OnPlayerQuestAccept(Player* player, Quest const* quest) override
    {
        if (!cfg.QuestAccept || !quest)
            return;

        LoreContext context = ContextFor(player);
        context.quest = quest->GetTitle();
        context.questId = quest->GetQuestId();
        Speak(player, TRIGGER_QUEST_ACCEPT, context);
    }

    void OnPlayerCompleteQuest(Player* player, Quest const* quest) override
    {
        if (!cfg.QuestComplete || !quest)
            return;

        LoreContext context = ContextFor(player);
        context.quest = quest->GetTitle();
        context.questId = quest->GetQuestId();
        Speak(player, TRIGGER_QUEST_COMPLETE, context);
    }

    void OnPlayerCreatureKill(Player* killer, Creature* killed) override
    {
        if (!killed)
            return;

        CreatureTemplate const* info = killed->GetCreatureTemplate();
        bool const notable = info && (info->rank == CREATURE_ELITE_ELITE || info->rank == CREATURE_ELITE_RAREELITE ||
                                      info->rank == CREATURE_ELITE_WORLDBOSS || info->rank == CREATURE_ELITE_RARE);

        if (notable ? !cfg.KillBoss : !cfg.Kill)
            return;

        LoreContext context = ContextFor(killer);
        context.creatureEntry = killed->GetEntry();
        context.target = killed->GetName();
        Speak(killer, notable ? TRIGGER_KILL_BOSS : TRIGGER_KILL, context);
    }

    void OnPlayerKilledByCreature(Creature* killer, Player* killed) override
    {
        if (!cfg.Death)
            return;

        LoreContext context = ContextFor(killed);
        if (killer)
        {
            context.creatureEntry = killer->GetEntry();
            context.target = killer->GetName();
        }

        Speak(killed, TRIGGER_DEATH, context);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        if (!cfg.LevelUp)
            return;

        Speak(player, TRIGGER_LEVEL_UP, ContextFor(player));
    }

    void OnPlayerLootItem(Player* player, Item* item, uint32 /*count*/, ObjectGuid /*lootGuid*/) override
    {
        if (!cfg.LootRare || !item)
            return;

        ItemTemplate const* proto = item->GetTemplate();
        if (!proto || proto->Quality < ITEM_QUALITY_RARE)
            return;

        LoreContext context = ContextFor(player);
        context.item = proto->Name1;
        context.itemId = proto->ItemId;
        context.itemClass = int32(proto->Class);
        context.itemSubClass = int32(proto->SubClass);
        Speak(player, TRIGGER_LOOT_RARE, context);
    }

    void OnPlayerEnterCombat(Player* player, Unit* enemy) override
    {
        if (!cfg.CombatStart)
            return;

        LoreContext context = ContextFor(player);
        if (enemy)
            context.target = enemy->GetName();

        Speak(player, TRIGGER_COMBAT_START, context);
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        if (!cfg.Enable || !cfg.Idle)
            return;

        BotLoreData* data = player->CustomData.Get<BotLoreData>(DATA_KEY);
        if (!data)
        {
            // Only bots ever get an idle timer, and only once someone could
            // hear them.
            if (!IsBot(player) || listeners.empty())
                return;

            player->CustomData.GetDefault<BotLoreData>(DATA_KEY)->idleTimer = cfg.IdleSeconds * IN_MILLISECONDS;
            return;
        }

        if (!data->idleTimer)
        {
            data->idleTimer = cfg.IdleSeconds * IN_MILLISECONDS;
            return;
        }

        if (data->idleTimer > diff)
        {
            data->idleTimer -= diff;
            return;
        }

        data->idleTimer = cfg.IdleSeconds * IN_MILLISECONDS;

        if (player->IsInWorld() && !player->IsInCombat())
            Speak(player, TRIGGER_IDLE, ContextFor(player));
    }
};

class BotLore_CommandScript : public CommandScript
{
public:
    BotLore_CommandScript() : CommandScript("BotLore_CommandScript") { }

    ChatCommandTable GetCommands() const override
    {
        static ChatCommandTable botLoreCommandTable =
        {
            { "reload", HandleBotLoreReloadCommand, SEC_ADMINISTRATOR, Console::Yes },
            { "list",   HandleBotLoreListCommand,   SEC_GAMEMASTER,    Console::Yes },
            { "test",   HandleBotLoreTestCommand,   SEC_GAMEMASTER,    Console::Yes }
        };

        static ChatCommandTable commandTable =
        {
            { "botlore", botLoreCommandTable }
        };

        return commandTable;
    }

    static bool HandleBotLoreReloadCommand(ChatHandler* handler)
    {
        uint32 const count = LoadLines();
        handler->PSendSysMessage("mod-botlore: reloaded {} line(s) across {} trigger(s).", count, lines.size());
        return true;
    }

    static bool HandleBotLoreListCommand(ChatHandler* handler, Optional<std::string> triggerArg)
    {
        if (lines.empty())
        {
            handler->PSendSysMessage("No lore lines are loaded.");
            return true;
        }

        uint32 shown = 0;
        for (auto const& [trigger, entries] : lines)
        {
            if (triggerArg && *triggerArg != trigger)
                continue;

            handler->PSendSysMessage("{} ({} lines):", trigger, uint32(entries.size()));
            for (LoreLine const& line : entries)
            {
                handler->PSendSysMessage("  zone {} area {} creature {} team {} level {}-{} ch {} w{}: {}",
                    line.zoneId, line.areaId, line.creatureEntry, line.teamId,
                    line.minLevel, line.maxLevel, line.channel, line.weight, line.text);
                ++shown;
            }
        }

        if (!shown)
            handler->PSendSysMessage("No lines for that trigger.");

        return true;
    }

    // Resolves and speaks a line for a named bot, printing the result. This is
    // how the pipeline is checked without a game client: it proves the filter
    // match, the weighted pick, the placeholder substitution and the emit,
    // and a second call proves the cooldown.
    // The third argument is whatever entry the trigger is about: an item for
    // loot_rare, a quest for the quest triggers, a creature for the kill
    // ones. Without it a forced test cannot reach any line filtered on item
    // class, quest id or creature entry - which is most of the corpus.
    static bool HandleBotLoreTestCommand(ChatHandler* handler, std::string botName,
                                         Optional<std::string> triggerArg,
                                         Optional<uint32> entryArg)
    {
        Player* bot = ObjectAccessor::FindPlayerByName(botName, true);
        if (!bot)
        {
            handler->SendErrorMessage("No character named '{}' is online.", botName);
            return false;
        }

        std::string const trigger = triggerArg ? *triggerArg : TRIGGER_ZONE_ENTER;

        LoreContext context = ContextFor(bot);

        handler->PSendSysMessage("{} is a {} - class {}, zone {}.",
            bot->GetName(), PersonalityName(context.personality), bot->getClass(), context.zoneId);

        context.target = "Something Wicked";
        context.quest = "A Test of Valour";
        context.item = "Test Trinket";

        if (entryArg)
        {
            uint32 const entry = *entryArg;

            if (trigger == TRIGGER_LOOT_RARE)
            {
                ItemTemplate const* proto = sObjectMgr->GetItemTemplate(entry);
                if (!proto)
                {
                    handler->SendErrorMessage("No item template {}.", entry);
                    return false;
                }

                context.itemId       = entry;
                context.itemClass    = int32(proto->Class);
                context.itemSubClass = int32(proto->SubClass);
                context.item         = proto->Name1;
                handler->PSendSysMessage("item {} '{}', class {}, subclass {}.",
                    entry, proto->Name1, proto->Class, proto->SubClass);
            }
            else if (trigger == TRIGGER_QUEST_ACCEPT || trigger == TRIGGER_QUEST_COMPLETE)
            {
                Quest const* quest = sObjectMgr->GetQuestTemplate(entry);
                if (!quest)
                {
                    handler->SendErrorMessage("No quest template {}.", entry);
                    return false;
                }

                context.questId = entry;
                context.quest   = quest->GetTitle();
                handler->PSendSysMessage("quest {} '{}'.", entry, quest->GetTitle());
            }
            else
            {
                CreatureTemplate const* creature = sObjectMgr->GetCreatureTemplate(entry);
                if (!creature)
                {
                    handler->SendErrorMessage("No creature template {}.", entry);
                    return false;
                }

                context.creatureEntry = entry;
                context.target        = creature->Name;
                handler->PSendSysMessage("creature {} '{}'.", entry, creature->Name);
            }
        }

        std::string spoken;
        Refusal const refusal = Speak(bot, trigger, context, true, &spoken);

        if (refusal != Refusal::Spoke)
        {
            handler->PSendSysMessage("{} stayed quiet: {}.", bot->GetName(), RefusalText(refusal));
            return true;
        }

        handler->PSendSysMessage("{} (level {}, zone {}, area {}) said:",
            bot->GetName(), bot->GetLevel(), AreaName(context.zoneId), AreaName(context.areaId));
        handler->PSendSysMessage("  {}", spoken);
        return true;
    }
};

void AddBotLoreScripts()
{
    new BotLore_WorldScript();
    new BotLore_PlayerScript();
    new BotLore_CommandScript();
}
