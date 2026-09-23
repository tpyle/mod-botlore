/*
 * mod-botlore - choosing which line a bot says.
 *
 * The corpus is ~12,000 lines with fifteen filter columns, and the selection
 * rules are the part of this module that can go wrong without anyone
 * noticing: a filter that matches when it should not just means a night elf
 * saying a dwarf's line, which nobody reports as a bug. So the rules live
 * here, as functions over plain numbers and strings, and are tested (tests/).
 *
 * The module keeps everything that needs a world - reading the row, finding
 * the bot's spec, looking up a zone name - and calls into this header with
 * the results.
 *
 * Standard library only, so tests/ builds without AzerothCore.
 */

#ifndef MOD_BOTLORE_SELECTION_H
#define MOD_BOTLORE_SELECTION_H

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace BotLoreSelection
{
    using u8  = std::uint8_t;
    using i8  = std::int8_t;
    using u32 = std::uint32_t;
    using i32 = std::int32_t;

    // The filter columns of one bot_lore_text row. Zero (or -1 for the signed
    // ones) always means "any", so a generic line is a row of defaults.
    struct Filter
    {
        u32 zoneId          = 0;
        u32 areaId          = 0;
        u32 creatureEntry   = 0;
        u32 raceMask        = 0;
        u32 classMask       = 0;
        u32 personalityMask = 0;
        u32 questId         = 0;
        u32 itemId          = 0;
        i32 itemClass       = -1;
        i32 itemSubClass    = -1;
        i8  gender          = -1;
        u32 specMask        = 0;
        i8  teamId          = -1;
        u8  minLevel        = 0;
        u8  maxLevel        = 0;
    };

    // The bot itself.
    struct Speaker
    {
        u32 raceMask  = 0;
        u32 classMask = 0;
        i8  gender    = -1;
        i8  teamId    = -1;
        u8  level     = 1;

        // Talent tree with the most points spent, or -1 for "has not chosen".
        // The core's GetMostPointsTalentTree returns 0 when nothing is spent,
        // which would make every fresh character read as Arms, Holy, Beast
        // Mastery and so on - so the module passes -1 when the talent map is
        // empty and spec lines stay silent until the bot has actually picked.
        i32 specTree  = -1;
    };

    // What is happening, and to whom.
    struct Context
    {
        u32 zoneId        = 0;
        u32 areaId        = 0;
        u32 creatureEntry = 0;
        u32 questId       = 0;
        u32 itemId        = 0;
        u32 personality   = 0;
        i32 itemClass     = -1;
        i32 itemSubClass  = -1;
    };

    // How specific a line is. Used to weight the draw, not to filter it.
    inline u32 Specificity(Filter const& f)
    {
        u32 score = 0;
        if (f.zoneId)
            score += 1;
        if (f.areaId)
            score += 2;
        if (f.creatureEntry)
            score += 2;
        if (f.questId)
            score += 3;
        if (f.itemId)
            score += 3;
        if (f.itemSubClass >= 0)
            score += 2;
        else if (f.itemClass >= 0)
            score += 1;
        if (f.gender >= 0)
            score += 1;
        if (f.specMask)
            score += 1;
        if (f.classMask)
            score += 1;
        if (f.personalityMask)
            score += 1;
        return score;
    }

    inline bool Matches(Filter const& f, Speaker const& who, Context const& ctx)
    {
        if (f.zoneId && f.zoneId != ctx.zoneId)
            return false;
        if (f.areaId && f.areaId != ctx.areaId)
            return false;
        if (f.creatureEntry && f.creatureEntry != ctx.creatureEntry)
            return false;
        if (f.raceMask && !(f.raceMask & who.raceMask))
            return false;
        if (f.classMask && !(f.classMask & who.classMask))
            return false;
        if (f.personalityMask && !(f.personalityMask & ctx.personality))
            return false;
        if (f.questId && f.questId != ctx.questId)
            return false;
        if (f.itemId && f.itemId != ctx.itemId)
            return false;
        if (f.itemClass >= 0 && f.itemClass != ctx.itemClass)
            return false;
        if (f.itemSubClass >= 0 && f.itemSubClass != ctx.itemSubClass)
            return false;
        if (f.gender >= 0 && f.gender != who.gender)
            return false;
        if (f.specMask)
        {
            if (who.specTree < 0 || who.specTree > 2)
                return false;
            if (!(f.specMask & (1u << who.specTree)))
                return false;
        }
        if (f.teamId >= 0 && f.teamId != who.teamId)
            return false;
        if (f.minLevel && who.level < f.minLevel)
            return false;
        if (f.maxLevel && who.level > f.maxLevel)
            return false;

        return true;
    }

    // Specificity multiplies the row's own weight rather than filtering.
    //
    // It used to be a hard filter - keep the most specific matches, discard
    // the rest - and that made the pool in any one situation tiny: standing
    // in Duskwood, the handful of Duskwood lines were the only candidates and
    // several hundred archetype and generic lines could never be heard. As a
    // multiplier a line written for one quest still overwhelmingly wins, but
    // the whole matching corpus stays in the draw, which is what stops a long
    // session repeating itself.
    inline u32 WeightOf(u8 weight, Filter const& f, u32 specificityWeight)
    {
        return u32(weight) * (1 + Specificity(f) * specificityWeight);
    }

    // Walks a weighted list. roll is expected in [0, total). Returns the last
    // index if the roll is out of range, which is what the caller's urand
    // could only produce through a rounding mistake.
    inline std::size_t PickIndex(std::vector<u32> const& weights, u32 roll)
    {
        for (std::size_t i = 0; i < weights.size(); ++i)
        {
            if (roll < weights[i])
                return i;

            roll -= weights[i];
        }

        return weights.empty() ? 0 : weights.size() - 1;
    }

    // Replaces each %token with its value, every occurrence, left to right.
    //
    // The search resumes *after* the inserted value rather than at it: a
    // value that itself contains the token (a creature called "%name", a
    // zone name a future patch spells with a percent) would otherwise be
    // rewritten forever.
    inline std::string Substitute(std::string text,
                                  std::vector<std::pair<std::string, std::string>> const& replacements)
    {
        for (auto const& [token, value] : replacements)
        {
            if (token.empty())
                continue;

            for (std::size_t at = text.find(token); at != std::string::npos; at = text.find(token, at))
            {
                text.replace(at, token.size(), value);
                at += value.size();
            }
        }

        return text;
    }
}

#endif // MOD_BOTLORE_SELECTION_H
