#!/usr/bin/env python3
"""Writes DATA_DICTIONARY.md listing every column of every CSV with its meaning and role."""
import re
import sys

import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT = sys.argv[2] if len(sys.argv) > 2 else "DATA_DICTIONARY.md"

# (regex, description, role)  role: id | feature | label | meta
PAT = [
    (r"die_id", "Unique die identifier", "id"),
    (r"lot_id", "Fab lot", "meta"),
    (r"wafer_id", "Wafer (lot-Wnn); use for grouped train/test splits", "meta"),
    (r"derivative", "Derivative / SKU the die is fused as", "meta"),
    (r"die_x|die_y", "Die grid index on the wafer", "feature"),
    (r"x_mm|y_mm", "Die centre position from wafer centre (mm)", "feature"),
    (r"radius_mm", "Distance of die centre from wafer centre (mm)", "feature"),
    (r"pcm_vth_n_mV", "Process monitor: NMOS threshold voltage (mV)", "feature"),
    (r"pcm_vth_p_mV", "Process monitor: PMOS threshold voltage (mV)", "feature"),
    (r"pcm_rs_ohm_sq", "Process monitor: poly sheet resistance (ohm/sq)", "feature"),
    (r"pcm_tox_A", "Process monitor: gate oxide thickness (Angstrom)", "feature"),
    (r"pcm_mobility_rel", "Process monitor: relative carrier mobility", "feature"),
    (r"package", "Package type (drives sort-to-final drift)", "meta"),
    (r"temp_grade", "Temperature grade", "meta"),
    (r"latent_defect", "Injected latent defect (ground truth for anomaly screening)", "label"),
    (r"bg_untrim_V", "Bandgap output before trim, measured at sort (V); target 1.200 V", "feature"),
    (r"bg_trim_code_opt", "Optimal 6-bit bandgap trim code (2 mV/LSB, 32 = no change)", "label"),
    (r"bg_trimmed_sort_V", "Bandgap after optimal trim at sort (V)", "label"),
    (r"bg_final_V", "Bandgap at final test after packaging (V); spec 1.200 V ± 5 mV", "label"),
    (r"hsi_untrim_MHz", "HSI oscillator before trim (MHz); target 16 MHz", "feature"),
    (r"hsi_trim_code_opt", "Optimal 7-bit HSI trim code (0.2 %/LSB, 64 = no change)", "label"),
    (r"hsi_trimmed_sort_MHz", "HSI after optimal trim at sort (MHz)", "label"),
    (r"hsi_final_MHz", "HSI at final test (MHz); spec ± 1 %", "label"),
    (r"ldo_untrim_V", "LDO output before trim (V); target 1.10 V", "feature"),
    (r"ldo_trim_code_opt", "Optimal 5-bit LDO trim code (5 mV/LSB, 16 = no change)", "label"),
    (r"ldo_trimmed_sort_V", "LDO after optimal trim at sort (V)", "label"),
    (r"ldo_final_V", "LDO at final test (V); spec ± 2 %", "label"),
    (r"(bg|hsi|ldo)_conv_iterations", "Iterations used by the conventional binary-search trim", "meta"),
    (r"ts_cal1_30C_counts", "Temperature sensor reading at 30 C (counts), fused as TS_CAL1", "feature"),
    (r"ts_slope_counts_per_C_true", "True temperature-sensor slope (counts/°C)", "label"),
    (r"ts_cal2_110C_counts", "Temperature sensor reading at 110 C (counts); label to predict from 30 C data", "label"),
    (r"ts_cal2_measured_on_tester", "True where the hot point is actually measured in production (MCU-C)", "meta"),
    (r"sram_fail_bits", "Failing SRAM bits at sort", "feature"),
    (r"sram_repairable", "SRAM repairable with 2 spare rows", "label"),
    (r"conv_trim_time_ms", "Trim test time with conventional search (ms)", "meta"),
    (r"conv_trim_iterations", "Total conventional trim iterations (all trims)", "meta"),
    (r"sort_pass", "Die passes wafer sort", "label"),
    (r"final_pass", "Die passes final test after packaging", "label"),
    (r"fuse_map_hex", "64-bit fuse word (see mcu_fuse_schema.csv)", "label"),
    (r"has_error", "Fuse word contains an injected error", "label"),
    (r"error_type", "Injected error type (none, wrong_flash_size, missing_debug_lock, ...)", "label"),
    (r"vref_untrim_V", "PMIC reference before trim (V); target 0.600 V", "feature"),
    (r"vref_trim_code_opt", "Optimal 6-bit reference trim code (0.75 mV/LSB)", "label"),
    (r"vref_trimmed_sort_V", "Reference after trim at sort (V)", "feature"),
    (r"vref_final_V", "Reference at final test (V)", "label"),
    (r"(buck1|buck2|ldo1|ldo2)_target_V", "Default output target for this derivative (V)", "meta"),
    (r"(buck1|buck2|ldo1|ldo2)_untrim_V", "Rail output before rail trim, after reference trim (V)", "feature"),
    (r"(buck1|buck2|ldo1|ldo2)_trim_code_opt", "Optimal 6-bit rail trim code (0.2 % of target per LSB)", "label"),
    (r"(buck1|buck2|ldo1|ldo2)_trimmed_sort_V", "Rail output after trim at sort (V); spec ± 0.5 %", "label"),
    (r"(buck1|buck2|ldo1|ldo2)_final_V", "Rail output at final test (V); spec ± 1 %", "label"),
    (r"ovp_untrim_V|uvlo_untrim_V", "Threshold before trim (V)", "feature"),
    (r"ovp_trim_code_opt|uvlo_trim_code_opt", "Optimal 4-bit threshold trim code (0.5 %/LSB)", "label"),
    (r"ovp_trimmed_V|uvlo_trimmed_V", "Threshold after trim (V); OVP 3.63 V, UVLO 2.70 V", "label"),
    (r"ilim_untrim_A", "Current limit before trim (A); target 3.0 A", "feature"),
    (r"ilim_trim_code_opt", "Optimal 5-bit current-limit trim code (1 %/LSB)", "label"),
    (r"ilim_trimmed_A", "Current limit after trim (A)", "label"),
    (r"cs_meas_0p5A_A|cs_meas_2p0A_A", "Current-sense reading at 0.5 A / 2.0 A forced load (A)", "feature"),
    (r"cs_gain_err_true_pct", "True current-sense gain error from full sweep (%)", "label"),
    (r"cs_offset_true_mA", "True current-sense offset (mA)", "label"),
    (r"cs_inl_true_pct", "True current-sense nonlinearity (%)", "label"),
    (r"efficiency_1A_pct", "Buck efficiency at 1 A (%)", "feature"),
    (r"load_reg_mV", "Load regulation (mV)", "feature"),
    (r"sequence", "Power-up sequence (first > last)", "meta"),
    (r"i2c_addr", "I²C address (hex)", "meta"),
    (r"otp_image_hex", "PMIC OTP image: trims, default voltages, sequence, I²C address, customer id", "label"),
    (r"request_id|customer", "OTP configuration request identifiers", "id"),
    (r"buck1_V|buck2_V|ldo1_V|ldo2_V", "Requested default rail voltage (V)", "feature"),
    (r"other_addresses_on_bus", "Other I²C addresses on the customer board", "feature"),
    (r"^label$", "Rule-check outcome: valid, out_of_range, sequence_conflict, invalid_sequence, "
                 "address_collision, address_reserved", "label"),
    (r"full_scale_g", "Accelerometer full-scale range (g)", "meta"),
    (r"nominal_sens_LSB_per_g", "Nominal sensitivity (LSB/g)", "meta"),
    (r"stress_gauge_mV", "On-chip package-stress gauge reading (mV)", "feature"),
    (r"asic_vref_mV", "ASIC reference voltage (mV)", "feature"),
    (r"mems_resonance_kHz", "MEMS resonance frequency (kHz)", "feature"),
    (r"mems_q_factor", "MEMS quality factor", "feature"),
    (r"characterized_3temp", "True for dies with full 3-temperature data (use as training set)", "meta"),
    (r"st_response_[xyz]_mg", "Self-test response (mg)", "feature"),
    (r"offset_[xyz]_25C_mg", "Zero-g offset at 25 C (mg)", "feature"),
    (r"offset_[xyz]_(m40|85)C_mg", "Zero-g offset at -40 C / 85 C (mg)", "label"),
    (r"sens_[xyz]_25C_rel", "Sensitivity at 25 C relative to nominal", "feature"),
    (r"sens_[xyz]_(m40|85)C_rel", "Sensitivity at -40 C / 85 C relative to nominal", "label"),
    (r"tco_[xyz]_true_mg_per_C", "True offset temperature coefficient (mg/°C)", "label"),
    (r"tco2_[xyz]_true_mg_per_C2", "True 2nd-order offset temperature coefficient (mg/°C²)", "label"),
    (r"tcs_[xyz]_true_ppm_per_C", "True sensitivity temperature coefficient (ppm/°C)", "label"),
    (r"post_reflow_offset_shift_[xyz]_mg", "Offset shift after customer solder reflow (mg)", "label"),
    (r"cal_offset_code_[xyz]", "Ideal offset calibration code (0.5 mg/LSB)", "label"),
    (r"cal_tco_code_[xyz]", "Ideal TCO calibration code (0.01 mg/°C per LSB, 8-bit signed)", "label"),
    (r"cal_tcs_code_[xyz]", "Ideal TCS calibration code (5 ppm/°C per LSB, 8-bit signed)", "label"),
    (r"conv_test_insertions", "Temperature insertions in the conventional flow", "meta"),
    (r"conv_test_time_s", "Calibration test time in the conventional flow (s)", "meta"),
    (r"ro_freq_MHz", "Ring-oscillator frequency (MHz)", "feature"),
    (r"cpm_path_delay_ps", "Critical-path monitor delay (ps)", "feature"),
    (r"iddq_25C_mA", "Quiescent leakage current at 25 C (mA)", "feature"),
    (r"core\d_defect", "Core failed structural/functional test (defective)", "label"),
    (r"core\d_fmax_GHz", "Core maximum frequency at 0.85 V (GHz); blank if defective", "label"),
    (r"core\d_vmin_2GHz_mV", "Core minimum voltage at 2.0 GHz (mV); blank if defective", "label"),
    (r"l2_slice\d_fail_bits", "Failing L2 cache bits in slice", "feature"),
    (r"l2_repairable", "All L2 slices repairable", "label"),
    (r"conv_speed_test_time_ms", "Functional speed-binning test time (ms)", "meta"),
    (r"sku_rule_based", "SKU from the rule-based binning flow (Pro / Std / Lite / scrap)", "label"),
    (r"avs_voltage_bin", "AVS voltage bin fused (0.75 V + 12.5 mV x bin); -1 = scrap", "label"),
    (r"avs_voltage_V", "AVS operating voltage (V)", "label"),
    (r"cores_disabled_mask", "Bit mask of cores fused off (harvesting)", "label"),
    (r"power_at_sku_W", "Estimated power at the assigned SKU operating point (W)", "label"),
    (r"array_id", "Memory array identifier", "id"),
    (r"^array$", "Array name", "meta"),
    (r"^rows$|^cols$", "Array size", "meta"),
    (r"spare_rows|spare_cols", "Available redundancy lines", "meta"),
    (r"n_fail_cells", "Number of failing cells", "feature"),
    (r"fail_cells", "Failing cells as row:col pairs separated by ';'", "feature"),
    (r"greedy_repairable", "Repairable with greedy most-fails-first allocation", "label"),
    (r"optimal_repairable", "Repairable with exact allocation", "label"),
    (r"optimal_spare_(rows|cols)_used", "Spare lines used by the exact solution", "label"),
    (r"^sku$|^cores$|fmax_GHz|tdp_W|price_usd|weekly_demand_units",
     "SKU definition, price and weekly demand", "meta"),
    (r"^field$|^lsb$|^nbits$|^description$|^MCU-[ABC]$", "Fuse schema definition", "meta"),
]

