/*!
 * VOID CHRONOS — Obsidian Play
 * Pure math / RNG game engine (backend logic only — no rendering, no DOM, no CSS).
 * Extracted 1:1 from the playable prototype (index.html) and mirrors slot_engine.py.
 *
 * Works as an ES module, a CommonJS module, or a plain <script> (attaches to
 * globalThis.VoidChronosEngine) — pick whichever `export` block at the bottom fits
 * the host environment and delete the others.
 */

/* =========================================================================================
   1) GRID / SYMBOL CONFIG
   ========================================================================================= */
const ROWS = 5, COLS = 5, GRID_CELLS = ROWS * COLS;
const MIN_WIN_COUNT = 8;

const LOW_SYMBOLS = ["S1", "S2", "S3", "S4"];
const HIGH_SYMBOLS = ["S5", "S6", "S7", "S8"];
const PAYING_SYMBOLS = LOW_SYMBOLS.concat(HIGH_SYMBOLS);
const WILD = "WILD", SCATTER = "SCAT", PORTAL = "PORTAL", COLLECTOR = "COLLECT", ORB = "ORB";

const SYMBOL_NAMES = {
  S1: "Crystal Hourglass", S2: "Teal Rune", S3: "Mystic Gem", S4: "Gold Coin",
  S5: "Void Heart", S6: "Star Rune", S7: "Chronos Gear", S8: "Obsidian Skull",
  WILD: "Void Wild", SCAT: "Chronos Scatter", PORTAL: "Portal Rift", COLLECT: "Void Collector", ORB: "Multiplier Orb"
};

/* --- paytable: cluster-size tiers x per-symbol value factor, calibrated for target RTP --- */
const TIER_CURVE = { 8: 0.04965, 10: 0.14893, 13: 0.49643, 17: 2.48215, 21: 16.54769 };
const VALUE_FACTOR = { S1: 1.0, S2: 1.4, S3: 2.0, S4: 2.8, S5: 5.0, S6: 8.0, S7: 13.0, S8: 20.0, WILD: 28.0, SCAT: 25.0 };
const PAYTABLE = {};
for (const sym in VALUE_FACTOR) {
  const f = VALUE_FACTOR[sym];
  PAYTABLE[sym] = Object.keys(TIER_CURVE).map(Number).sort((a, b) => b - a).map(t => [t, TIER_CURVE[t] * f]);
}

/* --- multiplier orb value ladder --- */
const ORB_VALUES = [2, 5, 10, 25, 50, 100, 500, 1000];
const ORB_WEIGHTS = [300, 240, 170, 110, 65, 30, 8, 2];

/* --- reel-symbol weights (base game vs free spins) --- */
const BASE_WEIGHTS = { S1: 170, S2: 155, S3: 139, S4: 124, S5: 109, S6: 93, S7: 78, S8: 62, WILD: 35, SCAT: 15, PORTAL: 20 };
const FREE_SPIN_WEIGHTS = { S1: 172, S2: 155, S3: 139, S4: 123, S5: 108, S6: 92, S7: 76, S8: 59, WILD: 40, SCAT: 5, PORTAL: 25, ORB: 12, COLLECT: 3 };

/* --- free spins triggering / retriggering --- */
const NATURAL_FS_TABLE = { 4: 10, 5: 12 };
const RETRIGGER_SCATTER_THRESHOLD = 3;
const RETRIGGER_SPINS = 5;
const MAX_WIN_MULT = 20000;
// caps the accumulating Global Multiplier itself, so orb collection can't spiral
// into implausible five-figure numbers on a spin that pays $0
const MAX_GLOBAL_MULT = 2000;
const MAX_CASCADE_STEPS = 40;

