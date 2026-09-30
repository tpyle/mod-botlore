/*
 * Tests for mod-botlore's selection rules (src/BotLoreSelection.h).
 *
 * The corpus is ~12,000 lines across nineteen filter columns. A filter that
 * matches when it should not is invisible in play - a night elf saying a
 * dwarf's line reads as flavour, not as a bug - so these are the rules worth
 * pinning down.
 */

#include "BotLoreSelection.h"

#include <gtest/gtest.h>

using namespace BotLoreSelection;

namespace
{
    // A level 40 male Alliance human warrior who has spent talents in tree 1.
    Speaker Bot()
    {
        Speaker who;
        who.raceMask  = 1u << 0;    // human
        who.classMask = 1u << 0;    // warrior
        who.gender    = 0;          // male
        who.teamId    = 0;          // Alliance
        who.level     = 40;
        who.specTree  = 1;
        return who;
    }

    // CreatureTemplate::rank for an elite. Spelled out here so the tests do
    // not depend on the core's enum, which this header deliberately cannot see.
    constexpr std::int32_t RANK_ELITE_FOR_TEST = 1;

    Context InDuskwood()
    {
        Context ctx;
        ctx.zoneId = 10;
        ctx.areaId = 42;
        return ctx;
    }
}

// ------------------------------------------------------------------- Matches

TEST(BotLoreMatches, AnEmptyFilterMatchesEverybody)
{
    EXPECT_TRUE(Matches(Filter{}, Bot(), InDuskwood()));
}

TEST(BotLoreMatches, ZoneAndArea)
{
    Filter f;
    f.zoneId = 10;
    EXPECT_TRUE(Matches(f, Bot(), InDuskwood()));

    f.zoneId = 11;
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));

    Filter area;
    area.areaId = 42;
    EXPECT_TRUE(Matches(area, Bot(), InDuskwood()));
    area.areaId = 43;
    EXPECT_FALSE(Matches(area, Bot(), InDuskwood()));
}

TEST(BotLoreMatches, MasksAreTestedAsMasksNotAsEquality)
{
    Filter f;
    f.raceMask = (1u << 0) | (1u << 2);   // human or dwarf
    EXPECT_TRUE(Matches(f, Bot(), InDuskwood()));

    f.raceMask = (1u << 1) | (1u << 2);   // orc or dwarf
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

TEST(BotLoreMatches, LevelRangeIsInclusiveAndOptionalAtBothEnds)
{
    Filter f;
    f.minLevel = 40;
    f.maxLevel = 40;
    EXPECT_TRUE(Matches(f, Bot(), InDuskwood()));

    f.minLevel = 41;
    f.maxLevel = 0;                       // 0 means no upper bound
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));

    f.minLevel = 0;
    f.maxLevel = 39;
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

TEST(BotLoreMatches, GenderZeroIsMaleNotAbsent)
{
    // The trap in this whole table: gender 0 is a real value, so the "any"
    // sentinel has to be -1. A filter for males must not be read as "any".
    Filter male;
    male.gender = 0;
    EXPECT_TRUE(Matches(male, Bot(), InDuskwood()));

    Speaker she = Bot();
    she.gender = 1;
    EXPECT_FALSE(Matches(male, she, InDuskwood()));

    Filter any;                            // gender defaults to -1
    EXPECT_TRUE(Matches(any, she, InDuskwood()));
}

TEST(BotLoreMatches, TeamZeroIsAllianceNotAbsent)
{
    Filter alliance;
    alliance.teamId = 0;
    EXPECT_TRUE(Matches(alliance, Bot(), InDuskwood()));

    Speaker horde = Bot();
    horde.teamId = 1;
    EXPECT_FALSE(Matches(alliance, horde, InDuskwood()));
}

TEST(BotLoreMatches, ItemClassZeroIsWeaponsNotAbsent)
{
    Context looted = InDuskwood();
    looted.itemClass = 0;                  // ITEM_CLASS_CONSUMABLE
    looted.itemSubClass = 0;

    Filter consumables;
    consumables.itemClass = 0;
    EXPECT_TRUE(Matches(consumables, Bot(), looted));

    Context armour = InDuskwood();
    armour.itemClass = 4;
    EXPECT_FALSE(Matches(consumables, Bot(), armour));
}

