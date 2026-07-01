"""ROI 分布分桶：固定产品档位。"""

from core.modules.strategy.engines.simulator.price_factor.session_roi_stats import (
    ROI_BUCKET_COUNT,
    _fixed_roi_bins,
    collect_roi_percents_from_stock_summaries,
    roi_distribution_session_fields,
)


def test_fixed_bucket_labels_and_count():
    labels, counts = _fixed_roi_bins([])
    assert len(labels) == ROI_BUCKET_COUNT == 13
    assert labels[0] == "[-100%, -50%)"
    assert labels[5] == "[-5%, 0%)"
    assert labels[6] == "[0%, 5%)"
    assert labels[-1] == ">100%"
    assert sum(counts) == 0


def test_fixed_bucket_assignment():
    rois = [-120.0, -60.0, -8.0, -0.1, 0.0, 3.0, 7.0, 15.0, 25.0, 40.0, 80.0, 150.0]
    labels, counts = _fixed_roi_bins(rois)
    assert sum(counts) == len(rois)
    by_label = dict(zip(labels, counts))
    assert by_label["[-100%, -50%)"] == 2
    assert by_label["[-10%, -5%)"] == 1
    assert by_label["[-5%, 0%)"] == 1
    assert by_label["[0%, 5%)"] == 2
    assert by_label["[5%, 10%)"] == 1
    assert by_label["[10%, 20%)"] == 1
    assert by_label["[20%, 30%)"] == 1
    assert by_label["[30%, 50%)"] == 1
    assert by_label["[50%, 100%)"] == 1
    assert by_label[">100%"] == 1


def test_distribution_fields_shape():
    fields = roi_distribution_session_fields([10.0, -5.0, 0.0, 20.0], truncated_exit_count=0)
    assert len(fields["roi_percentile_values"]) == 9
    assert len(fields["roi_bucket_labels"]) == ROI_BUCKET_COUNT
    assert len(fields["roi_bucket_labels"]) == len(fields["roi_bucket_counts"])
    assert fields["roi_bucket_bin_count"] == ROI_BUCKET_COUNT
    assert fields["roi_distribution_sample_count"] == 4
    assert fields["roi_truncated_exit_count"] == 0


def test_excludes_forced_exit():
    summaries = [
        {
            "investments": [
                {
                    "roi": 0.2,
                    "lifecycle": "complete",
                    "completed_targets": [{"name": "win20%"}],
                },
                {
                    "roi": -0.03,
                    "lifecycle": "complete",
                    "completed_targets": [{"name": "enumeration_end"}],
                },
                {
                    "roi": -0.2,
                    "lifecycle": "complete",
                    "completed_targets": [{"name": "loss20%"}],
                },
            ]
        }
    ]
    rois, truncated, total = collect_roi_percents_from_stock_summaries(summaries)
    assert total == 3
    assert truncated == 1
    assert rois == [20.0, -20.0]
    fields = roi_distribution_session_fields(rois, truncated_exit_count=truncated)
    assert fields["roi_truncated_exit_count"] == 1
    assert fields["roi_distribution_sample_count"] == 2
    assert sum(fields["roi_bucket_counts"]) == 2