/* --- the 6 bet modes: Normal, Ante Bet, and the 4 direct bonus-buy modes --- */
const MODES = {
  NORMAL: {
    costMultiplier: 1, scatterWeightMult: 1, forcesFreeSpins: false,
    label: "Normal", desc: "Juego base estándar."
  },
  ANTE_BET: {
    costMultiplier: 3, scatterWeightMult: 3, forcesFreeSpins: false,
    label: "Ante Bet", desc: "Triplica la probabilidad de 4+ scatters."
  },
  SURGE: {
    costMultiplier: 50, forcesFreeSpins: true, fsCount: 8, minOrb: 5, startGlobalMult: 1,
    label: "Surge", desc: "8 Free Spins. Orbes mínimos 5x."
  },
  STANDARD_BONUS: {
    costMultiplier: 100, forcesFreeSpins: true, fsCount: 10, minOrb: null, startGlobalMult: 1,
    label: "Standard Bonus", desc: "10 Free Spins garantizados."
  },
  VOID_GATES: {
    costMultiplier: 500, forcesFreeSpins: true, fsCount: 10, minOrb: 10, startGlobalMult: 1,
    guaranteedOrbs: { countRange: [1, 2], forcedValues: [], poolMin: 10 },
    label: "Void Gates", desc: "10 Free Spins. Orbes mínimos 10x, con orbe garantizado."
  },
  CHRONOS_STORM: {
    costMultiplier: 1000, forcesFreeSpins: true, fsCount: 12, minOrb: null, startGlobalMult: 50,
    guaranteedOrbs: { countRange: [3, 5], forcedValues: [500, 1000], poolMin: 50 },
    label: "Chronos Storm", desc: "12 Free Spins. Multiplicador Global inicia en 50x. 3-5 orbes de alto valor garantizados cada spin (incluye 500x y 1000x)."
  }
};

const BET_STEPS = [0.20, 0.40, 0.60, 1.00, 2.00, 3.00, 5.00, 10, 20, 50, 100, 250];

/* =========================================================================================
   2) RNG / MATH ENGINE
   ========================================================================================= */
function idx(r, c) { return r * COLS + c; }
function rcOf(i) { return [Math.floor(i / COLS), i % COLS]; }
function neighborsOf(i) {
  const [r, c] = rcOf(i); const out = [];
  [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(([dr, dc]) => {
    const rr = r + dr, cc = c + dc;
    if (rr >= 0 && rr < ROWS && cc >= 0 && cc < COLS) out.push(idx(rr, cc));
  });
  return out;
}

function weightedPick(weights) {
  const keys = Object.keys(weights);
  let total = 0; for (const k of keys) total += weights[k];
  let r = Math.random() * total;
  for (const k of keys) { if (r < weights[k]) return k; r -= weights[k]; }
  return keys[keys.length - 1];
}

function rollOrbValue(minOrb) {
  let vals = ORB_VALUES, wts = ORB_WEIGHTS;
  if (minOrb != null) {
    const pairs = vals.map((v, i) => [v, wts[i]]).filter(p => p[0] >= minOrb);
    if (pairs.length) { vals = pairs.map(p => p[0]); wts = pairs.map(p => p[1]); }
  }
  let total = 0; for (const w of wts) total += w;
  let r = Math.random() * total;
  for (let i = 0; i < vals.length; i++) { if (r < wts[i]) return vals[i]; r -= wts[i]; }
  return vals[vals.length - 1];
}

function payMultiplier(sym, count) {
  const tiers = PAYTABLE[sym]; if (!tiers) return 0;
  for (const [c, m] of tiers) { if (count >= c) return m; }
  return 0;
}

function shuffleArr(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[a[i], a[j]] = [a[j], a[i]]; } return a; }
function sampleIndices(n, count) { const pool = [...Array(n).keys()]; shuffleArr(pool); return pool.slice(0, count); }

function newCell(symbol) { return symbol === ORB ? { symbol: ORB, value: null } : { symbol, value: null }; }

