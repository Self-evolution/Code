# Data behind the visual README

All files are documentation snapshots. The original implementation and checkpoints remain distributed separately in `Code.zip`.

## Representative simulation traces

`campe_joint_seed0_trace.csv`, `source_only_joint_seed0_trace.csv` and `ctta_joint_seed0_trace.csv` share the default configuration, frozen checkpoint, seed 0, Joint-shift schedule and Full MPC planner. Their metadata record source hashes and runtime versions. Initial positions match across all three methods. A shared random seed means a matched stochastic setup, not identical realized link quality once robot positions diverge.

The CAMPE snapshot is retained from the preceding README release. Its independent rerun matches all recorded numeric fields exactly; `campe_joint_seed0_rerun_metadata.json` records the verification run. The other two traces were newly recorded. No source policy, checkpoint or benchmark table was edited.

`step=-1` denotes the initial state at t=0. Rows for steps 0–299 are recorded after each transition, at t=(step+1)×0.5 s. Thus each file has 301 rows. Plotting curves includes the initial state; episode means exclude it. Scenario transitions occur at 30, 63 and 99 s; the first post-step record under each new regime is 0.5 s later.

`radius_error` is the mean absolute distance error relative to the desired 18 m ring. `score` is the instantaneous formation score, not the binary capture outcome. `per` is the mean exponential moving estimate of link error, not the aggregate fraction of lost packet attempts. `control_ratio` is a reservation, not the realized control-byte fraction. Status telemetry consumes shared capacity but does not gate local adapter updates.

For the time-resolved heatmap, each signal is independently min–max normalized over the complete 300-step record, without smoothing. Constant rows would map to zero. `heatmap_normalization.json` gives all ranges. Target and mean AUV speeds are finite differences of recorded positions divided by 0.5 s. The rows are diagnostic signals, not an inferred causal graph.

## Released multi-seed benchmark tables

`benchmarks/adaptation_raw.csv` (240 rows), `benchmarks/robustness_raw.csv` (400 rows) and `benchmarks/control_plane_raw.csv` (300 rows) are copied unchanged from the supplied archive. Their SHA-256 hashes match the preceding release's `benchmark_summary.json`.

The histogram uses Source Only, CTTA and CAMPE, each with all 40 structured-shift episodes. It uses fixed 0.25 m bins over 0–4 m; every selected observation is inside the displayed range. Frames add one matched scenario–seed record per method in seed/scenario order. No samples, outliers or failure episodes are discarded.

Success heatmaps use `capture_success_medium`, averaged over exactly ten seeds per method/scenario. The first view includes all six structured-shift methods; the second includes all four methods evaluated on OOD scenarios. The color scale is 0–100% in both views. The two protocols are not pooled.

The AoI chart shows empirical cumulative distributions of the recorded episode-mean `aoi` field for Fixed USV, FIM Only, Dual-Plane and Full MPC, with 50 records per planner. All observations are included, including unsuccessful episodes. Other planners remain available in the complete CSV. The plotted stair steps are empirical CDFs, not fitted curves.

Histogram, CDF and success-matrix animations use presentation progress rather than mission/training time. Only the replay, tracking curves and temporal signal heatmap advance in mission time.

## Scope

No full multi-seed experiment suite was rerun for this visual update. These plots do not replace the statistical uncertainty reporting in the paper. See `visual_provenance_v2.json` for source hashes and `../manifest.json` for the packaged asset inventory.

The earlier numerical discrepancy remains outside these new charts: Table IV reports Full MPC PER as 43.1%, while the supplied coordination CSV averages about 43.67%. The new coordination chart uses the aligned AoI metric; it does not silently alter PER or the manuscript.
