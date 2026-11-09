#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ターミナル将棋 — ターミナル上でPython製の将棋AIと対局するプログラム
（Windows / Ubuntu / macOS 対応、外部ライブラリ不要、Python 3.8以降）

  python shogi_cli.py                 # 先手で対局（中級）
  python shogi_cli.py --side gote     # 後手で対局
  python shogi_cli.py --level 3       # 強さ 1〜4
  python shogi_cli.py --time 8        # AIの持ち時間（1手あたり秒）
  python shogi_cli.py --watch         # AI同士の対局を観戦
  python shogi_cli.py --pvp           # 人間同士（1台で交互に入力）
"""
import argparse
import os
import random
import re
import sys
import time

# ─────────────────────────────────────────────
#  駒の定義
# ─────────────────────────────────────────────
FU, KY, KE, GI, KI, KA, HI, OU = 1, 2, 3, 4, 5, 6, 7, 8
TO, NY, NK, NG, UM, RY = 9, 10, 11, 12, 14, 15
PROMOTE = [0, 9, 10, 11, 12, 0, 14, 15, 0, 0, 0, 0, 0, 0, 0, 0]
BASE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 0, 6, 7]
VAL = [0, 100, 430, 450, 640, 690, 890, 1040, 0, 420, 630, 640, 670, 0, 1150, 1300]
HVAL = [0, 115, 480, 510, 720, 760, 1050, 1250, 0]

CH = ["", "歩", "香", "桂", "銀", "金", "角", "飛", "玉", "と", "杏", "圭", "全", "", "馬", "龍"]
NAME = ["", "歩", "香", "桂", "銀", "金", "角", "飛", "玉", "と", "成香", "成桂", "成銀", "", "馬", "龍"]
KAN = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
ZEN = ["１", "２", "３", "４", "５", "６", "７", "８", "９"]
USI_P = {1: "P", 2: "L", 3: "N", 4: "S", 5: "G", 6: "B", 7: "R"}
SFEN_P = {"P": 1, "L": 2, "N": 3, "S": 4, "G": 5, "B": 6, "R": 7, "K": 8}
SFEN_C = {1: "P", 2: "L", 3: "N", 4: "S", 5: "G", 6: "B", 7: "R", 8: "K"}
START_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"

# 盤のマス番号: sq = 段(0=一段目) * 9 + 列(0=９筋 … 8=１筋)
DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
GOLD = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0)]
ORTH = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
STEP0 = {FU: [(-1, 0)], KE: [(-2, -1), (-2, 1)],
         GI: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 1)],
         KI: GOLD, OU: DIRS8, TO: GOLD, NY: GOLD, NK: GOLD, NG: GOLD,
         UM: ORTH, RY: DIAG}
SLIDE0 = {KY: [(-1, 0)], KA: DIAG, HI: ORTH, UM: DIAG, RY: ORTH}


def _on(r, c):
    return 0 <= r < 9 and 0 <= c < 9


# 先手(si=0)/後手(si=1) ごとの利きテーブルを事前計算
STEPS = [[[[] for _ in range(81)] for _ in range(16)] for _ in range(2)]
RAYS = [[[[] for _ in range(81)] for _ in range(16)] for _ in range(2)]
STEPDIR = [[set() for _ in range(16)] for _ in range(2)]
SLIDEDIR = [[set() for _ in range(16)] for _ in range(2)]
for _si in range(2):
    _f = 1 if _si == 0 else -1
    for _t in range(16):
        st = [(dr * _f, dc) for dr, dc in STEP0.get(_t, [])]
        sl = [(dr * _f, dc) for dr, dc in SLIDE0.get(_t, [])]
        STEPDIR[_si][_t] = set(st)
        SLIDEDIR[_si][_t] = set(sl)
        for _sq in range(81):
            r, c = divmod(_sq, 9)
            STEPS[_si][_t][_sq] = [(r + dr) * 9 + c + dc for dr, dc in st if _on(r + dr, c + dc)]
            rays = []
            for dr, dc in sl:
                ray, rr, cc = [], r + dr, c + dc
                while _on(rr, cc):
                    ray.append(rr * 9 + cc)
                    rr += dr
                    cc += dc
                if ray:
                    rays.append(ray)
            RAYS[_si][_t][_sq] = rays

# 王手判定用: あるマスから方向kに見て、隣/遠方にいる駒がそのマスに利くか
RAY8 = [[[] for _ in range(8)] for _ in range(81)]
for _sq in range(81):
    r, c = divmod(_sq, 9)
    for k, (dr, dc) in enumerate(DIRS8):
        rr, cc = r + dr, c + dc
        while _on(rr, cc):
            RAY8[_sq][k].append(rr * 9 + cc)
            rr += dr
            cc += dc
ATK_ADJ = [[set() for _ in range(8)] for _ in range(2)]
ATK_FAR = [[set() for _ in range(8)] for _ in range(2)]
for _si in range(2):
    for k, (dr, dc) in enumerate(DIRS8):
        back = (-dr, -dc)
        for _t in range(1, 16):
            if back in STEPDIR[_si][_t] or back in SLIDEDIR[_si][_t]:
                ATK_ADJ[_si][k].add(_t)
            if back in SLIDEDIR[_si][_t]:
                ATK_FAR[_si][k].add(_t)
KN_SRC = [[[] for _ in range(81)] for _ in range(2)]
for _sq in range(81):
    r, c = divmod(_sq, 9)
    for _si, dr in ((0, 2), (1, -2)):
        for dc in (-1, 1):
            if _on(r + dr, c + dc):
                KN_SRC[_si][_sq].append((r + dr) * 9 + c + dc)

_rng = random.Random(20261026)
Z_P = [_rng.getrandbits(64) for _ in range(33 * 81)]
Z_H = [_rng.getrandbits(64) for _ in range(2 * 9 * 20)]
Z_SIDE = _rng.getrandbits(64)


# ─────────────────────────────────────────────
#  局面
# ─────────────────────────────────────────────
class Board:
    """指し手は (from, to, promote, drop_type) のタプル。打つ手は from = -1。"""

    def __init__(self):
        self.b = [0] * 81
        self.hand = [[0] * 9, [0] * 9]
        self.side = 1
        self.king = [-1, -1]
        self.hash = 0
        self.mat = 0
        self.stack = []

    # ---- 生成・変換 ----
    @staticmethod
    def from_sfen(sfen):
        p = Board()
        parts = sfen.split()
        rows = parts[0].split("/")
        if len(rows) != 9:
            raise ValueError("SFENの盤面は9段必要です")
        for r, row in enumerate(rows):
            c, promo = 0, False
            for ch in row:
                if ch == "+":
                    promo = True
                elif ch.isdigit():
                    c += int(ch)
                else:
                    t = SFEN_P[ch.upper()]
                    if promo:
                        t = PROMOTE[t]
                        promo = False
                    p.b[r * 9 + c] = t if ch.isupper() else -t
                    c += 1
            if c != 9:
                raise ValueError("SFENの段の長さが不正です")
        p.side = 1 if len(parts) < 2 or parts[1] == "b" else -1
        if len(parts) >= 3 and parts[2] != "-":
            n = ""
            for ch in parts[2]:
                if ch.isdigit():
                    n += ch
                else:
                    cnt = int(n) if n else 1
                    p.hand[0 if ch.isupper() else 1][SFEN_P[ch.upper()]] += cnt
                    n = ""
        p.recompute()
        return p

    def to_sfen(self, ply=1):
        rows = []
        for r in range(9):
            s, empty = "", 0
            for c in range(9):
                x = self.b[r * 9 + c]
                if not x:
                    empty += 1
                    continue
                if empty:
                    s += str(empty)
                    empty = 0
                t = abs(x)
                ch = ("+" + SFEN_C[BASE[t]]) if t > 8 else SFEN_C[t]
                s += ch if x > 0 else ch.lower()
            if empty:
                s += str(empty)
            rows.append(s)
        hand = ""
        for si in (0, 1):
            for t in (7, 6, 5, 4, 3, 2, 1):
                n = self.hand[si][t]
                if n:
                    ch = SFEN_C[t] if si == 0 else SFEN_C[t].lower()
                    hand += (str(n) if n > 1 else "") + ch
        return "%s %s %s %d" % ("/".join(rows), "b" if self.side > 0 else "w", hand or "-", ply)

    def recompute(self):
        self.hash, self.mat = 0, 0
        for sq, x in enumerate(self.b):
            if x:
                self.hash ^= Z_P[(x + 16) * 81 + sq]
                self.mat += VAL[x] if x > 0 else -VAL[-x]
                if x == OU:
                    self.king[0] = sq
                elif x == -OU:
                    self.king[1] = sq
        for si in (0, 1):
            for t in range(1, 8):
                n = self.hand[si][t]
                self.hash ^= Z_H[(si * 9 + t) * 20 + n]
                self.mat += (HVAL[t] * n) if si == 0 else -(HVAL[t] * n)
        if self.side < 0:
            self.hash ^= Z_SIDE

    def copy(self):
        p = Board()
        p.b = self.b[:]
        p.hand = [self.hand[0][:], self.hand[1][:]]
        p.side, p.king, p.hash, p.mat = self.side, self.king[:], self.hash, self.mat
        return p

    # ---- 指す・戻す ----
    def make(self, m):
        f, t, pr, d = m
        b, s = self.b, self.side
        si = 0 if s > 0 else 1
        H = self.hand[si]
        if f < 0:
            p = d * s
            b[t] = p
            n = H[d]
            self.hash ^= Z_P[(p + 16) * 81 + t] ^ Z_H[(si * 9 + d) * 20 + n] ^ Z_H[(si * 9 + d) * 20 + n - 1]
            H[d] = n - 1
            self.mat += s * (VAL[d] - HVAL[d])
            self.stack.append(0)
        else:
            p = b[f]
            cap = b[t]
            b[f] = 0
            self.hash ^= Z_P[(p + 16) * 81 + f]
            if cap:
                self.hash ^= Z_P[(cap + 16) * 81 + t]
                ac = cap if cap > 0 else -cap
                ct = BASE[ac]
                n = H[ct]
                self.hash ^= Z_H[(si * 9 + ct) * 20 + n] ^ Z_H[(si * 9 + ct) * 20 + n + 1]
                H[ct] = n + 1
                self.mat += s * (VAL[ac] + HVAL[ct])
            ap = p if p > 0 else -p
            if pr:
                np_ = PROMOTE[ap] * s
                self.mat += s * (VAL[PROMOTE[ap]] - VAL[ap])
            else:
                np_ = p
            b[t] = np_
            self.hash ^= Z_P[(np_ + 16) * 81 + t]
            if ap == OU:
                self.king[si] = t
            self.stack.append(cap)
        self.side = -s
        self.hash ^= Z_SIDE

    def unmake(self, m):
        cap = self.stack.pop()
        self.side = -self.side
        self.hash ^= Z_SIDE
        f, t, pr, d = m
        b, s = self.b, self.side
        si = 0 if s > 0 else 1
        H = self.hand[si]
        if f < 0:
            p = d * s
            b[t] = 0
            n = H[d]
            self.hash ^= Z_P[(p + 16) * 81 + t] ^ Z_H[(si * 9 + d) * 20 + n] ^ Z_H[(si * 9 + d) * 20 + n + 1]
            H[d] = n + 1
            self.mat -= s * (VAL[d] - HVAL[d])
        else:
            np_ = b[t]
            anp = np_ if np_ > 0 else -np_
            self.hash ^= Z_P[(np_ + 16) * 81 + t]
            if pr:
                op = BASE[anp] * s
                self.mat -= s * (VAL[anp] - VAL[BASE[anp]])
            else:
                op = np_
            b[f] = op
            self.hash ^= Z_P[(op + 16) * 81 + f]
            b[t] = cap
            if cap:
                self.hash ^= Z_P[(cap + 16) * 81 + t]
                ac = cap if cap > 0 else -cap
                ct = BASE[ac]
                n = H[ct]
                self.hash ^= Z_H[(si * 9 + ct) * 20 + n] ^ Z_H[(si * 9 + ct) * 20 + n - 1]
                H[ct] = n - 1
                self.mat -= s * (VAL[ac] + HVAL[ct])
            if (op if op > 0 else -op) == OU:
                self.king[si] = f

    # ---- 利き・王手 ----
    def attacked(self, sq, by):
        """マスsqに手番byの駒が利いているか"""
        if sq < 0:
            return False
        b = self.b
        bsi = 0 if by > 0 else 1
        adj, far = ATK_ADJ[bsi], ATK_FAR[bsi]
        rays = RAY8[sq]
        for k in range(8):
            ray = rays[k]
            if not ray:
                continue
            x = b[ray[0]]
            if x:
                if x * by > 0 and (x if x > 0 else -x) in adj[k]:
                    return True
                continue
            fk = far[k]
            for i in range(1, len(ray)):
                x = b[ray[i]]
                if x:
                    if x * by > 0 and (x if x > 0 else -x) in fk:
                        return True
                    break
        ke = KE * by
        for s2 in KN_SRC[bsi][sq]:
            if b[s2] == ke:
                return True
        return False

    def in_check(self):
        return self.attacked(self.king[0 if self.side > 0 else 1], -self.side)

    # ---- 指し手生成 ----
    def gen(self, captures_only=False, ai=False):
        """疑似合法手（自玉の王手放置チェック前）。ai=True のとき歩・角・飛の不成を省く。"""
        b, s = self.b, self.side
        si = 0 if s > 0 else 1
        out = []
        app = out.append
        ST, RY_ = STEPS[si], RAYS[si]
        for sq in range(81):
            p = b[sq] * s
            if p <= 0:
                continue
            fr = sq // 9
            prom = PROMOTE[p]
            for t in ST[p][sq]:
                x = b[t]
                if x * s > 0 or (captures_only and not x):
                    continue
                if prom:
                    self._add_promo(out, sq, t, p, fr, si, ai)
                else:
                    app((sq, t, 0, 0))
            for ray in RY_[p][sq]:
                for t in ray:
                    x = b[t]
                    if x * s > 0:
                        break
                    if not captures_only or x:
                        if prom:
                            self._add_promo(out, sq, t, p, fr, si, ai)
                        else:
                            app((sq, t, 0, 0))
                    if x:
                        break
        if not captures_only:
            H = self.hand[si]
            types = [t for t in (7, 6, 5, 4, 3, 2, 1) if H[t]]
            if types:
                fu = FU * s
                fu_cols = {sq % 9 for sq in range(81) if b[sq] == fu}
                empties = [sq for sq in range(81) if not b[sq]]
                for t in types:
                    for d in empties:
                        r = d // 9
                        rel = r if si == 0 else 8 - r
                        if t <= 2 and rel == 0:
                            continue
                        if t == 3 and rel <= 1:
                            continue
                        if t == 1 and (d % 9) in fu_cols:
                            continue
                        app((-1, d, 0, t))
        return out

    @staticmethod
    def _add_promo(out, f, t, p, fr, si, ai):
        tr = t // 9
        if (fr <= 2 or tr <= 2) if si == 0 else (fr >= 6 or tr >= 6):
            out.append((f, t, 1, 0))
            rel = tr if si == 0 else 8 - tr
            if (p == FU or p == KY) and rel == 0:
                return
            if p == KE and rel <= 1:
                return
            if ai and (p == FU or p == KA or p == HI):
                return
        out.append((f, t, 0, 0))

    def has_legal(self):
        si = 0 if self.side > 0 else 1
        for m in self.gen(False, True):
            self.make(m)
            ok = not self.attacked(self.king[si], self.side)
            self.unmake(m)
            if ok:
                return True
        return False

    def legal_after(self, m):
        """make(m) 直後に呼ぶ。王手放置と打ち歩詰めを判定。"""
        mover = -self.side
        msi = 0 if mover > 0 else 1
        if self.attacked(self.king[msi], self.side):
            return False
        if m[0] < 0 and m[3] == FU:
            ek = self.king[msi ^ 1]
            if ek == m[1] + (-9 if mover > 0 else 9) and not self.has_legal():
                return False
        return True

    def legal_moves(self):
        out = []
        for m in self.gen(False, False):
            self.make(m)
            if self.legal_after(m):
                out.append(m)
            self.unmake(m)
        return out

    # ---- 評価 ----
    def king_safety(self, si):
        b = self.b
        s = 1 if si == 0 else -1
        k = self.king[si]
        if k < 0:
            return 0
        kr, kc = divmod(k, 9)
        v = 0
        for dr in (-2, -1, 0, 1, 2):
            r = kr + dr
            if r < 0 or r > 8:
                continue
            for dc in (-2, -1, 0, 1, 2):
                c = kc + dc
                if c < 0 or c > 8 or (dr == 0 and dc == 0):
                    continue
                x = b[r * 9 + c]
                if not x:
                    continue
                near = -1 <= dr <= 1 and -1 <= dc <= 1
                t = x * s
                if t > 0:
                    if t == KI or t == GI or 9 <= t <= 12:
                        v += 30 if near else 14
                else:
                    et = -t
                    if et != OU:
                        v -= 42 if near else 18
                    if et in (RY, UM, HI, KA):
                        v -= 30 if near else 14
        rel = kr if si == 0 else 8 - kr
        v += 30 if rel >= 7 else (0 if rel == 6 else -(6 - rel) * 30)
        eh = self.hand[si ^ 1]
        v -= (eh[KI] + eh[GI]) * 10 + (eh[HI] + eh[KA]) * 14
        return v

    def evaluate(self):
        sc = self.mat + self.king_safety(0) - self.king_safety(1)
        return sc if self.side > 0 else -sc


# ─────────────────────────────────────────────
#  探索（反復深化 α-β）
# ─────────────────────────────────────────────
MATE = 100000
INF = 10 ** 9
EXACT, LOWER, UPPER = 0, 1, 2


class Timeout(Exception):
    pass


class Engine:
    def __init__(self):
        self.tt = {}

    def think(self, pos, limit, max_depth=64, noise=0, seen=None, on_iter=None):
        """戻り値: (指し手, 評価値[手番側から見た値, 指せる手が1つならNone], 読んだ深さ, 局面数)"""
        self.pos = pos.copy()
        self.t0 = time.time()
        self.deadline = self.t0 + limit
        self.nodes = 0
        self.noise = noise
        self.killers = [[None, None] for _ in range(130)]
        self.hist = {}
        self.seen = set(seen or ())
        self.seen.discard(pos.hash)
        if len(self.tt) > 1_500_000:
            self.tt.clear()
        root = self.pos.legal_moves()
        if not root:
            return None, -MATE, 0, 0
        if len(root) == 1:
            return root[0], None, 0, 0
        self._order(root, None, 0)
        best, best_sc, depth_done = root[0], 0, 0
        for d in range(1, max_depth + 1):
            self.iter_best = None
            try:
                sc, mv = self._root(d, root)
            except Timeout:
                if self.iter_best is not None:
                    best = self.iter_best
                break
            best, best_sc, depth_done = mv, sc, d
            root.remove(mv)
            root.insert(0, mv)
            if on_iter:
                on_iter(d, sc, self.nodes, time.time() - self.t0, mv)
            if abs(sc) >= MATE - 200:
                break
            if time.time() - self.t0 > limit * 0.45:
                break
        return best, best_sc, depth_done, self.nodes

    def _eval(self):
        v = self.pos.evaluate()
        if self.noise:
            v += random.randint(-self.noise, self.noise)
        return v

    def _order(self, moves, ttm, ply):
        b = self.pos.b
        k0, k1 = self.killers[ply] if ply < 130 else (None, None)
        hist = self.hist

        def key(m):
            if m == ttm:
                return 100_000_000
            f, t, pr, d = m
            cap = b[t]
            if cap:
                att = VAL[abs(b[f])] if f >= 0 else 0
                return 1_000_000 + VAL[abs(cap)] * 16 - att + pr * 1000
            if pr:
                return 900_000
            if m == k0:
                return 800_000
            if m == k1:
                return 700_000
            return hist.get(m, 0)

        moves.sort(key=key, reverse=True)

    def _root(self, depth, moves):
        pos = self.pos
        alpha, beta = -INF, INF
        best = None
        self.seen.add(pos.hash)
        for i, m in enumerate(moves):
            pos.make(m)
            if i == 0:
                sc = -self._ab(depth - 1, -beta, -alpha, 1)
            else:
                sc = -self._ab(depth - 1, -alpha - 1, -alpha, 1)
                if sc > alpha:
                    sc = -self._ab(depth - 1, -beta, -alpha, 1)
            pos.unmake(m)
            if sc > alpha:
                alpha, best = sc, m
                self.iter_best = m
        self.seen.discard(pos.hash)
        return alpha, best

    def _ab(self, depth, alpha, beta, ply):
        self.nodes += 1
        if not (self.nodes & 1023) and time.time() > self.deadline:
            raise Timeout
        pos = self.pos
        h = pos.hash
        if h in self.seen:
            return 0
        s = pos.side
        in_chk = pos.attacked(pos.king[0 if s > 0 else 1], -s)
        if depth <= 0:
            if not in_chk:
                return self._qs(alpha, beta, ply, 0)
            depth = 1
        if ply >= 120:
            return self._eval()
        ttm = None
        e = self.tt.get(h)
        if e:
            ed, es, ef, ttm = e
            if ed >= depth and (ef == EXACT or (ef == LOWER and es >= beta) or (ef == UPPER and es <= alpha)):
                return es
        moves = pos.gen(False, True)
        self._order(moves, ttm, ply)
        self.seen.add(h)
        b = pos.b
        best, bm, n, a0 = -INF, None, 0, alpha
        for m in moves:
            quiet = not m[2] and not b[m[1]]
            pos.make(m)
            if not pos.legal_after(m):
                pos.unmake(m)
                continue
            n += 1
            if n > 3 and depth >= 3 and quiet and not in_chk:
                sc = -self._ab(depth - 2, -alpha - 1, -alpha, ply + 1)
                if sc > alpha:
                    sc = -self._ab(depth - 1, -beta, -alpha, ply + 1)
            else:
                sc = -self._ab(depth - 1, -beta, -alpha, ply + 1)
            pos.unmake(m)
            if sc > best:
                best, bm = sc, m
            if sc > alpha:
                alpha = sc
                if alpha >= beta:
                    if quiet and ply < 130:
                        k = self.killers[ply]
                        if k[0] != m:
                            k[1], k[0] = k[0], m
                        self.hist[m] = self.hist.get(m, 0) + depth * depth
                    break
        self.seen.discard(h)
        if n == 0:
            return -MATE + ply
        flag = LOWER if best >= beta else (UPPER if best <= a0 else EXACT)
        self.tt[h] = (depth, best, flag, bm)
        return best

    def _qs(self, alpha, beta, ply, qd):
        self.nodes += 1
        if not (self.nodes & 1023) and time.time() > self.deadline:
            raise Timeout
        pos = self.pos
        stand = self._eval()
        if stand >= beta:
            return stand
        if stand > alpha:
            alpha = stand
        if qd >= 6:
            return stand
        moves = pos.gen(True, True)
        self._order(moves, None, min(ply, 129))
        b = pos.b
        for m in moves:
            cap = b[m[1]]
            if not m[2] and stand + VAL[abs(cap)] + 200 < alpha:
                continue
            pos.make(m)
            if not pos.legal_after(m):
                pos.unmake(m)
                continue
            sc = -self._qs(-beta, -alpha, ply + 1, qd + 1)
            pos.unmake(m)
            if sc > stand:
                stand = sc
            if sc > alpha:
                alpha = sc
                if alpha >= beta:
                    break
        return stand


# ─────────────────────────────────────────────
#  表記（棋譜・USI）
# ─────────────────────────────────────────────
def sq_of(file_, rank):
    return (rank - 1) * 9 + (9 - file_)


def file_rank(sq):
    r, c = divmod(sq, 9)
    return 9 - c, r + 1


def usi(m):
    f, t, pr, d = m
    tf, tr = file_rank(t)
    dest = "%d%s" % (tf, "abcdefghi"[tr - 1])
    if f < 0:
        return "%s*%s" % (USI_P[d], dest)
    ff, fr = file_rank(f)
    return "%d%s%s%s" % (ff, "abcdefghi"[fr - 1], dest, "+" if pr else "")


def move_names(pos, m, last_to):
    """(画面表示用 '▲７六歩(77)', KIF用 '７六歩(77)') を返す"""
    f, t, pr, d = m
    s = pos.side
    tf, tr = file_rank(t)
    ptype = d if f < 0 else abs(pos.b[f])
    name = NAME[ptype]
    if t == last_to:
        dest = "同" + ("　" if len(name) == 1 else "")
    else:
        dest = ZEN[tf - 1] + KAN[tr - 1]
    if f < 0:
        suf, frm = "打", ""
    else:
        suf = ""
        if pr:
            suf = "成"
        elif PROMOTE[ptype]:
            fr_ = f // 9
            r_ = t // 9
            if (fr_ <= 2 or r_ <= 2) if s > 0 else (fr_ >= 6 or r_ >= 6):
                suf = "不成"
        ff, frr = file_rank(f)
        frm = "(%d%d)" % (ff, frr)
    body = dest + name + suf
    return ("▲" if s > 0 else "△") + body + frm, body + frm


def kan_num(n):
    u = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    return u[n] if n < 10 else "十" + u[n - 10]


def hand_text(pos, si):
    items = []
    for t in (7, 6, 5, 4, 3, 2, 1):
        n = pos.hand[si][t]
        if n:
            items.append(NAME[t] + (kan_num(n) if n > 1 else ""))
    return "　".join(items) if items else "なし"


# ─────────────────────────────────────────────
#  入力の解釈
# ─────────────────────────────────────────────
_Z2H = str.maketrans("０１２３４５６７８９＋＊＝ａｂｃｄｅｆｇｈｉＰＬＮＳＧＢＲ",
                     "0123456789+*=abcdefghiPLNSGBR")
_KANR = {k: str(i + 1) for i, k in enumerate(KAN)}
_JP_PIECE = {"歩": 1, "香": 2, "桂": 3, "銀": 4, "金": 5, "角": 6, "飛": 7, "玉": 8, "王": 8,
             "と": 9, "成香": 10, "杏": 10, "成桂": 11, "圭": 11, "成銀": 12, "全": 12,
             "馬": 14, "龍": 15, "竜": 15}
_RE_USI = re.compile(r"^([1-9])([a-i])([1-9])([a-i])([+=]?)$")
_RE_NUM = re.compile(r"^([1-9])([1-9])([1-9])([1-9])([+=]?)$")
_RE_DROP = re.compile(r"^([PLNSGBRplnsgbr])\*([1-9])([a-i1-9])$")
_RE_JP = re.compile(r"^(同|[1-9][1-9])\s*(成香|成桂|成銀|[歩香桂銀金角飛玉王と杏圭全馬龍竜])(打|成|不成|生)?$")


def parse_move(text, pos, legal, last_to):
    """戻り値: (候補手リスト, エラーメッセージ)。候補が2つ（成/不成）なら呼び出し側で確認する。"""
    s = text.strip().translate(_Z2H).replace(" ", "").replace("　", "")
    m = _RE_USI.match(s) or _RE_NUM.match(s)
    if m:
        ff, fr, tf, tr, p = m.groups()
        conv = lambda x: int(x) if x.isdigit() else "abcdefghi".index(x) + 1
        f = sq_of(int(ff), conv(fr))
        t = sq_of(int(tf), conv(tr))
        pr_req = {"+": 1, "=": 0}.get(p)
        if pos.b[f] * pos.side <= 0:
            return [], "%s%d に動かせる自分の駒がありません。" % (ff, conv(fr))
        c = [x for x in legal if x[0] == f and x[1] == t]
        if not c:
            return [], "その駒はそこへ動けません（または王手を放置する手です）。"
        if pr_req is not None:
            c = [x for x in c if x[2] == pr_req]
            if not c:
                return [], "その手は成り／不成の指定どおりには指せません。"
        return c, None
    m = _RE_DROP.match(s)
    if m:
        pl, tf, tr = m.groups()
        d = SFEN_P[pl.upper()]
        r = int(tr) if tr.isdigit() else "abcdefghi".index(tr) + 1
        t = sq_of(int(tf), r)
        c = [x for x in legal if x[0] < 0 and x[3] == d and x[1] == t]
        if not c:
            if pos.hand[0 if pos.side > 0 else 1][d] == 0:
                return [], "持ち駒に%sがありません。" % NAME[d]
            return [], "そこには打てません（二歩・行き所のない駒・打ち歩詰め・王手放置など）。"
        return c, None
    s2 = s
    if len(s2) >= 2 and s2[1] in _KANR:
        s2 = s2[0] + _KANR[s2[1]] + s2[2:]
    m = _RE_JP.match(s2)
    if m:
        dest, pname, suf = m.groups()
        if dest == "同":
            if last_to < 0:
                return [], "「同」は直前の手がある時だけ使えます。"
            t = last_to
        else:
            t = sq_of(int(dest[0]), int(dest[1]))
        ptype = _JP_PIECE[pname]
        c = []
        for x in legal:
            if x[1] != t:
                continue
            xt = x[3] if x[0] < 0 else abs(pos.b[x[0]])
            if xt == ptype:
                c.append(x)
        drops = [x for x in c if x[0] < 0]
        board = [x for x in c if x[0] >= 0]
        if suf == "打":
            c = drops
        else:
            c = board if board else drops
        if suf == "成":
            c = [x for x in c if x[2] == 1]
        elif suf in ("不成", "生"):
            c = [x for x in c if x[2] == 0 and any(y[0] == x[0] and y[2] == 1 for y in board)]
        if not c:
            return [], "その手は指せません。"
        froms = sorted({x[0] for x in c})
        if len(froms) > 1:
            alts = []
            for f in froms:
                ff, fr = file_rank(f)
                tf, tr = file_rank(t)
                alts.append("%d%d%d%d" % (ff, fr, tf, tr))
            return [], "動ける%sが複数あります。%s のように元のマスも入力してください。" % (NAME[ptype], " / ".join(alts))
        return c, None
    return [], None


HELP = """
指し手の入力方法（どれでも可）
  76歩  ７六歩  同歩  55角打  22角成  23銀不成   … 日本語の棋譜表記
  7776  8822+  2324=                            … 移動元と移動先の数字4桁（+で成る / =で成らない）
  7g7f  8h2b+  P*5e                             … USI形式
  成れる手で指定がない場合は「成りますか？」と聞きます。