TEST(BotLoreMatches, SpecLinesStaySilentUntilTheBotHasChosen)
{
    Filter fury;
    fury.specMask = 1u << 1;
    EXPECT_TRUE(Matches(fury, Bot(), InDuskwood()));

    // A fresh character: the core would report tree 0 with nothing spent, so
    // the module passes -1 instead and no spec line may match.
    Speaker fresh = Bot();
    fresh.specTree = -1;
    EXPECT_FALSE(Matches(fury, fresh, InDuskwood()));

    Filter arms;
    arms.specMask = 1u << 0;
    EXPECT_FALSE(Matches(arms, fresh, InDuskwood()));
}

TEST(BotLoreMatches, AnOutOfRangeSpecNeverMatches)
{
    Filter any;
    any.specMask = 0x7;
    Speaker odd = Bot();
    odd.specTree = 3;
    EXPECT_FALSE(Matches(any, odd, InDuskwood()));
}

TEST(BotLoreMatches, EveryDimensionMustAgree)
{
    Filter f;
    f.zoneId = 10;
    f.classMask = 1u << 0;
    f.minLevel = 30;
    EXPECT_TRUE(Matches(f, Bot(), InDuskwood()));

    f.creatureEntry = 448;                 // Hogger, who is not in this context
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

// --------------------------------------------------------------- Specificity

TEST(BotLoreSpecificity, GenericLinesScoreNothing)
{
    EXPECT_EQ(Specificity(Filter{}), 0u);
}

TEST(BotLoreSpecificity, NarrowerColumnsScoreHigher)
{
    Filter zone;   zone.zoneId = 10;
    Filter area;   area.areaId = 42;
    Filter quest;  quest.questId = 26;

    EXPECT_LT(Specificity(zone), Specificity(area));
    EXPECT_LT(Specificity(area), Specificity(quest));
}

TEST(BotLoreSpecificity, SubclassSupersedesClassRatherThanAddingToIt)
{
    Filter itemClass;
    itemClass.itemClass = 4;

    Filter itemSubClass;
    itemSubClass.itemClass = 4;
    itemSubClass.itemSubClass = 1;

    EXPECT_EQ(Specificity(itemClass), 1u);
    EXPECT_EQ(Specificity(itemSubClass), 2u);
}

TEST(BotLoreSpecificity, Accumulates)
{
    Filter f;
    f.zoneId = 10;        // 1
    f.areaId = 42;        // 2
    f.questId = 26;       // 3
    f.gender = 0;         // 1
    EXPECT_EQ(Specificity(f), 7u);
}

// ------------------------------------------------------------ creature rank

TEST(BotLoreMatches, NoRankRequirementMatchesAnything)
{
    Context ctx = InDuskwood();
    ctx.creatureRank = 3;                  // world boss
    EXPECT_TRUE(Matches(Filter{}, Bot(), ctx));

    ctx.creatureRank = -1;                 // no creature at all
    EXPECT_TRUE(Matches(Filter{}, Bot(), ctx));
}

TEST(BotLoreMatches, ARankLineNeedsThatRank)
{
    Filter f;
    f.creatureRank = RANK_ELITE_FOR_TEST;

    Context elite = InDuskwood();
    elite.creatureRank = RANK_ELITE_FOR_TEST;
    EXPECT_TRUE(Matches(f, Bot(), elite));

    Context trash = InDuskwood();
    trash.creatureRank = 0;
    EXPECT_FALSE(Matches(f, Bot(), trash));
}

// Rank 0 is a real rank - an ordinary creature - so it cannot double as the
// wildcard the masks use. A line asking for rank 0 must not fire on an elite,
// and must not fire when there is no creature at all.
TEST(BotLoreMatches, RankZeroIsOrdinaryNotWildcard)
{
    Filter f;
    f.creatureRank = 0;

    Context trash = InDuskwood();
    trash.creatureRank = 0;
    EXPECT_TRUE(Matches(f, Bot(), trash));

    Context elite = InDuskwood();
    elite.creatureRank = RANK_ELITE_FOR_TEST;
    EXPECT_FALSE(Matches(f, Bot(), elite));

    Context none = InDuskwood();           // creatureRank stays -1
    EXPECT_FALSE(Matches(f, Bot(), none));
}

// ----------------------------------------------------------- item quality

TEST(BotLoreMatches, NoQualityBoundsMatchAnyItem)
{
    Context ctx = InDuskwood();
    ctx.itemQuality = 4;
    EXPECT_TRUE(Matches(Filter{}, Bot(), ctx));
}

TEST(BotLoreMatches, MinQualityExcludesLesserItems)
{
    Filter epicOnly;
    epicOnly.minQuality = 4;

    Context epic = InDuskwood();
    epic.itemQuality = 4;
    EXPECT_TRUE(Matches(epicOnly, Bot(), epic));

    // Legendary is better than epic, so an epic-or-better line still fires.
    Context legendary = InDuskwood();
    legendary.itemQuality = 5;
    EXPECT_TRUE(Matches(epicOnly, Bot(), legendary));

    Context rare = InDuskwood();
    rare.itemQuality = 3;
    EXPECT_FALSE(Matches(epicOnly, Bot(), rare));
}

TEST(BotLoreMatches, MaxQualityKeepsARareLineOffEpics)
{
    Filter rareOnly;
    rareOnly.minQuality = 3;
    rareOnly.maxQuality = 3;

    Context rare = InDuskwood();
    rare.itemQuality = 3;
    EXPECT_TRUE(Matches(rareOnly, Bot(), rare));

    Context epic = InDuskwood();
    epic.itemQuality = 4;
    EXPECT_FALSE(Matches(rareOnly, Bot(), epic));
}

// A quality bound on a trigger that has no item (a kill, a zone change) must
// not match, rather than matching everything: itemQuality is 0 there.
TEST(BotLoreMatches, AQualityLineDoesNotFireWithoutAnItem)
{
    Filter f;
    f.minQuality = 2;
    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

// ------------------------------------------------------------- group state

TEST(BotLoreMatches, GroupAnyMatchesAloneAndGrouped)
{
    Context alone = InDuskwood();
    EXPECT_TRUE(Matches(Filter{}, Bot(), alone));

    Context grouped = InDuskwood();
    grouped.inGroup = true;
    EXPECT_TRUE(Matches(Filter{}, Bot(), grouped));
}

TEST(BotLoreMatches, AnAloneLineNeedsNoGroup)
{
    Filter f;
    f.groupState = GROUP_ALONE;

    EXPECT_TRUE(Matches(f, Bot(), InDuskwood()));

    Context grouped = InDuskwood();
    grouped.inGroup = true;
    EXPECT_FALSE(Matches(f, Bot(), grouped));
}

TEST(BotLoreMatches, AGroupedLineNeedsAGroupOfAnyKind)
{
    Filter f;
    f.groupState = GROUP_GROUPED;

    Context withBots = InDuskwood();
    withBots.inGroup = true;
    EXPECT_TRUE(Matches(f, Bot(), withBots));

    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

// "Stay close to me" is only worth saying where a person will read it, so the
// strictest group line needs a real player in the group, not just other bots.
TEST(BotLoreMatches, AWithPlayerLineNeedsARealPlayerInTheGroup)
{
    Filter f;
    f.groupState = GROUP_WITH_PLAYER;

    Context withPlayer = InDuskwood();
    withPlayer.inGroup = true;
    withPlayer.groupHasRealPlayer = true;
    EXPECT_TRUE(Matches(f, Bot(), withPlayer));

    Context botsOnly = InDuskwood();
    botsOnly.inGroup = true;
    EXPECT_FALSE(Matches(f, Bot(), botsOnly));

    EXPECT_FALSE(Matches(f, Bot(), InDuskwood()));
}

// ---------------------------------------------------- specificity additions

TEST(BotLoreSpecificity, TheNewFiltersEachCountOne)
{
    Filter rank;
    rank.creatureRank = RANK_ELITE_FOR_TEST;
    EXPECT_EQ(Specificity(rank), 1u);

    Filter quality;
    quality.minQuality = 4;
    EXPECT_EQ(Specificity(quality), 1u);

    // Both ends of the quality range are one filter, not two.
    quality.maxQuality = 4;
    EXPECT_EQ(Specificity(quality), 1u);

    Filter group;
    group.groupState = GROUP_WITH_PLAYER;
    EXPECT_EQ(Specificity(group), 1u);
}

// A named creature must stay more specific than its rank, so a Hogger line
// outweighs a generic elite line when Hogger is the one who died.
TEST(BotLoreSpecificity, ANamedCreatureOutweighsItsRank)
{
    Filter named;
    named.creatureEntry = 448;             // Hogger

    Filter anyElite;
    anyElite.creatureRank = RANK_ELITE_FOR_TEST;

    EXPECT_GT(Specificity(named), Specificity(anyElite));
}

// -------------------------------------------------------------------- Weight

TEST(BotLoreWeight, AGenericLineKeepsItsOwnWeight)
{
    EXPECT_EQ(WeightOf(1, Filter{}, 4), 1u);
    EXPECT_EQ(WeightOf(5, Filter{}, 4), 5u);
}

TEST(BotLoreWeight, SpecificityMultipliesRatherThanFilters)
{
    Filter quest;
    quest.questId = 26;                    // specificity 3

    // The whole corpus stays in the draw - that is the point - but a line
    // written for this quest is thirteen times likelier than a generic one.
    EXPECT_EQ(WeightOf(1, quest, 4), 13u);
    EXPECT_GT(WeightOf(1, quest, 4), WeightOf(1, Filter{}, 4));
}

TEST(BotLoreWeight, TurningTheDialToZeroIgnoresSpecificity)
{
    Filter quest;
    quest.questId = 26;
    EXPECT_EQ(WeightOf(1, quest, 0), 1u);
}

// ----------------------------------------------------------------- PickIndex

TEST(BotLorePick, WalksTheWeightsInOrder)
{
    std::vector<std::uint32_t> const weights = { 3, 1, 6 };

    EXPECT_EQ(PickIndex(weights, 0), 0u);
    EXPECT_EQ(PickIndex(weights, 2), 0u);   // last roll still in the first band
    EXPECT_EQ(PickIndex(weights, 3), 1u);   // first roll of the second
    EXPECT_EQ(PickIndex(weights, 4), 2u);
    EXPECT_EQ(PickIndex(weights, 9), 2u);   // last roll overall
}

TEST(BotLorePick, ZeroWeightEntriesAreNeverChosen)
{
    std::vector<std::uint32_t> const weights = { 0, 5 };

    EXPECT_EQ(PickIndex(weights, 0), 1u);
    EXPECT_EQ(PickIndex(weights, 4), 1u);
}

TEST(BotLorePick, ARollPastTheEndFallsBackToTheLastLine)
{
    std::vector<std::uint32_t> const weights = { 1, 1 };
    EXPECT_EQ(PickIndex(weights, 99), 1u);
}

TEST(BotLorePick, OneCandidateIsAlwaysThatCandidate)
{
    EXPECT_EQ(PickIndex({ 7 }, 0), 0u);
    EXPECT_EQ(PickIndex({ 7 }, 6), 0u);
}

// ---------------------------------------------------------------- Substitute

TEST(BotLoreSubstitute, ReplacesEveryOccurrence)
{
    EXPECT_EQ(Substitute("%zone, sweet %zone.", { { "%zone", "Duskwood" } }),
              "Duskwood, sweet Duskwood.");
}

TEST(BotLoreSubstitute, LeavesTextWithoutTokensAlone)
{
    EXPECT_EQ(Substitute("Nothing to see here.", { { "%zone", "Duskwood" } }),
              "Nothing to see here.");
}

TEST(BotLoreSubstitute, AnEmptyValueRemovesTheToken)
{
    // An unknown creature or an unnamed quest: better a gap than a literal
    // "%target" in a bot's mouth.
    EXPECT_EQ(Substitute("Killed %target!", { { "%target", "" } }), "Killed !");
}

TEST(BotLoreSubstitute, AppliesReplacementsInOrder)
{
    EXPECT_EQ(Substitute("%name of %zone", { { "%name", "Sasha" }, { "%zone", "Elwynn" } }),
              "Sasha of Elwynn");
}

TEST(BotLoreSubstitute, AValueContainingItsOwnTokenDoesNotLoopForever)
{
    // The rule that makes this safe: the search resumes after the inserted
    // value, not at it. A creature or zone named with a percent would
    // otherwise rewrite itself until the string ate the process.
    EXPECT_EQ(Substitute("hello %name", { { "%name", "%name the Bold" } }),
              "hello %name the Bold");
}

TEST(BotLoreSubstitute, AnEmptyTokenIsIgnoredRatherThanMatchingEverywhere)
{
    EXPECT_EQ(Substitute("unchanged", { { "", "x" } }), "unchanged");
}
