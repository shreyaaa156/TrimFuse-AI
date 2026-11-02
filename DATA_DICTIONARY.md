# Data dictionary

Roles: **feature** = available at test time, **label** = ground truth to predict or check, **meta** = context, **id** = key.

## mcu_trim_fuse.csv

MCU wafer sort + final test: bandgap, HSI, LDO and temperature-sensor trims, SRAM repair, package drift and fuse maps for 3 derivatives. 8,420 rows × 42 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `die_id` | id | Unique die identifier | MCU-000000 |
| `lot_id` | meta | Fab lot | MA1 |
| `wafer_id` | meta | Wafer (lot-Wnn); use for grouped train/test splits | MA1-W01 |
| `derivative` | meta | Derivative / SKU the die is fused as | MCU-A |
| `die_x` | feature | Die grid index on the wafer | 9 |
| `die_y` | feature | Die grid index on the wafer | 1 |
| `x_mm` | feature | Die centre position from wafer centre (mm) | -24.0 |
| `y_mm` | feature | Die centre position from wafer centre (mm) | -88.0 |
| `radius_mm` | feature | Distance of die centre from wafer centre (mm) | 91.21 |
| `pcm_vth_n_mV` | feature | Process monitor: NMOS threshold voltage (mV) | 452.04 |
| `pcm_vth_p_mV` | feature | Process monitor: PMOS threshold voltage (mV) | -477.49 |
| `pcm_rs_ohm_sq` | feature | Process monitor: poly sheet resistance (ohm/sq) | 284.88 |
| `pcm_tox_A` | feature | Process monitor: gate oxide thickness (Angstrom) | 20.435 |
| `pcm_mobility_rel` | feature | Process monitor: relative carrier mobility | 1.0356 |
| `package` | meta | Package type (drives sort-to-final drift) | QFN48 |
| `temp_grade` | meta | Temperature grade | industrial |
| `latent_defect` | label | Injected latent defect (ground truth for anomaly screening) | False |
| `bg_untrim_V` | feature | Bandgap output before trim, measured at sort (V); target 1.200 V | 1.19017 |
| `bg_trim_code_opt` | label | Optimal 6-bit bandgap trim code (2 mV/LSB, 32 = no change) | 37 |
| `bg_trimmed_sort_V` | label | Bandgap after optimal trim at sort (V) | 1.20051 |
| `bg_conv_iterations` | meta | Iterations used by the conventional binary-search trim | 6 |
| `hsi_untrim_MHz` | feature | HSI oscillator before trim (MHz); target 16 MHz | 16.98648 |
| `hsi_trim_code_opt` | label | Optimal 7-bit HSI trim code (0.2 %/LSB, 64 = no change) | 36 |
| `hsi_trimmed_sort_MHz` | label | HSI after optimal trim at sort (MHz) | 16.04461 |
| `hsi_conv_iterations` | meta | Iterations used by the conventional binary-search trim | 7 |
| `ldo_untrim_V` | feature | LDO output before trim (V); target 1.10 V | 1.09439 |
| `ldo_trim_code_opt` | label | Optimal 5-bit LDO trim code (5 mV/LSB, 16 = no change) | 17 |
| `ldo_trimmed_sort_V` | label | LDO after optimal trim at sort (V) | 1.09872 |
| `ldo_conv_iterations` | meta | Iterations used by the conventional binary-search trim | 7 |
| `ts_cal1_30C_counts` | feature | Temperature sensor reading at 30 C (counts), fused as TS_CAL1 | 1055 |
| `ts_slope_counts_per_C_true` | label | True temperature-sensor slope (counts/°C) | 3.2525 |
| `ts_cal2_110C_counts` | label | Temperature sensor reading at 110 C (counts); label to predict from 30 C data | 1316 |
| `ts_cal2_measured_on_tester` | meta | True where the hot point is actually measured in production (MCU-C) | False |
| `sram_fail_bits` | feature | Failing SRAM bits at sort | 0 |
| `sram_repairable` | label | SRAM repairable with 2 spare rows | True |
| `conv_trim_time_ms` | meta | Trim test time with conventional search (ms) | 28.2 |
| `sort_pass` | label | Die passes wafer sort | True |
| `bg_final_V` | label | Bandgap at final test after packaging (V); spec 1.200 V ± 5 mV | 1.20278 |
| `hsi_final_MHz` | label | HSI at final test (MHz); spec ± 1 % | 15.99442 |
| `ldo_final_V` | label | LDO at final test (V); spec ± 2 % | 1.1005 |
| `final_pass` | label | Die passes final test after packaging | True |
| `fuse_map_hex` | label | 64-bit fuse word (see mcu_fuse_schema.csv) | 0x000002FF507E2925 |