function generateGrid(weights, minOrb, guaranteedOrbs) {
  const grid = [];
  for (let i = 0; i < GRID_CELLS; i++) {
    const sym = weightedPick(weights);
    if (sym === ORB) grid.push({ symbol: ORB, value: rollOrbValue(minOrb) });
    else grid.push({ symbol: sym, value: null });
  }
  if (guaranteedOrbs) {
    const [lo, hi] = guaranteedOrbs.countRange;
    const count = lo + Math.floor(Math.random() * (hi - lo + 1));
    const positions = sampleIndices(GRID_CELLS, count);
    const forced = guaranteedOrbs.forcedValues || [];
    const values = [];
    for (let i = 0; i < count; i++) {
      if (i < forced.length) values.push(forced[i]);
      else values.push(rollOrbValue(guaranteedOrbs.poolMin));
    }
    shuffleArr(values);
    positions.forEach((pos, i) => { grid[pos] = { symbol: ORB, value: values[i] }; });
  }
  return grid;
}

/* portal rift tiles convert themselves + 1-3 random orthogonal neighbours into Wilds */
function applyPortalWilds(grid) {
  const events = [];
  const portalPositions = [];
  grid.forEach((c, i) => { if (c && c.symbol === PORTAL) portalPositions.push(i); });
  for (const p of portalPositions) {
    const candidates = neighborsOf(p).filter(n => grid[n] && ![SCATTER, PORTAL, COLLECTOR, ORB, WILD].includes(grid[n].symbol));
    shuffleArr(candidates);
    const extra = 1 + Math.floor(Math.random() * Math.min(3, Math.max(1, candidates.length)));
    const chosen = candidates.slice(0, extra);
    const converted = [p, ...chosen];
    converted.forEach(pos => { grid[pos] = { symbol: WILD, value: null }; });
    events.push({ portalPosition: p, convertedPositions: converted });
  }
  return events;
}

/* cluster (scatter-pays) win evaluation: count of a symbol anywhere on the grid + Wilds */
function evaluateWins(grid) {
  const wildPositions = [];
  grid.forEach((c, i) => { if (c && c.symbol === WILD) wildPositions.push(i); });
  const wins = []; const allPositions = new Set();

  for (const sym of PAYING_SYMBOLS) {
    const positions = [];
    grid.forEach((c, i) => { if (c && c.symbol === sym) positions.push(i); });
    const total = positions.length + wildPositions.length;
    if (total < MIN_WIN_COUNT) continue;
    const mult = payMultiplier(sym, total);
    if (mult <= 0) continue;
    const posSet = Array.from(new Set(positions.concat(wildPositions))).sort((a, b) => a - b);
    wins.push({ symbol: sym, count: total, positions: posSet, payBase: mult });
    posSet.forEach(p => allPositions.add(p));
  }
  if (wildPositions.length >= MIN_WIN_COUNT) {
    const mult = payMultiplier(WILD, wildPositions.length);
    if (mult > 0) {
      const posSet = [...wildPositions].sort((a, b) => a - b);
      wins.push({ symbol: WILD, count: wildPositions.length, positions: posSet, payBase: mult });
      posSet.forEach(p => allPositions.add(p));
    }
  }
  const scatPositions = [];
  grid.forEach((c, i) => { if (c && c.symbol === SCATTER) scatPositions.push(i); });
  if (scatPositions.length >= MIN_WIN_COUNT) {
    const mult = payMultiplier(SCATTER, scatPositions.length);
    if (mult > 0) {
      wins.push({ symbol: SCATTER, count: scatPositions.length, positions: scatPositions, payBase: mult });
      scatPositions.forEach(p => allPositions.add(p));
    }
  }
  return { wins, positions: Array.from(allPositions).sort((a, b) => a - b) };
}

/* Void Collector tiles harvest every Multiplier Orb on the board into the Global Multiplier */
function applyOrbCollector(grid) {
  const collectorPositions = [];
  grid.forEach((c, i) => { if (c && c.symbol === COLLECTOR) collectorPositions.push(i); });
  if (!collectorPositions.length) return null;
  const orbPositions = [];
  grid.forEach((c, i) => { if (c && c.symbol === ORB) orbPositions.push(i); });
  const orbValues = orbPositions.map(i => grid[i].value || 0);
  const collectedTotal = orbValues.reduce((a, b) => a + b, 0);
  return { collectorPositions, orbPositions, orbValues, collectedTotal, positions: collectorPositions.concat(orbPositions) };
}

