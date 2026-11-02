# Synthetic dataset: AI-optimized trim & fuse for derivative chips

A synthetic, reproducible dataset for developing and testing the solution described in *AI-Optimized Trim & Fuse for Derivative Chips*. It covers all four chip types (MCU, PMIC, sensor and SoC), with three derivatives each, plus fuse-map, OTP-configuration, memory-repair and SKU-demand tables.

All data is synthetic. No real product, fab or customer data was used.

## Contents

| File | Rows | Use case |
|---|---|---|
| `data/mcu_trim_fuse.csv` | 8,420 | Predictive trim (bandgap, HSI, LDO), temperature-sensor hot-point prediction, drift-aware targets, transfer learning, fuse maps |
| `data/mcu_fuse_schema.csv` | 10 | Fuse-word bit fields per derivative |
| `data/mcu_fuse_map_audit.csv` | 1,500 | Fuse-map validation; 25 % carry injected errors |
| `data/pmic_trim_otp.csv` | 11,060 | Coupled multi-rail trim, threshold trims, current-sense calibration, OTP images |
| `data/pmic_otp_config_requests.csv` | 400 | Customer OTP configuration rule checking |
| `data/sensor_calibration.csv` | 11,060 | Multi-temperature calibration from one insertion, post-reflow drift |
| `data/soc_binning_harvesting.csv` | 6,160 | Vmin/Fmax prediction, AVS bins, harvesting, SKU assignment |
| `data/soc_sku_demand.csv` | 3 | Prices and demand for die-to-SKU optimization |
| `data/memory_repair_bitmaps.csv` | 3,000 | Redundancy allocation (greedy vs exact) |
| `DATA_DICTIONARY.md` | — | Every column, its role (feature / label / meta) and units |
| `generate_synthetic_data.py` | — | Regenerates the data (`--seed` for a different draw) |
| `baseline_models.py` | — | Baseline models proving each use case; output in `baseline_results.txt` |

## Derivative structure

Each chip type has an imbalanced set of derivatives, so transfer learning can be tested:

| Chip type | Base derivative (most data) | Smaller derivatives |
|---|---|---|
| MCU | MCU-A, QFN48, 512 KB (15 wafers) | MCU-B, QFN32, 256 KB (3 wafers) · MCU-C, LQFP100, automotive (2 wafers) |
| PMIC | PMIC-P1, WLCSP (15 wafers) | PMIC-P2, QFN24 (3 wafers) · PMIC-C7, customer variant (2 wafers) |
| Sensor | ACC-2G (15 wafers) | ACC-8G (3 wafers) · ACC-16G, LGA12 (2 wafers) |
| SoC | One die, 20 wafers | Fused into SoC-Pro / SoC-Std / SoC-Lite by binning |

## How the data is generated

- **Process variation:** each die gets five process parameters built from lot offset, wafer offset, radial bowl, wafer tilt and die-random terms. PCM columns report them with measurement noise.
- **Trim DACs:** every trim has finite bits, LSB, per-die gain error and INL. The `*_trim_code_opt` labels come from an exhaustive search, so they are the true best codes.
- **Coupling:** PMIC rails share the trimmed reference, and the MCU HSI and LDO track the trimmed bandgap.
- **Drift:** sort-to-final shift depends on package and on package stress, which grows with wafer radius. MCU-C (LQFP100) shifts the most, giving a clear drift-aware-target case.
- **Defects:** 0.3–0.5 % latent defects are injected (`latent_defect`). SoC core defects and memory fails rise toward the wafer edge.
- **Conventional baseline:** iteration counts and test times for binary-search trim and 3-insertion calibration are included for savings calculations.

## Baseline results

From `baseline_models.py` (gradient-boosted trees, wafer-grouped splits):

| Use case | Result |
|---|---|
| MCU bandgap predictive trim | 98 % within ±1 code; 6.6 → 1.35 iterations |
| MCU LDO predictive trim | 99.9 % within ±1 code; 5.6 → 1.1 iterations |
| MCU HSI predictive trim | 80 % within ±1 code; 7.6 → 2.7 iterations (hardest trim) |
| MCU-C drift transfer (50 dies) | Shift error 1.73 → 0.86 mV; final bandgap pass 90.9 % → 99.4 % |
| PMIC rail codes from reference only | 83–91 % within ±1 code without measuring the rails |
| Sensor TCO / TCS from 25 °C data | R² 0.84 / 0.94; 85 °C offset error 12.8 → 6.5 mg RMS |
| SoC slowest-core Fmax from monitors | R² 0.97 |
| Fuse-map validation | 406 / 406 injected errors caught, 0 false alarms |
| Memory repair | Exact solver repairs 17 arrays greedy allocation misses |

## Suggested splits

- **Group by `wafer_id`** for every train/test split. Dies on the same wafer are correlated.
- **Transfer learning:** train on the base derivative, fine-tune on a few dies of the small derivative, test on the rest.
- **Sensor:** train on `characterized_3temp == True` (20 %), predict for the other 80 %.
- **MCU temperature sensor:** only MCU-C measures the hot point in production (`ts_cal2_measured_on_tester`). Train there and predict for MCU-A/B.

## Regenerate

```bash
pip install numpy pandas scikit-learn
python generate_synthetic_data.py data --seed 2026
python baseline_models.py data
python make_data_dictionary.py data DATA_DICTIONARY.md
```

## Limitations

Relationships are simplified and synthetic. Use this dataset to build and test pipelines, models and tools, then retrain and validate on real STDF/PCM data before any production use. Never blow fuses on predictions validated only on synthetic data.
