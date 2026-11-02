#!/usr/bin/env python3
"""
Synthetic dataset generator for AI-optimized trim & fuse across derivative chips.

Covers four chip families built from shared IP:
  * MCU    - bandgap, HSI oscillator, LDO, temperature-sensor trims; fuse maps
  * PMIC   - reference + 4 coupled rails, thresholds, current sense; OTP images
  * Sensor - 3-axis accelerometer multi-temperature calibration
  * SoC    - per-core Fmax/Vmin, leakage, AVS bins, harvesting / SKU assignment
plus memory-repair bitmaps, an MCU fuse-map audit set, PMIC OTP config requests
and an SoC SKU demand table.

All values are synthetic but follow physically plausible relationships:
lot / wafer / radial / tilt process variation, shared-reference coupling,
package-dependent sort-to-final drift, gain error and INL in trim DACs,
and a small fraction of injected latent defects.

Usage:  python generate_synthetic_data.py [output_dir] [--seed N]
"""
import argparse
import os

import numpy as np
import pandas as pd

P = argparse.ArgumentParser()
P.add_argument("out", nargs="?", default="data")
P.add_argument("--seed", type=int, default=2026)
ARGS = P.parse_args()
OUT = ARGS.out
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(ARGS.seed)
N = lambda *s: rng.normal(0.0, 1.0, s if s else None)

# --------------------------------------------------------------------------
# Common: wafer die grid and process variation
# --------------------------------------------------------------------------
PROC = ["vthn", "vthp", "rs", "tox", "mob"]


def die_grid(wafer_mm, die_w, die_h, edge=3.0):
    R = wafer_mm / 2 - edge
    nx, ny = int(np.ceil(wafer_mm / die_w)), int(np.ceil(wafer_mm / die_h))
    xs = (np.arange(nx) - nx / 2 + 0.5) * die_w
    ys = (np.arange(ny) - ny / 2 + 0.5) * die_h
    X, Y = np.meshgrid(xs, ys)
    IX, IY = np.meshgrid(np.arange(nx), np.arange(ny))
    far = np.sqrt((np.abs(X) + die_w / 2) ** 2 + (np.abs(Y) + die_h / 2) ** 2)
    k = far <= R
    return IX[k], IY[k], X[k], Y[k]


def gen_wafers(prefix, lots_plan, wafer_mm, die_w, die_h):
    """lots_plan: list of (lot_id, derivative, n_wafers). Returns die frame + z (process sigmas)."""
    ix, iy, X, Y = die_grid(wafer_mm, die_w, die_h)
    R = wafer_mm / 2
    n = len(X)
    frames, zs = [], []
    for lot_id, deriv, nw in lots_plan:
        lot_off = N(5)
        for w in range(1, nw + 1):
            waf, bowl, tilt = 0.5 * N(5), 0.7 * N(5), 0.3 * N(2, 5)
            r = np.sqrt(X ** 2 + Y ** 2) / R
            Z = (lot_off + waf + np.outer(r ** 2 - 0.4, bowl)
                 + np.outer(X / R, tilt[0]) + np.outer(Y / R, tilt[1]) + 0.35 * N(n, 5))
            df = pd.DataFrame({
                "lot_id": lot_id, "wafer_id": f"{lot_id}-W{w:02d}", "derivative": deriv,
                "die_x": ix, "die_y": iy, "x_mm": X.round(2), "y_mm": Y.round(2),
                "radius_mm": (r * R).round(2)})
            frames.append(df)
            zs.append(Z)
    df = pd.concat(frames, ignore_index=True)
    Z = np.vstack(zs)
    df.insert(0, "die_id", [f"{prefix}-{i:06d}" for i in range(len(df))])
    # PCM / e-test (measured, with measurement noise)
    df["pcm_vth_n_mV"] = (450 + 15 * Z[:, 0] + 1.5 * N(len(df))).round(2)
    df["pcm_vth_p_mV"] = (-480 - 15 * Z[:, 1] + 1.5 * N(len(df))).round(2)
    df["pcm_rs_ohm_sq"] = (300 * (1 + 0.04 * Z[:, 2]) + 1.0 * N(len(df))).round(2)
    df["pcm_tox_A"] = (20 * (1 + 0.02 * Z[:, 3]) + 0.05 * N(len(df))).round(3)
    df["pcm_mobility_rel"] = (1 + 0.05 * Z[:, 4] + 0.003 * N(len(df))).round(4)
    return df, Z, R


def trim_search(untrim, target, step, bits, gain, inl=0.0, mult=False):
    """Exhaustive best code (ground truth) for an additive or multiplicative trim DAC."""
    codes = np.arange(2 ** bits)
    c0 = 2 ** (bits - 1)
    d = (codes[None, :] - c0) * step * gain[:, None] + inl * np.sin(codes * 0.9)[None, :]
    vals = untrim[:, None] * (1 + d) if mult else untrim[:, None] + d
    tgt = np.asarray(target, dtype=float)
    tgt = tgt[:, None] if tgt.ndim == 1 else tgt
    idx = np.abs(vals - tgt).argmin(axis=1)
    return idx, vals[np.arange(len(untrim)), idx]