/* remove winning positions, drop survivors, refill from the top of each column */
function tumble(grid, removePositions, weights, minOrb) {
  removePositions.forEach(p => { grid[p] = null; });
  const newPositions = [];
  for (let col = 0; col < COLS; col++) {
    const colCells = []; for (let r = 0; r < ROWS; r++) colCells.push(grid[idx(r, col)]);
    const surviving = colCells.filter(c => c !== null);
    const missing = ROWS - surviving.length;
    const fresh = [];
    for (let i = 0; i < missing; i++) {
      const sym = weightedPick(weights);
      if (sym === ORB) fresh.push({ symbol: ORB, value: rollOrbValue(minOrb) });
      else fresh.push({ symbol: sym, value: null });
    }
    const newCol = fresh.concat(surviving);
    for (let r = 0; r < ROWS; r++) {
      const cellIdx = idx(r, col);
      grid[cellIdx] = newCol[r];
      if (r < missing) newPositions.push(cellIdx);
    }
  }
  return newPositions;
}

function cloneGrid(grid) { return grid.map(c => c ? { symbol: c.symbol, value: c.value } : null); }

/* one full spin's cascade sequence: initial grid -> repeated tumble-and-refill until no new wins */
function resolveSpinSequence(opts) {
  const { weights, initialWeights, globalMultiplier, minOrb, guaranteedOrbs, inFreeSpins } = opts;
  const grid = generateGrid(initialWeights || weights, minOrb, inFreeSpins ? guaranteedOrbs : null);
  let scatterCount = grid.filter(c => c.symbol === SCATTER).length;
  let gm = globalMultiplier;
  const cascades = []; let spinWin = 0; let step = 0;

  while (true) {
    step++;
    if (step > MAX_CASCADE_STEPS) break;
    const gridBefore = cloneGrid(grid);
    const portalEvents = applyPortalWilds(grid);
    const { wins, positions: winPositions } = evaluateWins(grid);
    const winPayRaw = wins.reduce((s, w) => s + w.payBase, 0);
    const orbEvent = applyOrbCollector(grid);
    if (orbEvent) gm = Math.min(gm + orbEvent.collectedTotal, MAX_GLOBAL_MULT);
    const winPay = winPayRaw * gm;
    spinWin += winPay;
    wins.forEach(w => { w.pay = w.payBase * gm; });

    const removePositions = Array.from(new Set(winPositions.concat(orbEvent ? orbEvent.positions : []))).sort((a, b) => a - b);
    const cascadeEntry = {
      step, gridBefore, portalEvents, wins, orbEvent,
      globalMultiplierAfter: gm, removePositions, stepWin: winPay
    };

    if (!removePositions.length) {
      cascadeEntry.gridAfter = cloneGrid(grid);
      cascadeEntry.newSymbols = [];
      cascades.push(cascadeEntry);
      break;
    }

    const newSymbols = tumble(grid, removePositions, weights, minOrb);
    newSymbols.forEach(p => { if (grid[p].symbol === SCATTER) scatterCount++; });
    cascadeEntry.gridAfter = cloneGrid(grid);
    cascadeEntry.newSymbols = newSymbols;
    cascades.push(cascadeEntry);
  }

  return { initialGrid: cascades[0].gridBefore, cascades, scatterCount, spinWin, globalMultiplierEnd: gm };
}

