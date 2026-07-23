"""All tunable constants for tactics_game.

Phase 1 values are placeholders chosen to validate the *shape* of the
simulation, not balanced numbers. See docs/02_phase1_definition.md.
"""

# --- Hero synthesis (hidden affinity + starting attributes) ---
BASE_ATTRIBUTE_VALUE = 1
DIRICHLET_ALPHA = 1.0  # symmetric Dirichlet (uniform over the simplex)
SYNTHESIS_LEVEL_UPS = 5
POINTS_PER_LEVEL_UP = 3

# --- Derived HP ---
BASE_HP = 10
HP_ATTRIBUTE_MULTIPLIER = 2

# --- Track 1 progression (level & XP) ---
XP_LEVEL_THRESHOLD = 50
# Per-battle XP pool, awarded on victory: XP_POOL_PER_STRENGTH_POINT *
# progression.compute_enemy_strength(enemy_squad). Supersedes the old
# per-action accrual (docs/03_phase2a_definition.md section 5;
# docs/adr/0003-track1-per-battle-xp-and-downed-state.md).
XP_POOL_PER_STRENGTH_POINT = 25
# Bonus pool for benched heroes, as a fraction of the fielded pool. 0
# until a later meta-progression phase makes it upgradeable; plumbed now
# so the award function doesn't need touching twice (Phase 2a has no
# bench yet).
BENCH_XP_BONUS_MULTIPLIER = 0.0
# HP a downed hero (0 HP) revives to at battle end — "downed, not dead."
DOWNED_REVIVE_HP = 1
# Manual attribute allocation (docs/04_phase2b_definition.md section 5): of
# POINTS_PER_LEVEL_UP points, this many are chosen deterministically by the
# player instead of by affinity-weighted random draw. Fixed at 1 this phase
# (training facilities that raise it are out of scope). Design invariant:
# must always stay below POINTS_PER_LEVEL_UP — a hero can never reach full
# manual allocation, so growth always stays partly affinity-driven.
MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP = 1

# --- Track 2 progression (class XP, accrual only this phase) ---
CLASS_XP_PER_ABILITY_USE = 5

# --- Basic ability kit ---
# Per-ability data (range, cooldown, damage/heal scaling, etc.) lives in
# data/abilities.yaml — see engine/ability_library.py. Only the kit-shape
# invariant lives here, since it's enforced by Hero itself, not per-ability
# data.
ABILITY_SLOT_COUNT = 4

# --- Battle grid ---
GRID_WIDTH = 8
GRID_HEIGHT = 12
MOVEMENT_RANGE = 3

# --- Squad setup ---
# The player's full roster (Phase 2b) vs. how many of them can be fielded
# in a single battle. Battle combat itself never sees the roster — it only
# ever sees whichever subset was fielded — so nothing in engine/ may assume
# ROSTER_SIZE == FIELDED_SQUAD_SIZE even though the current values leave
# little room to actually bench anyone (docs/04_phase2b_definition.md
# section 1). Enemy squads are always generated at FIELDED_SQUAD_SIZE,
# independent of how many player heroes are actually fielded — fielding
# fewer than the max is an intended "fight outnumbered" choice, not a
# reduction in enemy count.
ROSTER_SIZE = 4
FIELDED_SQUAD_SIZE = 2

# --- Enemy AI decision-making ---
# Fraction of max HP below which an ally is considered in need of healing.
HEAL_TRIGGER_HP_FRACTION = 0.5
# Score bonus for an attack that would kill its target, so kills always
# outrank raw damage maximization when comparing candidate attacks.
AI_KILL_SCORE_BONUS = 10_000

# Safety cap on headless simulation steps, to guard against an
# unforeseen AI stalemate rather than a real game rule.
MAX_BATTLE_STEPS = 500

# --- Session chaining ---
SESSION_BATTLE_COUNT = 5
# Gradual recovery (docs/04_phase2b_definition.md section 3): between
# battles, every roster hero heals a fraction of their max HP, at a rate
# set by whether they were fielded or benched in the battle just fought.
# Benched heals substantially faster — sitting out is the mechanism by
# which a hero returns to full strength, including one revived at
# DOWNED_REVIVE_HP; there is no separate injury system. Both fractions are
# placeholders.
FIELDED_RECOVERY_FRACTION = 0.15
BENCHED_RECOVERY_FRACTION = 0.5

# --- Dev tooling ---
# Number of seeded battles captured by dev_tools' AI-vs-AI regression
# fixture (docs/03_phase2a_definition.md, build-order step 0).
AI_BASELINE_SEED_COUNT = 10

# --- Debug visualizer (pygame) ---
TILE_SIZE_PX = 48
SIDEBAR_WIDTH_PX = 340
AUTO_PLAY_INTERVAL_MS = 800
CARD_WIDTH_PX = 360
CARD_HEIGHT_PX = 230
CARD_MARGIN_PX = 16
CARD_VIEW_COLUMNS = 2
MESSAGE_BAR_HEIGHT_PX = 90  # full-width strip below the grid for event text
# Between-battle screen (docs/04_phase2b_definition.md section 6): one row
# per roster hero, sized to its own content like the card view.
BETWEEN_BATTLE_WIDTH_PX = 760
BETWEEN_BATTLE_ROW_HEIGHT_PX = 140
BETWEEN_BATTLE_MARGIN_PX = 16
BETWEEN_BATTLE_TOP_PX = 70  # room for the status/instruction line(s)