## mcu_fuse_schema.csv

Bit-field definition of the MCU fuse word per derivative. 10 rows × 7 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `field` | meta | Fuse schema definition | BG_TRIM |
| `lsb` | meta | Fuse schema definition | 0 |
| `nbits` | meta | Fuse schema definition | 6 |
| `description` | meta | Fuse schema definition | Bandgap trim code (2 mV/LSB, 32 = no cha… |
| `MCU-A` | meta | Fuse schema definition | per-die |
| `MCU-B` | meta | Fuse schema definition | per-die |
| `MCU-C` | meta | Fuse schema definition | per-die |

## mcu_fuse_map_audit.csv

1,500 fuse words, 25 % with injected errors, for fuse-map validation. 1,500 rows × 5 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `die_id` | id | Unique die identifier | MCU-000691 |
| `derivative` | meta | Derivative / SKU the die is fused as | MCU-A |
| `fuse_map_hex` | label | 64-bit fuse word (see mcu_fuse_schema.csv) | 0x000002FF504A2927 |
| `has_error` | label | Fuse word contains an injected error | False |
| `error_type` | label | Injected error type (none, wrong_flash_size, missing_debug_lock, ...) | none |

## pmic_trim_otp.csv

PMIC reference + 4 coupled rails, OVP/UVLO/current-limit trims, current sense, efficiency and OTP images for 3 derivatives. 11,060 rows × 63 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `die_id` | id | Unique die identifier | PMIC-000000 |
| `lot_id` | meta | Fab lot | PA1 |
| `wafer_id` | meta | Wafer (lot-Wnn); use for grouped train/test splits | PA1-W01 |
| `derivative` | meta | Derivative / SKU the die is fused as | PMIC-P1 |
| `die_x` | feature | Die grid index on the wafer | 12 |
| `die_y` | feature | Die grid index on the wafer | 1 |
| `x_mm` | feature | Die centre position from wafer centre (mm) | -14.0 |
| `y_mm` | feature | Die centre position from wafer centre (mm) | -91.0 |
| `radius_mm` | feature | Distance of die centre from wafer centre (mm) | 92.07 |
| `pcm_vth_n_mV` | feature | Process monitor: NMOS threshold voltage (mV) | 450.41 |
| `pcm_vth_p_mV` | feature | Process monitor: PMOS threshold voltage (mV) | -471.02 |
| `pcm_rs_ohm_sq` | feature | Process monitor: poly sheet resistance (ohm/sq) | 300.45 |
| `pcm_tox_A` | feature | Process monitor: gate oxide thickness (Angstrom) | 20.11 |
| `pcm_mobility_rel` | feature | Process monitor: relative carrier mobility | 1.0212 |
| `package` | meta | Package type (drives sort-to-final drift) | WLCSP |
| `latent_defect` | label | Injected latent defect (ground truth for anomaly screening) | False |
| `vref_untrim_V` | feature | PMIC reference before trim (V); target 0.600 V | 0.59825 |
| `vref_trim_code_opt` | label | Optimal 6-bit reference trim code (0.75 mV/LSB) | 35 |
| `vref_trimmed_sort_V` | feature | Reference after trim at sort (V) | 0.60041 |
| `vref_final_V` | label | Reference at final test (V) | 0.60036 |
| `buck1_target_V` | meta | Default output target for this derivative (V) | 0.8 |
| `buck1_untrim_V` | feature | Rail output before rail trim, after reference trim (V) | 0.80195 |
| `buck1_trim_code_opt` | label | Optimal 6-bit rail trim code (0.2 % of target per LSB) | 31 |
| `buck1_trimmed_sort_V` | label | Rail output after trim at sort (V); spec ± 0.5 % | 0.80016 |
| `buck1_final_V` | label | Rail output at final test (V); spec ± 1 % | 0.80051 |
| `buck2_target_V` | meta | Default output target for this derivative (V) | 1.1 |
| `buck2_untrim_V` | feature | Rail output before rail trim, after reference trim (V) | 1.10064 |
| `buck2_trim_code_opt` | label | Optimal 6-bit rail trim code (0.2 % of target per LSB) | 32 |
| `buck2_trimmed_sort_V` | label | Rail output after trim at sort (V); spec ± 0.5 % | 1.10075 |
| `buck2_final_V` | label | Rail output at final test (V); spec ± 1 % | 1.10216 |
| `ldo1_target_V` | meta | Default output target for this derivative (V) | 1.8 |
| `ldo1_untrim_V` | feature | Rail output before rail trim, after reference trim (V) | 1.79868 |
| `ldo1_trim_code_opt` | label | Optimal 6-bit rail trim code (0.2 % of target per LSB) | 33 |
| `ldo1_trimmed_sort_V` | label | Rail output after trim at sort (V); spec ± 0.5 % | 1.80125 |
| `ldo1_final_V` | label | Rail output at final test (V); spec ± 1 % | 1.80408 |
| `ldo2_target_V` | meta | Default output target for this derivative (V) | 3.3 |
| `ldo2_untrim_V` | feature | Rail output before rail trim, after reference trim (V) | 3.29318 |
| `ldo2_trim_code_opt` | label | Optimal 6-bit rail trim code (0.2 % of target per LSB) | 33 |
| `ldo2_trimmed_sort_V` | label | Rail output after trim at sort (V); spec ± 0.5 % | 3.29744 |
| `ldo2_final_V` | label | Rail output at final test (V); spec ± 1 % | 3.30569 |
| `ovp_untrim_V` | feature | Threshold before trim (V) | 3.6125 |
| `ovp_trim_code_opt` | label | Optimal 4-bit threshold trim code (0.5 %/LSB) | 9 |
| `ovp_trimmed_V` | label | Threshold after trim (V); OVP 3.63 V, UVLO 2.70 V | 3.6306 |
| `uvlo_untrim_V` | feature | Threshold before trim (V) | 2.6932 |
| `uvlo_trim_code_opt` | label | Optimal 4-bit threshold trim code (0.5 %/LSB) | 9 |
| `uvlo_trimmed_V` | label | Threshold after trim (V); OVP 3.63 V, UVLO 2.70 V | 2.7067 |
| `ilim_untrim_A` | feature | Current limit before trim (A); target 3.0 A | 2.9329 |
| `ilim_trim_code_opt` | label | Optimal 5-bit current-limit trim code (1 %/LSB) | 18 |
| `ilim_trimmed_A` | label | Current limit after trim (A) | 2.9916 |
| `cs_meas_0p5A_A` | feature | Current-sense reading at 0.5 A / 2.0 A forced load (A) | 0.50103 |
| `cs_meas_2p0A_A` | feature | Current-sense reading at 0.5 A / 2.0 A forced load (A) | 1.99939 |
| `cs_gain_err_true_pct` | label | True current-sense gain error from full sweep (%) | -0.0918 |
| `cs_offset_true_mA` | label | True current-sense offset (mA) | -1.149 |
| `cs_inl_true_pct` | label | True current-sense nonlinearity (%) | 0.0367 |
| `efficiency_1A_pct` | feature | Buck efficiency at 1 A (%) | 90.958 |
| `load_reg_mV` | feature | Load regulation (mV) | 5.28 |
| `conv_trim_iterations` | meta | Total conventional trim iterations (all trims) | 47 |
| `conv_trim_time_ms` | meta | Trim test time with conventional search (ms) | 37.6 |
| `sort_pass` | label | Die passes wafer sort | True |
| `final_pass` | label | Die passes final test after packaging | True |
| `sequence` | meta | Power-up sequence (first > last) | buck1>buck2>ldo1>ldo2 |
| `i2c_addr` | meta | I²C address (hex) | 0x60 |
| `otp_image_hex` | label | PMIC OTP image: trims, default voltages, sequence, I²C address, customer id | 0x00307274381C104A6618607E3 |

## pmic_otp_config_requests.csv

400 customer OTP configuration requests with rule-check labels. 400 rows × 10 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `request_id` | id | OTP configuration request identifiers | OTPREQ-0000 |
| `customer` | id | OTP configuration request identifiers | CUST-32 |
| `buck1_V` | feature | Requested default rail voltage (V) | 0.762 |
| `buck2_V` | feature | Requested default rail voltage (V) | 1.108 |
| `ldo1_V` | feature | Requested default rail voltage (V) | 3.0 |
| `ldo2_V` | feature | Requested default rail voltage (V) | 3.3 |
| `sequence` | meta | Power-up sequence (first > last) | ldo1>buck1>buck2>ldo2 |
| `i2c_addr` | meta | I²C address (hex) | 0x7F |
| `other_addresses_on_bus` | feature | Other I²C addresses on the customer board | 0x3B;0x5E;0x70 |
| `label` | label | Rule-check outcome: valid, out_of_range, sequence_conflict, invalid_sequence, address_collision, address_reserved | address_reserved |

## sensor_calibration.csv

3-axis accelerometer: room-temperature measurements, -40/85 C ground truth, temperature coefficients, post-reflow shift and calibration codes. 11,060 rows × 67 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `die_id` | id | Unique die identifier | SNS-000000 |
| `lot_id` | meta | Fab lot | SA1 |
| `wafer_id` | meta | Wafer (lot-Wnn); use for grouped train/test splits | SA1-W01 |
| `derivative` | meta | Derivative / SKU the die is fused as | ACC-2G |
| `die_x` | feature | Die grid index on the wafer | 12 |
| `die_y` | feature | Die grid index on the wafer | 1 |
| `x_mm` | feature | Die centre position from wafer centre (mm) | -14.0 |
| `y_mm` | feature | Die centre position from wafer centre (mm) | -91.0 |
| `radius_mm` | feature | Distance of die centre from wafer centre (mm) | 92.07 |
| `pcm_vth_n_mV` | feature | Process monitor: NMOS threshold voltage (mV) | 409.31 |
| `pcm_vth_p_mV` | feature | Process monitor: PMOS threshold voltage (mV) | -458.02 |
| `pcm_rs_ohm_sq` | feature | Process monitor: poly sheet resistance (ohm/sq) | 288.99 |
| `pcm_tox_A` | feature | Process monitor: gate oxide thickness (Angstrom) | 20.434 |
| `pcm_mobility_rel` | feature | Process monitor: relative carrier mobility | 1.0246 |
| `full_scale_g` | meta | Accelerometer full-scale range (g) | 2 |
| `nominal_sens_LSB_per_g` | meta | Nominal sensitivity (LSB/g) | 16384 |
| `package` | meta | Package type (drives sort-to-final drift) | LGA14 |
| `latent_defect` | label | Injected latent defect (ground truth for anomaly screening) | False |
| `stress_gauge_mV` | feature | On-chip package-stress gauge reading (mV) | -0.414 |
| `asic_vref_mV` | feature | ASIC reference voltage (mV) | 1186.181 |
| `mems_resonance_kHz` | feature | MEMS resonance frequency (kHz) | 5.124 |
| `mems_q_factor` | feature | MEMS quality factor | 2.0482 |
| `characterized_3temp` | meta | True for dies with full 3-temperature data (use as training set) | False |
| `st_response_x_mg` | feature | Self-test response (mg) | 492.491 |
| `offset_x_m40C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -36.389 |
| `sens_x_m40C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 0.992587 |
| `offset_x_25C_mg` | feature | Zero-g offset at 25 C (mg) | -28.055 |
| `sens_x_25C_rel` | feature | Sensitivity at 25 C relative to nominal | 0.978392 |
| `offset_x_85C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -16.489 |
| `sens_x_85C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 0.967169 |
| `tco_x_true_mg_per_C` | label | True offset temperature coefficient (mg/°C) | 0.13861 |
| `tco2_x_true_mg_per_C2` | label | True 2nd-order offset temperature coefficient (mg/°C²) | 0.000302 |
| `tcs_x_true_ppm_per_C` | label | True sensitivity temperature coefficient (ppm/°C) | -195.281 |
| `post_reflow_offset_shift_x_mg` | label | Offset shift after customer solder reflow (mg) | 1.03 |
| `cal_offset_code_x` | label | Ideal offset calibration code (0.5 mg/LSB) | 58 |
| `cal_tco_code_x` | label | Ideal TCO calibration code (0.01 mg/°C per LSB, 8-bit signed) | -14 |
| `cal_tcs_code_x` | label | Ideal TCS calibration code (5 ppm/°C per LSB, 8-bit signed) | 39 |
| `st_response_y_mg` | feature | Self-test response (mg) | 496.418 |
| `offset_y_m40C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -33.17 |
| `sens_y_m40C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 1.008096 |
| `offset_y_25C_mg` | feature | Zero-g offset at 25 C (mg) | -25.501 |
| `sens_y_25C_rel` | feature | Sensitivity at 25 C relative to nominal | 0.989546 |
| `offset_y_85C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -21.438 |
| `sens_y_85C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 0.971912 |
| `tco_y_true_mg_per_C` | label | True offset temperature coefficient (mg/°C) | 0.1077 |
| `tco2_y_true_mg_per_C2` | label | True 2nd-order offset temperature coefficient (mg/°C²) | -0.000211 |
| `tcs_y_true_ppm_per_C` | label | True sensitivity temperature coefficient (ppm/°C) | -285.663 |
| `post_reflow_offset_shift_y_mg` | label | Offset shift after customer solder reflow (mg) | 1.667 |
| `cal_offset_code_y` | label | Ideal offset calibration code (0.5 mg/LSB) | 53 |
| `cal_tco_code_y` | label | Ideal TCO calibration code (0.01 mg/°C per LSB, 8-bit signed) | -11 |
| `cal_tcs_code_y` | label | Ideal TCS calibration code (5 ppm/°C per LSB, 8-bit signed) | 57 |
| `st_response_z_mg` | feature | Self-test response (mg) | 486.367 |
| `offset_z_m40C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -41.233 |
| `sens_z_m40C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 0.996447 |
| `offset_z_25C_mg` | feature | Zero-g offset at 25 C (mg) | -31.317 |
| `sens_z_25C_rel` | feature | Sensitivity at 25 C relative to nominal | 0.986123 |
| `offset_z_85C_mg` | label | Zero-g offset at -40 C / 85 C (mg) | -16.016 |
| `sens_z_85C_rel` | label | Sensitivity at -40 C / 85 C relative to nominal | 0.972623 |
| `tco_z_true_mg_per_C` | label | True offset temperature coefficient (mg/°C) | 0.20865 |
| `tco2_z_true_mg_per_C2` | label | True 2nd-order offset temperature coefficient (mg/°C²) | -1.6e-05 |
| `tcs_z_true_ppm_per_C` | label | True sensitivity temperature coefficient (ppm/°C) | -194.09 |
| `post_reflow_offset_shift_z_mg` | label | Offset shift after customer solder reflow (mg) | 1.842 |
| `cal_offset_code_z` | label | Ideal offset calibration code (0.5 mg/LSB) | 60 |
| `cal_tco_code_z` | label | Ideal TCO calibration code (0.01 mg/°C per LSB, 8-bit signed) | -21 |
| `cal_tcs_code_z` | label | Ideal TCS calibration code (5 ppm/°C per LSB, 8-bit signed) | 39 |
| `conv_test_insertions` | meta | Temperature insertions in the conventional flow | 3 |
| `conv_test_time_s` | meta | Calibration test time in the conventional flow (s) | 7.28 |

## soc_binning_harvesting.csv

SoC monitors, per-core Fmax/Vmin/defects, L2 repair, AVS bin, harvesting mask and rule-based SKU. 6,160 rows × 52 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `die_id` | id | Unique die identifier | SOC-000000 |
| `lot_id` | meta | Fab lot | QA1 |
| `wafer_id` | meta | Wafer (lot-Wnn); use for grouped train/test splits | QA1-W01 |
| `derivative` | meta | Derivative / SKU the die is fused as | SoC-Std |
| `die_x` | feature | Die grid index on the wafer | 8 |
| `die_y` | feature | Die grid index on the wafer | 1 |
| `x_mm` | feature | Die centre position from wafer centre (mm) | -35.0 |
| `y_mm` | feature | Die centre position from wafer centre (mm) | -133.0 |
| `radius_mm` | feature | Distance of die centre from wafer centre (mm) | 137.53 |
| `pcm_vth_n_mV` | feature | Process monitor: NMOS threshold voltage (mV) | 454.14 |
| `pcm_vth_p_mV` | feature | Process monitor: PMOS threshold voltage (mV) | -478.86 |
| `pcm_rs_ohm_sq` | feature | Process monitor: poly sheet resistance (ohm/sq) | 337.89 |
| `pcm_tox_A` | feature | Process monitor: gate oxide thickness (Angstrom) | 19.895 |
| `pcm_mobility_rel` | feature | Process monitor: relative carrier mobility | 0.8532 |
| `ro_freq_MHz` | feature | Ring-oscillator frequency (MHz) | 865.77 |
| `cpm_path_delay_ps` | feature | Critical-path monitor delay (ps) | 347.77 |
| `iddq_25C_mA` | feature | Quiescent leakage current at 25 C (mA) | 99.62 |
| `core0_defect` | label | Core failed structural/functional test (defective) | False |
| `core0_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.6958 |
| `core0_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 671.45 |
| `core1_defect` | label | Core failed structural/functional test (defective) | False |
| `core1_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.6816 |
| `core1_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 669.31 |
| `core2_defect` | label | Core failed structural/functional test (defective) | False |
| `core2_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.6922 |
| `core2_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 666.44 |
| `core3_defect` | label | Core failed structural/functional test (defective) | False |
| `core3_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.6921 |
| `core3_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 661.34 |
| `core4_defect` | label | Core failed structural/functional test (defective) | True |
| `core4_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.661 |
| `core4_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 670.5 |
| `core5_defect` | label | Core failed structural/functional test (defective) | False |
| `core5_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.6411 |
| `core5_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 673.15 |
| `core6_defect` | label | Core failed structural/functional test (defective) | False |
| `core6_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.7195 |
| `core6_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 670.41 |
| `core7_defect` | label | Core failed structural/functional test (defective) | False |
| `core7_fmax_GHz` | label | Core maximum frequency at 0.85 V (GHz); blank if defective | 2.7388 |
| `core7_vmin_2GHz_mV` | label | Core minimum voltage at 2.0 GHz (mV); blank if defective | 675.3 |
| `l2_slice0_fail_bits` | feature | Failing L2 cache bits in slice | 1 |
| `l2_slice1_fail_bits` | feature | Failing L2 cache bits in slice | 3 |
| `l2_slice2_fail_bits` | feature | Failing L2 cache bits in slice | 0 |
| `l2_slice3_fail_bits` | feature | Failing L2 cache bits in slice | 1 |
| `l2_repairable` | label | All L2 slices repairable | True |
| `conv_speed_test_time_ms` | meta | Functional speed-binning test time (ms) | 485.3 |
| `sku_rule_based` | label | SKU from the rule-based binning flow (Pro / Std / Lite / scrap) | SoC-Std |
| `avs_voltage_bin` | label | AVS voltage bin fused (0.75 V + 12.5 mV x bin); -1 = scrap | 7 |
| `avs_voltage_V` | label | AVS operating voltage (V) | 0.8375 |
| `cores_disabled_mask` | label | Bit mask of cores fused off (harvesting) | 0x30 |
| `power_at_sku_W` | label | Estimated power at the assigned SKU operating point (W) | 11.225 |

## soc_sku_demand.csv

SKU definitions, prices and weekly demand for die-to-SKU optimization. 3 rows × 6 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `sku` | meta | SKU definition, price and weekly demand | SoC-Pro |
| `cores` | meta | SKU definition, price and weekly demand | 8 |
| `fmax_GHz` | meta | SKU definition, price and weekly demand | 3.0 |
| `tdp_W` | meta | SKU definition, price and weekly demand | 18.0 |
| `price_usd` | meta | SKU definition, price and weekly demand | 145 |
| `weekly_demand_units` | meta | SKU definition, price and weekly demand | 900 |

## memory_repair_bitmaps.csv

3,000 L2 fail bitmaps (512 x 512, 4+4 spares) with greedy and exact results. 3,000 rows × 13 columns.

| Column | Role | Description | Example |
|---|---|---|---|
| `array_id` | id | Memory array identifier | L2ARR-00000 |
| `die_id` | id | Unique die identifier | SOC-005713 |
| `array` | meta | Array name | L2_slice0 |
| `rows` | meta | Array size | 512 |
| `cols` | meta | Array size | 512 |
| `spare_rows` | meta | Available redundancy lines | 4 |
| `spare_cols` | meta | Available redundancy lines | 4 |
| `n_fail_cells` | feature | Number of failing cells | 20 |
| `fail_cells` | feature | Failing cells as row:col pairs separated by ';' | 5:334;31:204;49:173;56:204;74:204;95:204… |
| `greedy_repairable` | label | Repairable with greedy most-fails-first allocation | True |
| `optimal_repairable` | label | Repairable with exact allocation | True |
| `optimal_spare_rows_used` | label | Spare lines used by the exact solution | 5;49;292;468 |
| `optimal_spare_cols_used` | label | Spare lines used by the exact solution | 204 |