/* plays out an entire free spins bonus, handling retriggers and the max-win cap */
function playFreeSpins(opts) {
  let { betAmount, fsCount, startGlobalMult, minOrb, guaranteedOrbs, runningTotal, capAmount } = opts;
  let gm = startGlobalMult, spinsRemaining = fsCount, spinsPlayed = 0, totalRetriggers = 0, totalFsWin = 0;
  const spinLog = [];
  while (spinsRemaining > 0) {
    if (runningTotal >= capAmount) break;
    spinsRemaining--; spinsPlayed++;
    const seq = resolveSpinSequence({ weights: FREE_SPIN_WEIGHTS, globalMultiplier: gm, minOrb, guaranteedOrbs, inFreeSpins: true });
    gm = seq.globalMultiplierEnd;
    const retrigger = seq.scatterCount >= RETRIGGER_SCATTER_THRESHOLD;
    if (retrigger) { spinsRemaining += RETRIGGER_SPINS; totalRetriggers++; }
    seq.spinIndex = spinsPlayed; seq.retrigger = retrigger; seq.spinsRemainingAfter = spinsRemaining;
    totalFsWin += seq.spinWin; runningTotal += seq.spinWin;
    spinLog.push(seq);
    if (runningTotal >= capAmount) break;
  }
  return {
    result: {
      initialSpinsAwarded: fsCount, spinsPlayed, retriggers: totalRetriggers,
      globalMultiplierStart: startGlobalMult, globalMultiplierFinal: gm,
      totalFreeSpinsWin: totalFsWin, spins: spinLog
    },
    runningTotal
  };
}

/**
 * Top-level RNG entrypoint: resolves one full round (base game, or a direct bonus-buy
 * round) for a given bet and mode, including any naturally-triggered or bought free
 * spins. Pure function of `betAmount`/`mode` plus Math.random() — no shared state,
 * no I/O, safe to call from a server per-round.
 */
function engineSpin(betAmount, mode) {
  const cfg = MODES[mode];
  if (!cfg) throw new Error(`Unknown mode "${mode}". Valid modes: ${Object.keys(MODES).join(", ")}`);
  const result = {
    game: "VOID CHRONOS", studio: "Obsidian Play", betAmount, mode,
    buyCost: betAmount * cfg.costMultiplier,
    baseGame: null, freeSpinsTriggered: false, freeSpins: null,
    totalWin: 0, totalWinMultiplier: 0, maxWinCapped: false
  };
  let runningTotal = 0;
  const capAmount = betAmount * MAX_WIN_MULT;

  if (cfg.forcesFreeSpins) {
    const { result: fsResult, runningTotal: rt } = playFreeSpins({
      betAmount, fsCount: cfg.fsCount, startGlobalMult: cfg.startGlobalMult || 1,
      minOrb: cfg.minOrb, guaranteedOrbs: cfg.guaranteedOrbs, runningTotal, capAmount
    });
    result.freeSpinsTriggered = true; result.freeSpins = fsResult; runningTotal = rt;
  } else {
    const initialWeights = Object.assign({}, BASE_WEIGHTS);
    const scatMult = cfg.scatterWeightMult || 1;
    if (scatMult !== 1) initialWeights.SCAT = initialWeights.SCAT * scatMult;

    const baseSeq = resolveSpinSequence({ weights: BASE_WEIGHTS, initialWeights, globalMultiplier: 1, minOrb: null, guaranteedOrbs: null, inFreeSpins: false });
    result.baseGame = baseSeq;
    runningTotal += baseSeq.spinWin;

    let fsAward = 0;
    if (baseSeq.scatterCount >= 5) fsAward = NATURAL_FS_TABLE[5];
    else if (baseSeq.scatterCount === 4) fsAward = NATURAL_FS_TABLE[4];

    if (fsAward > 0 && runningTotal < capAmount) {
      const { result: fsResult, runningTotal: rt } = playFreeSpins({
        betAmount, fsCount: fsAward, startGlobalMult: 1, minOrb: null, guaranteedOrbs: null, runningTotal, capAmount
      });
      result.freeSpinsTriggered = true; result.freeSpins = fsResult; runningTotal = rt;
    }
  }

  const capped = runningTotal >= capAmount;
  const finalTotal = Math.min(runningTotal, capAmount);
  result.totalWin = finalTotal;
  result.totalWinMultiplier = betAmount ? finalTotal / betAmount : 0;
  result.maxWinCapped = capped;
  return result;
}