コマンド
  moves (m)   指せる手の一覧        hint     AIにおすすめを聞く
  undo  (u)   待った                kifu (k) 棋譜を表示
  board (b)   盤面を再表示          sfen     現在局面をSFENで表示
  save 名前   棋譜をKIF形式で保存   level N  AIの強さを変更 (1〜4)
  resign      投了                  quit (q) 終了
"""


# ─────────────────────────────────────────────
#  画面表示
# ─────────────────────────────────────────────
def enable_vt():
    """Windowsのコンソールで色や行の書き換え（ANSIエスケープ）を使えるようにする"""
    if os.name != "nt":
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mode)):
            return False
        return bool(k.SetConsoleMode(h, mode.value | 0x0004))
    except Exception:
        return False


class Screen:
    def __init__(self, color):
        self.color = color

    def c(self, code, text):
        return "\033[%sm%s\033[0m" % (code, text) if self.color else text

    def board(self, pos, last_to, flip, labels, times):
        out = []
        top_si, bot_si = (0, 1) if flip else (1, 0)
        mark = {0: "▲先手", 1: "△後手"}
        out.append("%s %s の持駒：%s" % (mark[top_si], labels[top_si], hand_text(pos, top_si)))
        files = list(range(9, 0, -1)) if not flip else list(range(1, 10))
        out.append("  " + " ".join(ZEN[f - 1] for f in files))
        out.append("+---------------------------+")
        for i in range(9):
            r = i if not flip else 8 - i
            row = "|"
            for j in range(9):
                c = j if not flip else 8 - j
                sq = r * 9 + c
                x = pos.b[sq]
                if not x:
                    cell = " ・"
                else:
                    t = abs(x)
                    ch = ("玉" if x > 0 else "王") if t == OU else CH[t]
                    cell = (" " if x > 0 else "v") + ch
                    code = []
                    if x < 0:
                        code.append("31")
                    if t > 8:
                        code.append("1")
                    if code:
                        cell = self.c(";".join(code), cell)
                if sq == last_to:
                    cell = self.c("7", cell)
                row += cell
            row += "|" + KAN[r]
            out.append(row)
        out.append("+---------------------------+")
        out.append("%s %s の持駒：%s" % (mark[bot_si], labels[bot_si], hand_text(pos, bot_si)))
        out.append("消費時間  ▲%s  △%s" % (fmt_time(times[1]), fmt_time(times[-1])))
        return "\n".join(out)


def fmt_time(sec):
    sec = int(sec)
    return "%d:%02d" % (sec // 60, sec % 60)


def eval_text(score_sente, viewer):
    """score_sente: 先手から見た評価値。viewer: 1/-1 誰から見た言葉にするか (0なら先手基準)"""
    if abs(score_sente) >= MATE - 500:
        who = "先手" if score_sente > 0 else "後手"
        return "%s勝ちを読み切り" % who
    v = score_sente * (viewer or 1)
    sign = "+" if v > 0 else ""
    if abs(v) < 150:
        note = "互角"
    elif viewer:
        note = "あなたが有利" if v > 0 else "AIが有利"
    else:
        note = "先手有利" if v > 0 else "後手有利"
    return "%s%d（%s）" % (sign, v, note)


# ─────────────────────────────────────────────
#  対局の進行
# ─────────────────────────────────────────────
LEVELS = {
    1: dict(limit=0.6, depth=2, noise=150, label="初級"),
    2: dict(limit=3.0, depth=64, noise=0, label="中級"),
    3: dict(limit=8.0, depth=64, noise=0, label="上級"),
    4: dict(limit=20.0, depth=64, noise=0, label="最上級"),
}


class Game:
    def __init__(self, args):
        self.args = args
        self.pos = Board.from_sfen(args.sfen or START_SFEN)
        self.start_sfen = args.sfen or START_SFEN
        self.engine = Engine()
        self.scr = Screen(args.color)
        self.level = args.level
        self.moves, self.records = [], []
        self.rep = {self.pos.hash: 1}
        self.last_to = -1
        self.times = {1: 0.0, -1: 0.0}
        self.result = None
        self.last_eval = None
        if args.watch:
            self.ctrl = {1: "ai", -1: "ai"}
        elif args.pvp:
            self.ctrl = {1: "human", -1: "human"}
        else:
            hs = args.human_side
            self.ctrl = {hs: "human", -hs: "ai"}
        self.human = args.human_side if not (args.watch or args.pvp) else 0
        self.flip = self.human == -1
        lab = {"ai": "AI", "human": "あなた"}
        if args.pvp:
            self.labels = {0: "先手", 1: "後手"}
        else:
            self.labels = {0: lab[self.ctrl[1]], 1: lab[self.ctrl[-1]]}

    # ---- 基本操作 ----
    def play(self, m, sec):
        disp, kif = move_names(self.pos, m, self.last_to)
        side = self.pos.side
        self.times[side] += sec
        self.pos.make(m)
        self.moves.append(m)
        self.records.append(dict(disp=disp, kif=kif, sec=sec, total=self.times[side]))
        self.last_to = m[1]
        n = self.rep.get(self.pos.hash, 0) + 1
        self.rep[self.pos.hash] = n
        if n >= 4:
            self.result = ("draw", "千日手")
        return disp

    def undo(self, plies):
        done = 0
        while plies > 0 and self.moves:
            h = self.pos.hash
            self.rep[h] -= 1
            if self.rep[h] <= 0:
                del self.rep[h]
            m = self.moves.pop()
            rec = self.records.pop()
            self.pos.unmake(m)
            self.times[self.pos.side] -= rec["sec"]
            plies -= 1
            done += 1
        self.last_to = self.moves[-1][1] if self.moves else -1
        self.result = None
        return done

    def label_of(self, side):
        return self.labels[0 if side > 0 else 1]

    def show(self):
        if self.args.clear and self.args.vt:
            sys.stdout.write("\033[2J\033[H")
        print()
        print(self.scr.board(self.pos, self.last_to, self.flip, self.labels, self.times))
        if self.records:
            print("直前の手：%s" % self.records[-1]["disp"])
        if self.last_eval is not None:
            print("評価値：%s" % eval_text(self.last_eval, self.human))

    # ---- AI ----
    def ai_think(self, limit=None, quiet=False):
        L = LEVELS[self.level]
        limit = limit or self.args.time or L["limit"]
        depth = L["depth"] if not self.args.time else 64
        noise = L["noise"] if not self.args.time else 0
        pos, last_to = self.pos, self.last_to
        live = sys.stdout.isatty() and self.args.vt

        def on_iter(d, sc, nodes, el, mv):
            if quiet or not live:
                return
            name = move_names(pos, mv, last_to)[0]
            sys.stdout.write("\r\033[K  考え中… 深さ%d  %s  評価値%+d  %s局面  %.1f秒" %
                             (d, name, sc * pos.side, format(nodes, ","), el))
            sys.stdout.flush()

        if not quiet:
            sys.stdout.write("  考え中…")
            sys.stdout.flush()
        t0 = time.time()
        mv, sc, depth_done, nodes = self.engine.think(
            pos, limit, depth, noise, seen=self.rep.keys(), on_iter=on_iter)
        el = time.time() - t0
        if not quiet:
            sys.stdout.write("\r\033[K" if live else "\n")
            sys.stdout.flush()
        return mv, (None if sc is None else sc * pos.side), depth_done, nodes, el

    # ---- 終局処理 ----
    def finish(self):
        kind, why = self.result
        print()
        if kind == "draw":
            print("━━ %s で引き分けです（%d手）━━" % (why, len(self.moves)))
        else:
            w = kind
            if self.human:
                msg = "あなたの勝ちです！" if w == self.human else "AIの勝ちです。"
            else:
                msg = "%sの勝ちです。" % ("先手" if w > 0 else "後手")
            print("━━ %s（%s・%d手）%s ━━" % (why, "先手" if w > 0 else "後手", len(self.moves), msg))
        self.print_kifu()
        if sys.stdin.isatty():
            try:
                name = input("棋譜を保存するファイル名（Enterで保存せず終了）> ").strip()
            except EOFError:
                name = ""
            if name:
                self.save(name)

    def print_kifu(self):
        if not self.records:
            print("（まだ指していません）")
            return
        line = []
        for i, r in enumerate(self.records):
            line.append("%3d %s" % (i + 1, r["disp"]))
            if len(line) == 4:
                print("   ".join(line))
                line = []
        if line:
            print("   ".join(line))

    def save(self, name):
        if not name.endswith(".kif"):
            name += ".kif"
        lines = ["# ---- ターミナル将棋 棋譜ファイル ----",
                 "開始日時：" + time.strftime("%Y/%m/%d %H:%M:%S"),
                 "手合割：平手" if self.start_sfen == START_SFEN else "手合割：その他",
                 "先手：" + self.labels[0], "後手：" + self.labels[1],
                 "手数----指手---------消費時間--"]
        for i, r in enumerate(self.records):
            s, tot = int(r["sec"]), int(r["total"])
            lines.append("%4d %-12s(%2d:%02d/%02d:%02d:%02d)" %
                         (i + 1, r["kif"], s // 60, s % 60, tot // 3600, tot // 60 % 60, tot % 60))
        if self.result:
            why = self.result[1]
            lines.append("%4d %s" % (len(self.records) + 1, {"投了": "投了", "千日手": "千日手"}.get(why, "詰み")))
        try:
            with open(name, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            print("棋譜を保存しました：%s" % os.path.abspath(name))
        except OSError as e:
            print("保存できませんでした：%s" % e)

    # ---- 人間の手番 ----
    def human_turn(self, legal):
        t0 = time.time()
        side = self.pos.side
        prompt = "%s %s %d手目 > " % ("▲" if side > 0 else "△", self.label_of(side), len(self.moves) + 1)
        while True:
            try:
                text = input(prompt).strip()
            except EOFError:
                print()
                return "quit"
            if not text:
                continue
            cmd, _, arg = text.partition(" ")
            low = cmd.lower()
            if low in ("q", "quit", "exit", "終了"):
                return "quit"
            if low in ("h", "help", "?", "ヘルプ"):
                print(HELP)
                continue
            if low in ("b", "board", "盤"):
                self.show()
                continue
            if low in ("k", "kifu", "棋譜"):
                self.print_kifu()
                continue
            if low == "sfen":
                print(self.pos.to_sfen(len(self.moves) + 1))
                continue
            if low in ("m", "moves", "手"):
                names = sorted(move_names(self.pos, x, self.last_to)[0][1:] for x in legal)
                print("指せる手（%d通り）" % len(names))
                for i in range(0, len(names), 6):
                    print("  " + "  ".join("%-10s" % n for n in names[i:i + 6]))
                continue
            if low in ("hint", "ヒント"):
                mv, sc, d, nodes, el = self.ai_think(limit=min(3.0, self.args.time or 3.0))
                name = move_names(self.pos, mv, self.last_to)[0]
                ev = "指せる手はこれだけです" if sc is None else "評価値 " + eval_text(sc, self.human)
                print("  ヒント：%s（%s）%s" % (name, usi(mv), ev))
                continue
            if low == "level":
                if arg.strip() in ("1", "2", "3", "4"):
                    self.level = int(arg)
                    self.args.time = None
                    print("AIの強さを %s にしました。" % LEVELS[self.level]["label"])
                else:
                    print("level 1〜4 で指定してください（1:初級 2:中級 3:上級 4:最上級）。")
                continue
            if low == "save":
                if arg.strip():
                    self.save(arg.strip())
                else:
                    print("save ファイル名 の形で入力してください。")
                continue
            if low in ("u", "undo", "待った"):
                n = 2 if (self.human and len(self.moves) >= 2 and self.ctrl[-side] == "ai") else 1
                if self.undo(n):
                    print("%d手戻しました。" % n)
                    return "undo"
                print("戻せる手がありません。")
                continue
            if low in ("resign", "投了"):
                return "resign"
            cands, err = parse_move(text, self.pos, legal, self.last_to)
            if err:
                print("  " + err)
                continue
            if not cands:
                print("  入力を読み取れませんでした。help で入力方法を表示します。")
                continue
            if len(cands) > 1:
                while True:
                    try:
                        a = input("  成りますか？ [y/n] > ").strip().lower()
                    except EOFError:
                        return "quit"
                    if a in ("y", "yes", "成", "成る", "1"):
                        m = [x for x in cands if x[2] == 1][0]
                        break
                    if a in ("n", "no", "不成", "成らない", "0"):
                        m = [x for x in cands if x[2] == 0][0]
                        break
            else:
                m = cands[0]
            return ("move", m, time.time() - t0)

    # ---- メインループ ----
    def run(self):
        print("━━ ターミナル将棋 ━━")
        if self.args.watch:
            print("AI同士の対局を観戦します（Ctrl+C で中断）。")
        elif self.args.pvp:
            print("人間同士で交互に入力します。")
        else:
            print("あなたは%sです。AIの強さ：%s%s" % (
                "▲先手" if self.human > 0 else "△後手", LEVELS[self.level]["label"],
                "（1手 %.1f秒）" % self.args.time if self.args.time else ""))
        print("入力例：76歩 / 7776 / 7g7f    コマンド一覧：help")
        need_show = True
        while True:
            legal = self.pos.legal_moves()
            if not self.result and not legal:
                self.result = (-self.pos.side, "詰み")
            if self.result:
                self.show()
                self.finish()
                return
            side = self.pos.side
            if self.ctrl[side] == "human":
                if need_show:
                    self.show()
                    if self.pos.in_check():
                        print(self.scr.c("1;31", "王手です！"))
                r = self.human_turn(legal)
                if r == "quit":
                    print("対局を中断しました。")
                    return
                if r == "resign":
                    self.result = (-side, "投了")
                    continue
                if r == "undo":
                    self.last_eval = None
                    need_show = True
                    continue
                _, m, sec = r
                disp = self.play(m, sec)
                need_show = True
                if self.ctrl[-side] == "ai":
                    print("  あなた：%s" % disp)
            else:
                if self.args.watch:
                    self.show()
                mv, sc, d, nodes, el = self.ai_think()
                disp = self.play(mv, el)
                if sc is None:
                    print("  %s：%s   [指せる手はこれだけ]" % (self.label_of(side), disp))
                else:
                    self.last_eval = sc
                    print("  %s：%s   [深さ%d / %s局面 / %.1f秒 / 評価値 %s]" % (
                        self.label_of(side), disp, d, format(nodes, ","), el, eval_text(sc, self.human)))
                need_show = True


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="ターミナル将棋：ターミナル上でAIと対局します。")
    ap.add_argument("--side", choices=["sente", "gote", "random"], default="sente",
                    help="あなたの手番（sente=先手, gote=後手, random）")
    ap.add_argument("--level", type=int, choices=[1, 2, 3, 4], default=2,
                    help="AIの強さ 1:初級 2:中級 3:上級 4:最上級（既定 2）")
    ap.add_argument("--time", type=float, default=None, help="AIの1手あたりの思考時間（秒）。指定すると強さ設定より優先")
    ap.add_argument("--watch", action="store_true", help="AI同士の対局を観戦")
    ap.add_argument("--pvp", action="store_true", help="人間同士で対局")
    ap.add_argument("--sfen", default=None, help="開始局面をSFENで指定")
    ap.add_argument("--clear", action="store_true", help="毎手、画面を消して描き直す")
    ap.add_argument("--no-color", action="store_true", help="色を使わない")
    args = ap.parse_args()
    args.vt = sys.stdout.isatty() and enable_vt()
    args.color = args.vt and not args.no_color and "NO_COLOR" not in os.environ
    args.human_side = {"sente": 1, "gote": -1}.get(args.side, random.choice((1, -1)))
    try:
        import readline  # noqa: F401  （Linux/macOSで矢印キーの入力履歴を使えるようにする）
    except ImportError:
        pass
    game = Game(args)
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n対局を中断しました。")


if __name__ == "__main__":
    main()
