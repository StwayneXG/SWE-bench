#!/bin/bash

python -m swebench.harness.run_evaluation \
    --predictions_path all_preds.jsonl \
    --max_workers 1 \
    --instance_ids django__django-12193 \
    --run_id validate-mutation \
    --dataset_name princeton-nlp/SWE-bench_Verified