def conv_iters(bits, n):
    """Conventional binary search iterations incl. occasional re-measure retries."""
    return bits + rng.choice([0, 0, 0, 1, 2], size=n)


def pack_fields(fields):
    """fields: list of (value_array, nbits) LSB first -> hex strings."""
    out = []
    n = len(fields[0][0])
    for i in range(n):
        word, pos = 0, 0
        for vals, nb in fields:
            v = int(vals[i]) & ((1 << nb) - 1)
            word |= v << pos
            pos += nb
        out.append(f"0x{word:0{(pos + 3) // 4}X}")
    return out


# --------------------------------------------------------------------------
# MCU
# --------------------------------------------------------------------------
MCU = {
    "MCU-A": dict(pkg="QFN48", flash_kb=512, flash_code=1, periph=0xFF, grade="industrial",
                  rdp=0, bg_shift=1.5e-3, hsi_shift=-0.0010, ldo_shift=2.0e-3),
    "MCU-B": dict(pkg="QFN32", flash_kb=256, flash_code=0, periph=0x3F, grade="industrial",
                  rdp=0, bg_shift=0.8e-3, hsi_shift=-0.0005, ldo_shift=1.2e-3),
    "MCU-C": dict(pkg="LQFP100", flash_kb=1024, flash_code=2, periph=0xFF, grade="automotive",
                  rdp=1, bg_shift=3.0e-3, hsi_shift=-0.0030, ldo_shift=4.5e-3),
}


def make_mcu():
    plan = ([(f"MA{l}", "MCU-A", 5) for l in range(1, 4)]
            + [("MB1", "MCU-B", 3), ("MC1", "MCU-C", 2)])
    df, Z, R = gen_wafers("MCU", plan, 200, 8.0, 8.0)
    n = len(df)
    r = df["radius_mm"].values / R
    info = df["derivative"].map(MCU)
    pkg_bg = np.array([d["bg_shift"] for d in info])
    pkg_hsi = np.array([d["hsi_shift"] for d in info])
    pkg_ldo = np.array([d["ldo_shift"] for d in info])
    df["package"] = [d["pkg"] for d in info]
    df["temp_grade"] = [d["grade"] for d in info]

    latent = rng.random(n) < 0.004
    df["latent_defect"] = latent

    # ---- Bandgap: target 1.200 V, 6-bit, 2 mV LSB
    bg_true = (1.200 + 0.009 * Z[:, 0] - 0.004 * Z[:, 3] + 0.003 * Z[:, 2] + 0.004 * N(n))
    bg_true[latent] += rng.choice([-1, 1], latent.sum()) * rng.uniform(0.05, 0.08, latent.sum())
    bg_gain = 1 + 0.04 * Z[:, 4] + 0.02 * N(n)
    df["bg_untrim_V"] = (bg_true + 0.0003 * N(n)).round(5)
    bg_code, bg_sort = trim_search(bg_true, 1.200, 2e-3, 6, bg_gain, inl=0.3e-3)
    df["bg_trim_code_opt"] = bg_code
    df["bg_trimmed_sort_V"] = (bg_sort + 0.0002 * N(n)).round(5)
    df["bg_conv_iterations"] = conv_iters(6, n)

    # ---- HSI oscillator: target 16 MHz, 7-bit, 0.2 % LSB (depends on trimmed bandgap)
    hsi_true = 16.0 * (1 - 0.035 * Z[:, 2] + 0.01 * Z[:, 4] + 0.012 * N(n)) * np.sqrt(bg_sort / 1.2)
    hsi_gain = 1 + 0.03 * Z[:, 3] + 0.02 * N(n)
    df["hsi_untrim_MHz"] = (hsi_true * (1 + 0.0002 * N(n))).round(5)
    hsi_code, hsi_sort = trim_search(hsi_true, 16.0, 0.002, 7, hsi_gain, inl=0.004, mult=True)
    df["hsi_trim_code_opt"] = hsi_code
    df["hsi_trimmed_sort_MHz"] = (hsi_sort * (1 + 0.0001 * N(n))).round(5)
    df["hsi_conv_iterations"] = conv_iters(7, n)

    # ---- LDO: target 1.10 V, 5-bit, 5 mV LSB (tracks trimmed bandgap)
    ldo_true = 1.10 * bg_sort / 1.2 + 0.012 * Z[:, 0] - 0.005 * Z[:, 1] + 0.006 * N(n)
    ldo_gain = 1 + 0.03 * Z[:, 2] + 0.02 * N(n)
    df["ldo_untrim_V"] = (ldo_true + 0.0005 * N(n)).round(5)
    ldo_code, ldo_sort = trim_search(ldo_true, 1.10, 5e-3, 5, ldo_gain, inl=0.5e-3)
    df["ldo_trim_code_opt"] = ldo_code
    df["ldo_trimmed_sort_V"] = (ldo_sort + 0.0003 * N(n)).round(5)
    df["ldo_conv_iterations"] = conv_iters(5, n)

    # ---- Temperature sensor calibration (counts at 30 C, label at 110 C)
    ts1 = 1050 + 25 * Z[:, 0] + 8 * N(n)
    slope = 3.20 * (1 + 0.015 * Z[:, 3] + 0.01 * N(n))
    df["ts_cal1_30C_counts"] = ts1.round().astype(int)
    df["ts_slope_counts_per_C_true"] = slope.round(4)
    df["ts_cal2_110C_counts"] = (ts1 + slope * 80 + 2 * N(n)).round().astype(int)
    df["ts_cal2_measured_on_tester"] = df["derivative"].eq("MCU-C")

    # ---- SRAM repair (2 spare rows)
    sram_fails = rng.poisson(0.05 + 0.6 * r ** 4)
    df["sram_fail_bits"] = sram_fails
    df["sram_repairable"] = sram_fails <= 2

    # ---- Conventional trim test time
    df["conv_trim_time_ms"] = (df.bg_conv_iterations * 1.2 + df.hsi_conv_iterations * 2.0
                               + df.ldo_conv_iterations * 1.0).round(1)

    # ---- Sort pass and final test (package shift grows with radius / stress)
    df["sort_pass"] = ((np.abs(bg_sort - 1.2) <= 4e-3) & (np.abs(hsi_sort / 16 - 1) <= 0.005)
                       & (np.abs(ldo_sort - 1.1) <= 0.011) & df["sram_repairable"])
    stress = 1 + 0.4 * r ** 2
    bg_fin = bg_sort + pkg_bg * stress + 0.8e-3 * N(n)
    bg_fin[latent] += rng.uniform(5e-3, 15e-3, latent.sum())
    hsi_fin = hsi_sort * (1 + pkg_hsi * stress + 0.0012 * N(n))
    ldo_fin = ldo_sort + pkg_ldo * stress + 1.5e-3 * N(n)
    df["bg_final_V"] = bg_fin.round(5)
    df["hsi_final_MHz"] = hsi_fin.round(5)
    df["ldo_final_V"] = ldo_fin.round(5)
    df["final_pass"] = (df["sort_pass"] & (np.abs(bg_fin - 1.2) <= 5e-3)
                        & (np.abs(hsi_fin / 16 - 1) <= 0.01) & (np.abs(ldo_fin - 1.1) <= 0.022))

    # ---- Fuse map (64-bit)
    df["fuse_map_hex"] = pack_fields([
        (bg_code, 6), (hsi_code, 7), (ldo_code, 5), (df.ts_cal1_30C_counts.values, 12),
        (np.array([d["flash_code"] for d in info]), 2), (np.array([d["periph"] for d in info]), 8),
        (np.array([1 if d["grade"] == "automotive" else 0 for d in info]), 1),
        (np.ones(n, int), 1), (np.array([d["rdp"] for d in info]), 1),
        (np.zeros(n, int), 21)])
    return df