/* =========================================================================================
   3) SESSION / BANKROLL CONTROLLER
   Optional convenience wrapper around engineSpin() that tracks balance and bet size —
   everything a UI needs to drive the math engine without touching RNG internals.
   Skip this class entirely if your host (e.g. a stake-engine RGS) manages balance itself;
   engineSpin() alone is enough.
   ========================================================================================= */
class VoidChronosEngine {
  constructor({ balance = 10000, betIndex = 3, mode = "NORMAL" } = {}) {
    this.balance = balance;
    this.betIndex = betIndex;
    this.mode = mode;
  }

  get bet() { return BET_STEPS[this.betIndex]; }

  setBetIndex(i) {
    if (i < 0 || i >= BET_STEPS.length) throw new RangeError(`betIndex out of range 0..${BET_STEPS.length - 1}`);
    this.betIndex = i;
    return this.bet;
  }

  setMode(mode) {
    if (!MODES[mode]) throw new Error(`Unknown mode "${mode}"`);
    this.mode = mode;
  }

  /** Cost to buy directly into `mode` at the current bet, without spinning. */
  buyCost(mode = this.mode) {
    return this.bet * MODES[mode].costMultiplier;
  }

  /**
   * Resolves one round: validates funds, deducts stake, runs engineSpin(), credits the
   * payout. Returns the full engineSpin() result (with `balanceAfter` attached), or
   * `null` if the balance can't cover the stake — mirrors the UI's
   * "insufficient funds" guard without any DOM/animation coupling.
   */
  spin(forceMode) {
    const mode = forceMode || this.mode;
    const cfg = MODES[mode];
    if (!cfg) throw new Error(`Unknown mode "${mode}"`);
    const cost = this.bet * cfg.costMultiplier;
    if (cost > this.balance) return null;

    this.balance -= cost;
    const result = engineSpin(this.bet, mode);
    this.balance += result.totalWin;
    result.balanceAfter = this.balance;
    return result;
  }

  /**
   * Runs up to `count` spins back-to-back (the same "N spins" behaviour as the UI's
   * Autobet control), stopping early if funds run out. `onSpinResult(result, i)` fires
   * synchronously after each spin if provided.
   */
  runAutobet(count, { forceMode, onSpinResult } = {}) {
    const results = [];
    for (let i = 0; i < count; i++) {
      const result = this.spin(forceMode);
      if (!result) break; // insufficient funds
      results.push(result);
      if (onSpinResult) onSpinResult(result, i);
    }
    return results;
  }
}

/* =========================================================================================
   4) EXPORTS — keep whichever block matches your environment
   ========================================================================================= */
const VoidChronosEngineModule = {
  // config
  ROWS, COLS, GRID_CELLS, MIN_WIN_COUNT,
  LOW_SYMBOLS, HIGH_SYMBOLS, PAYING_SYMBOLS, WILD, SCATTER, PORTAL, COLLECTOR, ORB,
  SYMBOL_NAMES, TIER_CURVE, VALUE_FACTOR, PAYTABLE,
  ORB_VALUES, ORB_WEIGHTS, BASE_WEIGHTS, FREE_SPIN_WEIGHTS,
  NATURAL_FS_TABLE, RETRIGGER_SCATTER_THRESHOLD, RETRIGGER_SPINS,
  MAX_WIN_MULT, MAX_GLOBAL_MULT, MAX_CASCADE_STEPS, MODES, BET_STEPS,
  // low-level RNG / math functions
  idx, rcOf, neighborsOf, weightedPick, rollOrbValue, payMultiplier,
  shuffleArr, sampleIndices, newCell, generateGrid, applyPortalWilds,
  evaluateWins, applyOrbCollector, tumble, cloneGrid,
  resolveSpinSequence, playFreeSpins, engineSpin,
  // session wrapper
  VoidChronosEngine
};

// CommonJS / Node
if (typeof module !== "undefined" && module.exports) {
  module.exports = VoidChronosEngineModule;
}
// Browser global
if (typeof window !== "undefined") {
  window.VoidChronosEngine = VoidChronosEngineModule;
}
