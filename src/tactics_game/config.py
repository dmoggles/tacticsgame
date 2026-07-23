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
SQUAD_SIZE = 2

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
# Between-battle HP restoration. True = full heal (Phase 2a placeholder).
# TODO(phase2b): replace with gradual recovery from downed state; full
# heal exists only so Phase 2a doesn't produce a death spiral without a
# bench to rotate injured heroes out.
FULL_HEAL_BETWEEN_BATTLES = True

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
