# Receiving Review Feedback

Feedback is a claim to evaluate, not an order to obey and not an occasion for flattery.

## Order of work

1. **Read** all of it before reacting.
2. **Understand**: restate each item in your own words. If any item is unclear, ask about
   the unclear items. Continue independent, understood fixes; defer dependent changes until
   their requirements are clear.
3. **Verify** each claim against the actual code and requirements.
4. **Evaluate**: is it correct for *this* codebase, stack and spec? Does it break anything?
   Is there a reason the code is the way it is? Is it YAGNI (grep for real usage before
   "implementing it properly")?
5. **Respond**: agree with a short technical reason, or push back with evidence.
6. **Implement** one item at a time, in the order blocking → simple → complex, running the
   relevant check after each.

## Push back when

- it breaks existing behavior or tests
- the reviewer lacks context (link the spec section, the test, or the commit that explains it)
- it contradicts a decision already recorded in spec.md / plan.md: point to it. Changing
  that decision is a NEEDS DECISION, not a review fix
- it is wrong for the platform or stack, or adds unused scope

## Tone

- No "You're absolutely right!", "Great catch!", or thanks rituals. Fix it, or explain why not.
- If you pushed back and were wrong: "Checked X, you're right. Fixed in <commit>." No long apology.
- When replying in a review tool, use the original comment thread.