MCU_SCHEMA = [  # field, lsb, nbits, description, MCU-A, MCU-B, MCU-C
    ("BG_TRIM", 0, 6, "Bandgap trim code (2 mV/LSB, 32 = no change)", "per-die", "per-die", "per-die"),
    ("HSI_TRIM", 6, 7, "HSI oscillator trim code (0.2 %/LSB, 64 = no change)", "per-die", "per-die", "per-die"),
    ("LDO_TRIM", 13, 5, "LDO trim code (5 mV/LSB, 16 = no change)", "per-die", "per-die", "per-die"),
    ("TS_CAL1", 18, 12, "Temperature sensor reading at 30 C", "per-die", "per-die", "per-die"),
    ("FLASH_SIZE", 30, 2, "0=256 KB, 1=512 KB, 2=1 MB", "1", "0", "2"),
    ("PERIPH_EN", 32, 8, "Peripheral enable mask", "0xFF", "0x3F", "0xFF"),
    ("TEMP_GRADE", 40, 1, "1 = automotive grade", "0", "0", "1"),
    ("DEBUG_LOCK", 41, 1, "1 = debug port locked (required in production)", "1", "1", "1"),
    ("RDP", 42, 1, "1 = read-out protection enabled", "0", "0", "1"),
    ("RESERVED", 43, 21, "Reserved, must be 0", "0", "0", "0"),
]


