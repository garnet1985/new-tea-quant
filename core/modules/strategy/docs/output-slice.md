# Output Slice API

`StrategyOutputReaderService.load_opportunity_snapshot(...)` provides a lightweight time-slice read API over enumerator artifacts.

## Method

`load_opportunity_snapshot(output_version_dir, *, start_date, end_date, stock_ids=None, include_targets=True)`

## Inputs

- `output_version_dir`: enumerator version directory (`.../results/opportunity_enums/{test|output}/{version}`)
- `start_date`, `end_date`: inclusive `YYYYMMDD` range
- `stock_ids` (optional): restrict to specific stocks
- `include_targets`: include target rows grouped by `opportunity_id`

## Output Shape

- `opportunities`: list of opportunity rows (sorted by `trigger_date`, `stock_id`, `opportunity_id`)
- `targets_map`: mapping `{ opportunity_id: [target_rows...] }` when `include_targets=True`; empty object otherwise

## Notes

- This API is read-only and does not trigger enumeration.
- It is intended for both backend orchestration and UI snapshot loading.
- Range filtering is applied to opportunities by `trigger_date`, and targets by `date/target_date`.