FILES = [
    ("mcu_trim_fuse.csv", "MCU wafer sort + final test: bandgap, HSI, LDO and temperature-sensor trims, "
                          "SRAM repair, package drift and fuse maps for 3 derivatives."),
    ("mcu_fuse_schema.csv", "Bit-field definition of the MCU fuse word per derivative."),
    ("mcu_fuse_map_audit.csv", "1,500 fuse words, 25 % with injected errors, for fuse-map validation."),
    ("pmic_trim_otp.csv", "PMIC reference + 4 coupled rails, OVP/UVLO/current-limit trims, current sense, "
                          "efficiency and OTP images for 3 derivatives."),
    ("pmic_otp_config_requests.csv", "400 customer OTP configuration requests with rule-check labels."),
    ("sensor_calibration.csv", "3-axis accelerometer: room-temperature measurements, -40/85 C ground truth, "
                               "temperature coefficients, post-reflow shift and calibration codes."),
    ("soc_binning_harvesting.csv", "SoC monitors, per-core Fmax/Vmin/defects, L2 repair, AVS bin, "
                                   "harvesting mask and rule-based SKU."),
    ("soc_sku_demand.csv", "SKU definitions, prices and weekly demand for die-to-SKU optimization."),
    ("memory_repair_bitmaps.csv", "3,000 L2 fail bitmaps (512 x 512, 4+4 spares) with greedy and exact results."),
]


def describe(col):
    for rx, d, role in PAT:
        if re.fullmatch(rx, col):
            return d, role
    return "", ""


lines = ["# Data dictionary", "",
         "Roles: **feature** = available at test time, **label** = ground truth to predict or check, "
         "**meta** = context, **id** = key.", ""]
missing = []
for f, blurb in FILES:
    df = pd.read_csv(f"{D}/{f}")
    lines += [f"## {f}", "", f"{blurb} {len(df):,} rows × {df.shape[1]} columns.", "",
              "| Column | Role | Description | Example |", "|---|---|---|---|"]
    for c in df.columns:
        d, role = describe(c)
        if not d:
            missing.append(f"{f}:{c}")
        ex = df[c].dropna().iloc[0] if df[c].notna().any() else ""
        ex = str(ex)
        ex = ex[:40] + "…" if len(ex) > 40 else ex
        lines.append(f"| `{c}` | {role} | {d} | {ex} |")
    lines.append("")
open(OUT, "w").write("\n".join(lines))
print("undocumented:", missing or "none")