def make_mcu_fuse_audit(mcu):
    s = mcu.sample(1500, random_state=ARGS.seed).reset_index(drop=True)
    rows = []
    for _, d in s.iterrows():
        word = int(d.fuse_map_hex, 16)
        etype = "none"
        if rng.random() < 0.25:
            etype = rng.choice(["wrong_flash_size", "missing_debug_lock", "periph_mask_mismatch",
                                "trim_field_corrupt", "reserved_bit_set", "rdp_missing_automotive"])
            if etype == "rdp_missing_automotive" and d.derivative != "MCU-C":
                etype = "missing_debug_lock"
            if etype == "wrong_flash_size":
                cur = (word >> 30) & 3
                word = (word & ~(3 << 30)) | (((cur + 1) % 3) << 30)
            elif etype == "missing_debug_lock":
                word &= ~(1 << 41)
            elif etype == "periph_mask_mismatch":
                word ^= (int(rng.integers(1, 255)) << 32)
            elif etype == "trim_field_corrupt":
                word ^= 1 << int(rng.integers(0, 18))
            elif etype == "reserved_bit_set":
                word |= 1 << int(rng.integers(43, 64))
            elif etype == "rdp_missing_automotive":
                word &= ~(1 << 42)
        rows.append(dict(die_id=d.die_id, derivative=d.derivative, fuse_map_hex=f"0x{word:016X}",
                         has_error=etype != "none", error_type=etype))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# PMIC
# --------------------------------------------------------------------------
RAILS = ["buck1", "buck2", "ldo1", "ldo2"]
PMIC = {
    "PMIC-P1": dict(pkg="WLCSP", targets=[0.80, 1.10, 1.80, 3.30], seq="buck1>buck2>ldo1>ldo2",
                    i2c=0x60, cust=0, shift=0.4e-3),
    "PMIC-P2": dict(pkg="QFN24", targets=[0.75, 1.20, 1.80, 3.30], seq="buck2>buck1>ldo1>ldo2",
                    i2c=0x61, cust=0, shift=1.1e-3),
    "PMIC-C7": dict(pkg="QFN24", targets=[0.90, 1.05, 2.50, 3.30], seq="buck1>ldo1>buck2>ldo2",
                    i2c=0x62, cust=7, shift=1.1e-3),
}
COUPLE = np.array([[0.8, -0.3, 0.4, 0.1, 0.2], [0.6, 0.2, 0.5, -0.2, 0.3],
                   [0.3, 0.7, -0.2, 0.4, 0.1], [0.2, 0.5, 0.1, 0.6, -0.3]])


