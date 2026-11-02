#!/usr/bin/env python3
"""
Baseline models that show the synthetic dataset supports each use case.
Splits are by wafer so no wafer appears in both train and test.

Usage: python baseline_models.py [data_dir]
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
from sklearn.metrics import r2_score

D = sys.argv[1] if len(sys.argv) > 1 else "data"
PCM = ["pcm_vth_n_mV", "pcm_vth_p_mV", "pcm_rs_ohm_sq", "pcm_tox_A", "pcm_mobility_rel"]
POS = ["x_mm", "y_mm", "radius_mm"]
rng = np.random.default_rng(0)


def wafer_split(df, frac=0.25):
    w = df["wafer_id"].unique()
    test_w = set(rng.choice(w, max(1, int(len(w) * frac)), replace=False))
    m = df["wafer_id"].isin(test_w)
    return df[~m], df[m]


def fit(X, y):
    return HGB(max_iter=300, learning_rate=0.08, random_state=0).fit(X, y)


def code_report(name, y, yhat, bits, conv_iters):
    c = np.clip(np.round(yhat), 0, 2 ** bits - 1)
    err = np.abs(c - y)
    exact, within1 = (err == 0).mean(), (err <= 1).mean()
    # predict -> verify (1 measurement); +1 step if off by 1; else fall back to full search
    ai_iters = np.where(err == 0, 1, np.where(err <= 1, 2, 1 + bits)).mean()
    print(f"  {name:28s} exact {exact:6.1%} | within ±1 {within1:6.1%} | "
          f"iterations conv {conv_iters:4.1f} -> AI {ai_iters:4.2f}")


print("=" * 88)
print("1) MCU predictive trim (train MCU-A wafers, test held-out MCU-A wafers)")
mcu = pd.read_csv(f"{D}/mcu_trim_fuse.csv")
a = mcu[mcu.derivative == "MCU-A"]
tr, te = wafer_split(a)
for t, unt, bits in [("bg", "bg_untrim_V", 6), ("hsi", "hsi_untrim_MHz", 7), ("ldo", "ldo_untrim_V", 5)]:
    feats = [unt] + PCM + POS
    mdl = fit(tr[feats], tr[f"{t}_trim_code_opt"])
    code_report(f"{t} trim code", te[f"{t}_trim_code_opt"].values, mdl.predict(te[feats]), bits,
                te[f"{t}_conv_iterations"].mean())
conv_ms = te.conv_trim_time_ms.mean()
print(f"  conventional trim time {conv_ms:.1f} ms/die")

print("\n2) MCU drift-aware targets + transfer learning (bandgap sort->final shift)")
mcu["bg_shift_mV"] = (mcu.bg_final_V - mcu.bg_trimmed_sort_V) * 1000
feats = PCM + POS
base = mcu[mcu.derivative == "MCU-A"]
c = mcu[mcu.derivative == "MCU-C"]
c_tune = c.sample(50, random_state=0)
c_test = c.drop(c_tune.index)
from sklearn.metrics import mean_absolute_error as MAE
m0 = fit(base[feats], base.bg_shift_mV)
print(f"  zero-shot (MCU-A model on MCU-C): MAE {MAE(c_test.bg_shift_mV, m0.predict(c_test[feats])):5.2f} mV")
X = pd.concat([base[feats].assign(is_c=0), c_tune[feats].assign(is_c=1)])
y = pd.concat([base.bg_shift_mV, c_tune.bg_shift_mV])
w = np.r_[np.ones(len(base)), np.full(len(c_tune), 20.0)]
m1 = HGB(max_iter=300, learning_rate=0.08, random_state=0).fit(X, y, sample_weight=w)
pred = m1.predict(c_test[feats].assign(is_c=1))
print(f"  fine-tuned with 50 MCU-C dies:    MAE {MAE(c_test.bg_shift_mV, pred):5.2f} mV")
fin_conv = (np.abs(c_test.bg_final_V - 1.2) <= 5e-3).mean()
fin_ai = (np.abs(c_test.bg_final_V - pred / 1000 - 1.2) <= 5e-3).mean()
print(f"  MCU-C bandgap final pass: trim to 1.200 V {fin_conv:6.1%} -> trim to offset target {fin_ai:6.1%}")

print("\n3) PMIC: predict all four rail codes from the reference measurement + PCM only")
pm = pd.read_csv(f"{D}/pmic_trim_otp.csv")
p1 = pm[pm.derivative == "PMIC-P1"]
tr, te = wafer_split(p1)
feats = ["vref_untrim_V", "vref_trimmed_sort_V"] + PCM + POS
for rail in ["buck1", "buck2", "ldo1", "ldo2"]:
    mdl = fit(tr[feats], tr[f"{rail}_trim_code_opt"])
    code_report(f"{rail} code (no rail meas.)", te[f"{rail}_trim_code_opt"].values,
                mdl.predict(te[feats]), 6, 6.3)

print("\n4) Sensor: predict temperature coefficients from room-temperature data")
s = pd.read_csv(f"{D}/sensor_calibration.csv")
tr, te = s[s.characterized_3temp], s[~s.characterized_3temp]
feats = ["offset_x_25C_mg", "sens_x_25C_rel", "st_response_x_mg", "stress_gauge_mV",
         "asic_vref_mV", "mems_resonance_kHz", "mems_q_factor"] + PCM + POS
for lab in ["tco_x_true_mg_per_C", "tcs_x_true_ppm_per_C"]:
    mdl = fit(tr[feats], tr[lab])
    print(f"  {lab:28s} R2 {r2_score(te[lab], mdl.predict(te[feats])):6.2f}")
mdl = fit(tr[feats], tr.tco_x_true_mg_per_C)
pred_85 = te.offset_x_25C_mg + mdl.predict(te[feats]) * 60
no_tc = te.offset_x_25C_mg
print(f"  residual offset at 85 C (RMS mg): no TC comp {np.sqrt(((te.offset_x_85C_mg - no_tc) ** 2).mean()):5.1f}"
      f" | AI 1-insertion {np.sqrt(((te.offset_x_85C_mg - pred_85) ** 2).mean()):5.1f}")

print("\n5) SoC: predict slowest-core Fmax from monitors (reduces functional speed test)")
q = pd.read_csv(f"{D}/soc_binning_harvesting.csv")
fcols = [f"core{i}_fmax_GHz" for i in range(8)]
q["fmax_min_good"] = q[fcols].min(axis=1)
tr, te = wafer_split(q)
feats = ["ro_freq_MHz", "cpm_path_delay_ps", "iddq_25C_mA"] + PCM + POS
mdl = fit(tr[feats], tr.fmax_min_good)
print(f"  slowest-core Fmax R2 {r2_score(te.fmax_min_good, mdl.predict(te[feats])):6.2f}")
print("  rule-based SKU mix:", q.sku_rule_based.value_counts(normalize=True).round(3).to_dict())

print("\n6) Fuse-map validation (schema rules + join to sort trim codes)")
au = pd.read_csv(f"{D}/mcu_fuse_map_audit.csv").merge(
    mcu[["die_id", "bg_trim_code_opt", "hsi_trim_code_opt", "ldo_trim_code_opt"]], on="die_id")
exp = {"MCU-A": (1, 0xFF, 0), "MCU-B": (0, 0x3F, 0), "MCU-C": (2, 0xFF, 1)}


def check(r):
    w = int(r.fuse_map_hex, 16)
    fl, pe, rdp = exp[r.derivative]
    trim = (w & 63, (w >> 6) & 127, (w >> 13) & 31)
    return bool(((w >> 30) & 3) != fl or ((w >> 32) & 255) != pe or not (w >> 41) & 1
                or ((w >> 42) & 1) != rdp or (w >> 43) != 0
                or trim != (r.bg_trim_code_opt, r.hsi_trim_code_opt, r.ldo_trim_code_opt))


flag = au.apply(check, axis=1)
print(f"  detection: {(flag & au.has_error).sum()}/{au.has_error.sum()} errors caught, "
      f"{(flag & ~au.has_error).sum()} false alarms")

print("\n7) Memory repair: greedy vs exact allocation")
rp = pd.read_csv(f"{D}/memory_repair_bitmaps.csv")
print(f"  repairable: greedy {rp.greedy_repairable.mean():6.1%} | exact {rp.optimal_repairable.mean():6.1%}"
      f" | arrays saved by exact solver {(rp.optimal_repairable & ~rp.greedy_repairable).sum()}")
print("=" * 88)