def make_pmic():
    plan = ([(f"PA{l}", "PMIC-P1", 5) for l in range(1, 4)]
            + [("PB1", "PMIC-P2", 3), ("PC1", "PMIC-C7", 2)])
    df, Z, R = gen_wafers("PMIC", plan, 200, 7.0, 7.0)
    n = len(df)
    r = df["radius_mm"].values / R
    info = df["derivative"].map(PMIC)
    df["package"] = [d["pkg"] for d in info]
    latent = rng.random(n) < 0.005
    df["latent_defect"] = latent
    stress = 1 + 0.4 * r ** 2
    shift = np.array([d["shift"] for d in info])

    # Reference: 0.600 V, 6-bit, 0.5 mV LSB
    vref = 0.600 + 0.006 * Z[:, 0] - 0.003 * Z[:, 3] + 0.002 * N(n)
    g = 1 + 0.04 * Z[:, 4] + 0.02 * N(n)
    df["vref_untrim_V"] = (vref + 0.0001 * N(n)).round(5)
    vc, vref_s = trim_search(vref, 0.600, 0.75e-3, 6, g, inl=0.1e-3)
    df["vref_trim_code_opt"] = vc
    df["vref_trimmed_sort_V"] = vref_s.round(5)
    vref_f = vref_s + shift * stress * 0.6 / 1.2 + 0.3e-3 * N(n)
    df["vref_final_V"] = vref_f.round(5)

    targets = np.array([d["targets"] for d in info])
    codes = {"vref": vc}
    iters = 6 + rng.choice([0, 0, 1], n)
    sort_ok = np.abs(vref_s - 0.6) <= 1.5e-3
    final_ok = np.abs(vref_f - 0.6) <= 3e-3
    for i, rail in enumerate(RAILS):
        T = targets[:, i]
        untr = T * (vref_s / 0.6) * (1 + 0.008 * Z @ COUPLE[i] + 0.0012 * N(n))
        gain = 1 + 0.03 * Z[:, (i + 2) % 5] + 0.01 * N(n)
        df[f"{rail}_target_V"] = T
        df[f"{rail}_untrim_V"] = (untr * (1 + 0.0003 * N(n))).round(5)
        c, s = trim_search(untr, T, 0.002, 6, gain, inl=0.0006, mult=True)
        codes[rail] = c
        df[f"{rail}_trim_code_opt"] = c
        df[f"{rail}_trimmed_sort_V"] = s.round(5)
        fin = s * (vref_f / vref_s) * (1 + 0.001 * N(n))
        fin[latent] *= 1 + rng.uniform(0.01, 0.03, latent.sum())
        df[f"{rail}_final_V"] = fin.round(5)
        sort_ok &= np.abs(s / T - 1) <= 0.005
        final_ok &= np.abs(fin / T - 1) <= 0.01
        iters = iters + 6 + rng.choice([0, 0, 1], n)

    for name, tgt, bits, step, zc in [("ovp", 3.63, 4, 0.005, 1), ("uvlo", 2.70, 4, 0.005, 3)]:
        untr = tgt * (vref_s / 0.6) * (1 + 0.012 * Z[:, zc] + 0.005 * N(n))
        c, s = trim_search(untr, tgt, step, bits, np.ones(n), mult=True)
        df[f"{name}_untrim_V"] = untr.round(4)
        df[f"{name}_trim_code_opt"] = c
        df[f"{name}_trimmed_V"] = s.round(4)
        codes[name] = c
        iters = iters + bits
    untr = 3.0 * (1 + 0.06 * Z[:, 2] - 0.02 * Z[:, 4] + 0.02 * N(n))
    c, s = trim_search(untr, 3.0, 0.01, 5, np.ones(n), mult=True)
    df["ilim_untrim_A"] = untr.round(4)
    df["ilim_trim_code_opt"] = c
    df["ilim_trimmed_A"] = s.round(4)
    codes["ilim"] = c
    iters = iters + 5

    # Current sense: 2-point measurement vs full-sweep truth
    ge = 0.8 * Z[:, 2] + 0.5 * N(n)
    off = 5 * Z[:, 1] + 3 * N(n)
    inl = 0.10 * Z[:, 4] + 0.05 * N(n)
    for I in (0.5, 2.0):
        nl = inl / 100 * I * (I - 3.0) / 1.5
        df[f"cs_meas_{str(I).replace('.', 'p')}A_A"] = (I * (1 + ge / 100 + nl) + off / 1000
                                                         + 0.002 * N(n)).round(5)
    df["cs_gain_err_true_pct"] = ge.round(4)
    df["cs_offset_true_mA"] = off.round(3)
    df["cs_inl_true_pct"] = inl.round(4)

    eff = 91 - 0.8 * Z[:, 2] + 0.3 * N(n)
    lreg = 4 + 1.2 * np.abs(Z[:, 2]) + 0.5 * np.abs(N(n))
    eff[latent] -= rng.uniform(2, 5, latent.sum())
    lreg[latent] += rng.uniform(5, 12, latent.sum())
    df["efficiency_1A_pct"] = eff.round(3)
    df["load_reg_mV"] = lreg.round(3)

    df["conv_trim_iterations"] = iters
    df["conv_trim_time_ms"] = (iters * 0.8).round(1)
    df["sort_pass"] = sort_ok
    df["final_pass"] = sort_ok & final_ok & (eff > 88) & (lreg < 10)

    # OTP image
    vcode = lambda V: np.round((V - 0.4) / 0.0125).astype(int)
    seq_code = np.array([sum(RAILS.index(x) << (2 * k) for k, x in enumerate(d["seq"].split(">")))
                         for d in info])
    df["sequence"] = [d["seq"] for d in info]
    df["i2c_addr"] = [f"0x{d['i2c']:02X}" for d in info]
    df["otp_image_hex"] = pack_fields(
        [(codes["vref"], 6)] + [(codes[rl], 6) for rl in RAILS]
        + [(codes["ovp"], 4), (codes["uvlo"], 4), (codes["ilim"], 5)]
        + [(vcode(targets[:, i]), 8) for i in range(4)]
        + [(seq_code, 8), (np.array([d["i2c"] for d in info]), 7), (np.array([d["cust"] for d in info]), 8)])
    return df


def make_pmic_otp_requests(k=400):
    lim = {"buck1": (0.4, 1.8), "buck2": (0.4, 1.8), "ldo1": (0.8, 3.3), "ldo2": (1.2, 3.6)}
    rows = []
    for i in range(k):
        T = [round(rng.uniform(0.6, 1.3), 3), round(rng.uniform(0.9, 1.5), 3),
             round(rng.choice([1.8, 2.5, 2.8, 3.0]), 2), 3.3]
        seq = ["buck1", "buck2", "ldo1", "ldo2"]
        rng.shuffle(seq)
        if seq.index("ldo2") < seq.index("buck1"):
            seq.remove("ldo2")
            seq.append("ldo2")
        addr = int(rng.integers(0x40, 0x70))
        bus = sorted(set(int(a) for a in rng.integers(0x20, 0x78, size=3)) - {addr})
        err = "valid"
        u = rng.random()
        if u < 0.12:
            j = int(rng.integers(0, 4))
            lo, hi = lim[RAILS[j]]
            T[j] = round(hi + rng.uniform(0.1, 0.6) if rng.random() < 0.7 else lo - 0.1, 3)
            err = "out_of_range"
        elif u < 0.22:
            seq.remove("ldo2")
            seq.insert(0, "ldo2")
            err = "sequence_conflict"
        elif u < 0.30:
            seq[int(rng.integers(0, 4))] = seq[int(rng.integers(0, 4))]
            err = "invalid_sequence" if len(set(seq)) < 4 else "valid"
        elif u < 0.40:
            bus.append(addr)
            err = "address_collision"
        elif u < 0.44:
            addr = int(rng.choice([0x00, 0x03, 0x78, 0x7F]))
            err = "address_reserved"
        rows.append(dict(request_id=f"OTPREQ-{i:04d}", customer=f"CUST-{int(rng.integers(1, 40)):02d}",
                         buck1_V=T[0], buck2_V=T[1], ldo1_V=T[2], ldo2_V=T[3],
                         sequence=">".join(seq), i2c_addr=f"0x{addr:02X}",
                         other_addresses_on_bus=";".join(f"0x{a:02X}" for a in sorted(bus)),
                         label=err))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Sensor (3-axis accelerometer)
# --------------------------------------------------------------------------
SENS = {"ACC-2G": (2, 16384, "LGA14"), "ACC-8G": (8, 4096, "LGA14"), "ACC-16G": (16, 2048, "LGA12")}


def make_sensor():
    plan = ([(f"SA{l}", "ACC-2G", 5) for l in range(1, 4)]
            + [("SB1", "ACC-8G", 3), ("SC1", "ACC-16G", 2)])
    df, Z, R = gen_wafers("SNS", plan, 200, 7.0, 7.0)
    n = len(df)
    r = df["radius_mm"].values / R
    df["full_scale_g"] = df["derivative"].map(lambda d: SENS[d][0])
    df["nominal_sens_LSB_per_g"] = df["derivative"].map(lambda d: SENS[d][1])
    df["package"] = df["derivative"].map(lambda d: SENS[d][2])
    pkg_k = df["package"].map({"LGA14": 1.0, "LGA12": 1.3}).values
    latent = rng.random(n) < 0.003
    df["latent_defect"] = latent
    stress = pkg_k * (0.6 * r ** 2 + 0.4 * N(n))
    df["stress_gauge_mV"] = (stress * 10 + 1.5 * N(n)).round(3)
    df["asic_vref_mV"] = (1200 + 5 * Z[:, 0] + 1.0 * N(n)).round(3)
    res = 5.0 * (1 + 0.03 * Z[:, 3] + 0.01 * N(n))
    q = 2.0 * (1 + 0.05 * Z[:, 4] + 0.03 * N(n))
    res[latent] *= rng.uniform(0.85, 0.92, latent.sum())
    df["mems_resonance_kHz"] = res.round(4)
    df["mems_q_factor"] = q.round(4)
    df["characterized_3temp"] = rng.random(n) < 0.20
    temps = [-40, 25, 85]
    for ax, a in zip("xyz", range(3)):
        za = 0.5 * N(n)
        off25 = 10 * Z[:, 0] + 20 * stress + 8 * za
        tco = 0.15 * Z[:, 3] + 0.25 * stress + 0.05 * N(n) + 0.02 * a
        tco2 = 0.001 * Z[:, 4] + 0.0005 * N(n)
        s25 = 1 + 0.02 * Z[:, 2] + 0.01 * N(n)
        tcs = 150 * Z[:, 1] + 120 * stress + 50 * N(n)
        tco[latent] += rng.uniform(0.5, 1.0, latent.sum())
        df[f"st_response_{ax}_mg"] = (500 * s25 * (1 + 0.01 * N(n))).round(3)
        for T in temps:
            dT = T - 25
            df[f"offset_{ax}_{'m40' if T < 0 else T}C_mg"] = (off25 + tco * dT + tco2 * dT ** 2
                                                              + 1.5 * N(n)).round(3)
            df[f"sens_{ax}_{'m40' if T < 0 else T}C_rel"] = (s25 * (1 + tcs * 1e-6 * dT)
                                                             + 0.001 * N(n)).round(6)
        df[f"tco_{ax}_true_mg_per_C"] = tco.round(5)
        df[f"tco2_{ax}_true_mg_per_C2"] = tco2.round(6)
        df[f"tcs_{ax}_true_ppm_per_C"] = tcs.round(3)
        df[f"post_reflow_offset_shift_{ax}_mg"] = (6 * stress + 2 * N(n)).round(3)
        df[f"cal_offset_code_{ax}"] = np.round(-off25 / 0.5).astype(int)
        df[f"cal_tco_code_{ax}"] = np.clip(np.round(-tco / 0.01), -128, 127).astype(int)
        df[f"cal_tcs_code_{ax}"] = np.clip(np.round(-tcs / 5), -128, 127).astype(int)
    df["conv_test_insertions"] = 3
    df["conv_test_time_s"] = (3 * 2.4 + 0.2 * N(n)).round(2)
    return df


# --------------------------------------------------------------------------
# SoC
# --------------------------------------------------------------------------
SKUS = pd.DataFrame([
    dict(sku="SoC-Pro", cores=8, fmax_GHz=3.0, tdp_W=18.0, price_usd=145, weekly_demand_units=900),
    dict(sku="SoC-Std", cores=6, fmax_GHz=2.6, tdp_W=15.0, price_usd=95, weekly_demand_units=2200),
    dict(sku="SoC-Lite", cores=4, fmax_GHz=2.2, tdp_W=10.0, price_usd=55, weekly_demand_units=2600),
])


def soc_power(fmax_sel, ncores, f, V, leak_hot_A):
    return ncores * 0.62 * (V / 0.85) ** 2 * f + leak_hot_A * V


def make_soc():
    plan = [(f"QA{l}", "SoC-die", 5) for l in range(1, 5)]
    df, Z, R = gen_wafers("SOC", plan, 300, 14.0, 14.0)
    n = len(df)
    r = df["radius_mm"].values / R
    df["ro_freq_MHz"] = (950 * (1 - 0.04 * Z[:, 0] + 0.03 * Z[:, 4] + 0.01 * N(n))).round(2)
    df["cpm_path_delay_ps"] = (320 * (1 + 0.04 * Z[:, 0] - 0.03 * Z[:, 4] + 0.008 * N(n))).round(2)
    iddq = 120 * np.exp(-0.35 * Z[:, 0] + 0.1 * Z[:, 3]) * (1 + 0.1 * N(n))
    df["iddq_25C_mA"] = iddq.round(2)
    leak_hot = iddq * 22 / 1000
    base = 3.02 * (1 - 0.05 * Z[:, 0] + 0.035 * Z[:, 4])
    fmax = np.zeros((n, 8))
    good = np.ones((n, 8), bool)
    for c in range(8):
        f = base * (1 + 0.015 * N(n))
        dprob = 0.06 + 0.15 * r ** 3
        bad = rng.random(n) < dprob
        good[:, c] = ~bad
        fmax[:, c] = f
        df[f"core{c}_defect"] = bad
        df[f"core{c}_fmax_GHz"] = np.where(bad, np.nan, f.round(4))
        df[f"core{c}_vmin_2GHz_mV"] = np.where(bad, np.nan,
                                               (640 + 18 * Z[:, 0] - 10 * Z[:, 4] + 8 * N(n)).round(2))
    l2 = rng.poisson(np.repeat((0.3 + 2.0 * r ** 4)[:, None], 4, axis=1))
    for s in range(4):
        df[f"l2_slice{s}_fail_bits"] = l2[:, s]
    l2_ok = (l2 <= 6).all(axis=1)
    df["l2_repairable"] = l2_ok
    df["conv_speed_test_time_ms"] = (450 + 30 * N(n)).round(1)

    sku_out, avs, mask_out, pw = [], [], [], []
    for i in range(n):
        order = np.argsort(-np.where(good[i], fmax[i], -1))
        assigned, bin_, mask, p = "scrap", -1, 0xFF, np.nan
        if l2_ok[i]:
            for _, s in SKUS.iterrows():
                k = int(s.cores)
                sel = order[:k]
                if not good[i, sel].all():
                    continue
                fslow = fmax[i, sel].min()
                vreq = 0.85 * (s.fmax_GHz / fslow) ** 0.8
                if vreq > 0.90:
                    continue
                vreq = max(vreq, 0.76)
                b = int(np.ceil((vreq - 0.75) / 0.0125))
                vb = 0.75 + b * 0.0125
                pp = soc_power(fslow, k, s.fmax_GHz, vb, leak_hot[i])
                if pp <= s.tdp_W:
                    assigned, bin_, p = s.sku, b, pp
                    mask = int(sum(1 << int(c) for c in range(8) if c not in sel))
                    break
        sku_out.append(assigned)
        avs.append(bin_)
        mask_out.append(f"0x{mask:02X}")
        pw.append(round(p, 3) if p == p else np.nan)
    df["derivative"] = sku_out
    df["sku_rule_based"] = sku_out
    df["avs_voltage_bin"] = avs
    df["avs_voltage_V"] = np.where(np.array(avs) >= 0, 0.75 + np.array(avs) * 0.0125, np.nan).round(4)
    df["cores_disabled_mask"] = mask_out
    df["power_at_sku_W"] = pw
    return df


# --------------------------------------------------------------------------
# Memory repair bitmaps
# --------------------------------------------------------------------------
def exact_repair(fails, sr, sc):
    if not fails:
        return True, [], []
    rows, cols = {}, {}
    for rr, cc in fails:
        rows.setdefault(rr, set()).add(cc)
        cols.setdefault(cc, set()).add(rr)
    for rr, cs in rows.items():  # must-repair rows
        if len(cs) > sc:
            if sr == 0:
                return False, [], []
            ok, a, b = exact_repair({f for f in fails if f[0] != rr}, sr - 1, sc)
            return (ok, [rr] + a, b)
    for cc, rs in cols.items():
        if len(rs) > sr:
            if sc == 0:
                return False, [], []
            ok, a, b = exact_repair({f for f in fails if f[1] != cc}, sr, sc - 1)
            return (ok, a, [cc] + b)
    if len(fails) > 2 * sr * sc:  # after must-repair each line holds <= spares of the other kind
        return False, [], []
    rr, cc = next(iter(sorted(fails)))
    if sr:
        ok, a, b = exact_repair({f for f in fails if f[0] != rr}, sr - 1, sc)
        if ok:
            return True, [rr] + a, b
    if sc:
        ok, a, b = exact_repair({f for f in fails if f[1] != cc}, sr, sc - 1)
        if ok:
            return True, a, [cc] + b
    return False, [], []


def greedy_repair(fails, sr, sc):
    fails = set(fails)
    while fails and (sr or sc):
        rc, cc = {}, {}
        for r_, c_ in fails:
            rc[r_] = rc.get(r_, 0) + 1
            cc[c_] = cc.get(c_, 0) + 1
        br = max(rc.items(), key=lambda t: t[1]) if sr else (None, -1)
        bc = max(cc.items(), key=lambda t: t[1]) if sc else (None, -1)
        if br[1] >= bc[1]:
            fails = {f for f in fails if f[0] != br[0]}
            sr -= 1
        else:
            fails = {f for f in fails if f[1] != bc[0]}
            sc -= 1
    return not fails


def make_repair(soc, k=3000):
    ids = soc["die_id"].sample(k, random_state=ARGS.seed, replace=False).values
    rows = []
    for i, die in enumerate(ids):
        lam = rng.choice([0.5, 2, 4, 7, 10])
        fails = {(int(rng.integers(0, 512)), int(rng.integers(0, 512))) for _ in range(rng.poisson(lam))}
        for _ in range(rng.binomial(2, 0.12)):
            rr = int(rng.integers(0, 512))
            fails |= {(rr, int(c)) for c in rng.choice(512, int(rng.integers(6, 30)), replace=False)}
        for _ in range(rng.binomial(2, 0.12)):
            cc = int(rng.integers(0, 512))
            fails |= {(int(rr), cc) for rr in rng.choice(512, int(rng.integers(6, 30)), replace=False)}
        for _ in range(rng.binomial(1, 0.2)):  # clustered 2x2 / 3x3 defects
            r0, c0 = int(rng.integers(0, 509)), int(rng.integers(0, 509))
            s_ = int(rng.integers(2, 4))
            fails |= {(r0 + a, c0 + b) for a in range(s_) for b in range(s_)}
        if rng.random() < 0.25:  # cross-coupled faults sharing a few word/bit lines (hard for greedy)
            nl = int(rng.integers(7, 10))
            Rs, Cs = rng.choice(512, nl, replace=False), rng.choice(512, nl, replace=False)
            fails |= {(int(rng.choice(Rs)), int(rng.choice(Cs))) for _ in range(int(rng.integers(14, 22)))}
        ok, rr_, cc_ = exact_repair(fails, 4, 4)
        rows.append(dict(array_id=f"L2ARR-{i:05d}", die_id=die, array="L2_slice0", rows=512, cols=512,
                         spare_rows=4, spare_cols=4, n_fail_cells=len(fails),
                         fail_cells=";".join(f"{a}:{b}" for a, b in sorted(fails)),
                         greedy_repairable=greedy_repair(fails, 4, 4), optimal_repairable=ok,
                         optimal_spare_rows_used=";".join(map(str, sorted(rr_))) if ok else "",
                         optimal_spare_cols_used=";".join(map(str, sorted(cc_))) if ok else ""))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    mcu = make_mcu()
    mcu.to_csv(f"{OUT}/mcu_trim_fuse.csv", index=False)
    make_mcu_fuse_audit(mcu).to_csv(f"{OUT}/mcu_fuse_map_audit.csv", index=False)
    pd.DataFrame(MCU_SCHEMA, columns=["field", "lsb", "nbits", "description", "MCU-A", "MCU-B", "MCU-C"]
                 ).to_csv(f"{OUT}/mcu_fuse_schema.csv", index=False)

    pmic = make_pmic()
    pmic.to_csv(f"{OUT}/pmic_trim_otp.csv", index=False)
    make_pmic_otp_requests().to_csv(f"{OUT}/pmic_otp_config_requests.csv", index=False)

    make_sensor().to_csv(f"{OUT}/sensor_calibration.csv", index=False)

    soc = make_soc()
    soc.to_csv(f"{OUT}/soc_binning_harvesting.csv", index=False)
    SKUS.to_csv(f"{OUT}/soc_sku_demand.csv", index=False)
    make_repair(soc).to_csv(f"{OUT}/memory_repair_bitmaps.csv", index=False)

    for f in sorted(os.listdir(OUT)):
        if f.endswith(".csv"):
            d = pd.read_csv(f"{OUT}/{f}")
            print(f"{f:34s} {len(d):7d} rows  {d.shape[1]:4d} cols")
