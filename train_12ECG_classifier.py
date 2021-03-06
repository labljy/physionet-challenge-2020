import csv
import json
import multiprocessing
import os
import queue
import subprocess
import warnings
from datetime import datetime, timedelta
from glob import glob
from time import time

import joblib
import numpy as np
import pandas as pd
import psutil

# import wfdb
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from xgboost import XGBClassifier

from driver import load_challenge_data
from neurokit2_parallel import (
    ECG_LEAD_NAMES,
    KEYS_INTERVALRELATED,
    KEYS_TSFRESH,
    wfdb_record_to_feature_dataframe,
)
from util import parse_fc_parameters
from util.elapsed_timer import ElapsedTimer
from util.evaluate_12ECG_score import is_number, load_table
from util.evaluation_helper import evaluate_score_batch
from util.log import configure_logging
from util.raw_to_wfdb import convert_to_wfdb_record


def _get_fieldnames():
    field_names = ["header_file", "age", "sex"]
    for lead_name in ECG_LEAD_NAMES:
        for key in KEYS_INTERVALRELATED:
            field_names.append(f"{lead_name}_{key}")
        for key in KEYS_TSFRESH:
            hb_key = f"hb__{key}"
            field_names.append(f"{lead_name}_{hb_key}")
        for key in KEYS_TSFRESH:
            sig_key = f"sig__{key}"
            field_names.append(f"{lead_name}_{sig_key}")
    return field_names


def feat_extract_process(
    input_queue: multiprocessing.JoinableQueue,
    output_queue: multiprocessing.JoinableQueue,
    fc_parameters: [None, dict],
):
    while True:
        try:
            header_file_path = input_queue.get(True, 1)
            input_queue.task_done()
        except queue.Empty:
            # When the input queue is empty, worker process terminates
            # NOTE: queue.Empty may be raised even in input_queue contains values
            # parent process should respawn new workers in this edge case
            break

        # for some reason, OS FileError (Too many files) is raised...
        # r = wfdb.rdrecord(header_file_path.rsplit(".hea")[0])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            mat_fp = header_file_path.replace(".hea", ".mat")
            data, header_data = load_challenge_data(mat_fp)
            r = convert_to_wfdb_record(data, header_data)

            record_features, dx = wfdb_record_to_feature_dataframe(
                r, fc_parameters=fc_parameters
            )

            # turn dataframe record_features into dict flatten out the values (one key to one row)
            ecg_features = dict(
                (k, v[0]) for (k, v) in record_features.to_dict().items()
            )
            output_queue.put((header_file_path, ecg_features, dx))


def train_12ECG_classifier(
    input_directory,
    output_directory,
    labels_fp="dxs.txt",
    features_fp="features.csv",
    weights_file="evaluation-2020/weights.csv",
    early_stopping_rounds=20,
    experiments_to_run=1,  # 1 for challenge, 100 for paper
    evaluation_size=0,  # 0 for challenge, 0.15 for paper
    limit_features_to=1000,
):
    logger = configure_logging()

    labels_fp = os.path.join(output_directory, labels_fp)
    features_fp = os.path.join(output_directory, features_fp)
    fieldnames = _get_fieldnames()
    fc_parameters = None

    # HARD CODE IN THE IMPORTANCES RANK!
    importance_data = None
    importances_fp = os.path.join("importances_rank.json")
    if os.path.exists(importances_fp):
        logger.info(f"Loading importances from '{importances_fp}'")
        with open(importances_fp) as importancesfile:
            importance_data = json.load(importancesfile)

        # update the fieldnames to be the important features
        logger.info(
            f"Limiting classification to top {limit_features_to} important features!"
        )
        important_fields = importance_data["sorted_keys"][:limit_features_to]
        fc_parameters = parse_fc_parameters(important_fields)
        fieldnames = ["header_file",] + sorted(important_fields)
    else:
        logger.info(
            "No importances_rank.json found, generating full feature set (VERY SLOW)."
        )

    logger.info(f"Loading feature extraction result from '{labels_fp}'...")
    # check how many files have been processed already, allows feature extraction to be resumable
    label_mapped_records = []
    if os.path.isfile(labels_fp):
        with open(labels_fp, mode="r", newline="\n") as labelfile:
            for line in labelfile.readlines():
                header_file_path, _ = json.loads(line)
                label_mapped_records.append(header_file_path)
        logger.info(f"Loaded {len(label_mapped_records)} from prior run.")
    else:
        logger.info("No labels file found.")
        with open(labels_fp, mode="w"):
            # initialize the file
            pass

    logger.info(f"Loading feature extraction result from '{features_fp}'...")
    feature_mapped_records = []
    if os.path.isfile(features_fp):
        # get fieldnames of existing records
        with open(features_fp, "r", newline="\n") as csvfile:
            reader = csv.reader(csvfile)
            fieldnames = next(reader)

        with open(features_fp, "r", newline="\n") as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=fieldnames)
            next(reader)  # ignore header
            with tqdm(reader) as t:
                for row in t:
                    feature_mapped_records.append(row["header_file"])
    else:
        logger.info("No features file found.")

    logger.info(f"Discovering ECG input files in '{input_directory}'...")
    process_header_files = tuple(
        hfp
        for hfp in glob(os.path.join(input_directory, "**/*.hea"), recursive=True)
        if hfp not in label_mapped_records or hfp not in feature_mapped_records
    )

    del label_mapped_records
    del feature_mapped_records

    logger.info(
        "Number of ECG records remain to process: %d", len(process_header_files)
    )

    # Setup & populate input queue, then initialize output queue
    input_queue = multiprocessing.JoinableQueue()
    for header_file in process_header_files:
        input_queue.put_nowait(header_file)
    output_queue = multiprocessing.JoinableQueue()

    # calculate CPUs used for feature extraction
    num_cpus = len(os.sched_getaffinity(0))
    logger.info("Number of available CPUs: %d", num_cpus)

    total_ram_bytes = psutil.virtual_memory().total
    total_ram_GiB = total_ram_bytes / (1024 ** 3)
    ram_bottleneck_cpus = max(int(total_ram_GiB / 2.3), 1)
    logger.info(f"Available virtual memory: {total_ram_GiB} GiB")

    # quick test for GPUs used, allow no GPU classifier training
    try:
        num_gpus = str(subprocess.check_output(["nvidia-smi", "-L"])).count("UUID")
    except Exception:
        num_gpus = 0
    logger.info(f"Detected {num_gpus} gpus.")

    if ram_bottleneck_cpus < num_cpus:
        logger.info(
            f"Each proccess takes ~2.3 GiB, capping to {ram_bottleneck_cpus} processes"
        )
        num_cpus = ram_bottleneck_cpus

    num_feature_extractor_procs = max(num_cpus, 1)
    feature_extractor_procs = []
    killed_extractor_procs = []
    for _ in range(num_feature_extractor_procs):
        p = multiprocessing.Process(
            target=feat_extract_process, args=(input_queue, output_queue, fc_parameters)
        )
        p.start()
        feature_extractor_procs.append(p)

    # main process used for concatenating features
    processed_files_counter = 0
    out_start = datetime.now()
    out_log = None
    avg_records_per_sec = 0

    # initialize the header if the file does not exist
    if not os.path.isfile(features_fp):
        with open(features_fp, "w", newline="\n") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(features_fp, "a", newline="\n") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        with open(labels_fp, "a") as labelfile:
            while True:
                try:
                    header_file_path, f_dict, dxs = output_queue.get(True, 0.1)
                    labelfile.write(json.dumps((header_file_path, dxs)) + "\n")
                    labelfile.flush()
                    f_dict["header_file"] = header_file_path
                    writer.writerow(f_dict)
                    output_queue.task_done()
                    processed_files_counter += 1
                except queue.Empty:
                    # When the output queue is empty and all workers are terminated
                    # all files have been processed

                    if input_queue.empty() and all(
                        not p.is_alive() for p in feature_extractor_procs
                    ):
                        # input queue is empty and all children processes have exited
                        break

                    elif not input_queue.empty():
                        # input queue is not empty, restart stopped workers
                        num_feature_extractor_procs = len(feature_extractor_procs)
                        for fe_proc_idx in range(num_feature_extractor_procs):
                            p = feature_extractor_procs[fe_proc_idx]
                            if p in killed_extractor_procs:
                                continue
                            if not p.is_alive():
                                disp_str = (
                                    f"{p.pid} (exitcode: {p.exitcode}) is not alive "
                                    f"while input queue contains {input_queue.qsize()} tasks! "
                                    "Restarting..."
                                )
                                logger.info(disp_str)
                                p.join()
                                killed_extractor_procs.append(p)
                                p_new = multiprocessing.Process(
                                    target=feat_extract_process,
                                    args=(input_queue, output_queue),
                                )
                                p_new.start()
                                feature_extractor_procs.append(p_new)

                finally:
                    out_cur = datetime.now()
                    if out_log is None or out_cur - out_log > timedelta(seconds=5):
                        start_delta = out_cur - out_start

                        remaining_time, avg_records_per_sec = _eta_calculate(
                            start_delta,
                            processed_files_counter,
                            len(process_header_files),
                            avg_records_per_sec,
                        )

                        logger.info(
                            f"Processed {processed_files_counter}/{len(process_header_files)} in {start_delta} (est {remaining_time} remain)"
                        )
                        out_log = out_cur

    out_cur = datetime.now()
    start_delta = out_cur - out_start
    logger.info(
        f"Finished processing {processed_files_counter}/{len(process_header_files)} in {start_delta}"
    )

    # Close the queues
    input_queue.close()
    input_queue.join_thread()
    output_queue.close()
    output_queue.join_thread()

    # print(input_queue.qsize(), output_queue.qsize(), processed_files_counter)

    # load the data
    logger.info(f"Loading record label mapping from '{labels_fp}'")
    mapped_records = {}
    with open(labels_fp, mode="r", newline="\n") as labelfile:
        for line in labelfile.readlines():
            header_file_path, dxs = json.loads(line)
            mapped_records[header_file_path] = dxs

    logger.info(f"Loading features_df from '{features_fp}'")
    features_df = pd.read_csv(
        features_fp, header=0, names=fieldnames, index_col="header_file"
    )
    logger.info("Constructing labels array...")
    labels = [mapped_records[row[0]] for row in features_df.itertuples()]

    # logger.info("Dropping 'header_file' column from features_df")
    # features_df.reset_index(drop=True, inplace=True) # is necessary?

    # Load the SNOMED CT code mapping table
    with open("data/snomed_ct_dx_map.json", "r") as f:
        SNOMED_CODE_MAP = json.load(f)

    logger.info("Loading scoring function weights")
    rows, cols, all_weights = load_table(weights_file)
    assert rows == cols, "rows and cols mismatch"
    scored_codes = rows

    for experiment_num in range(experiments_to_run):
        with ElapsedTimer() as timer:
            logger.info(f"Running experiment #{experiment_num}")

            logger.info(
                f"Splitting data into training and evaluation split ({evaluation_size})"
            )
            if evaluation_size > 0:
                (
                    train_features,
                    eval_features,
                    train_labels,
                    eval_labels,
                ) = train_test_split(features_df, labels, test_size=evaluation_size)
            else:
                train_features = features_df
                train_labels = labels
                eval_features = pd.DataFrame({})
                eval_labels = []

            logger.info(f"Training dataset shape: {train_features.shape}")
            logger.info(f"Evaluation dataset shape: {eval_features.shape}")

            to_save_data = {
                "train_records": train_features.index.to_list(),
                "eval_records": eval_features.index.to_list(),
                "field_names": features_df.columns.to_list(),
            }

            for idx_sc, sc in enumerate(scored_codes):
                _abbrv, dx = SNOMED_CODE_MAP[str(sc)]
                logger.info(f"Training classifier for {dx} (code {sc})...")

                sc, model = _train_label_classifier(
                    sc,
                    idx_sc,
                    all_weights,
                    train_features,
                    train_labels,
                    eval_features,
                    eval_labels,
                    scored_codes,
                    early_stopping_rounds,
                    num_gpus,
                )

                to_save_data[sc] = model

            if eval_labels:
                _display_metrics(logger, eval_features, eval_labels, to_save_data)
            else:
                logger.info("Metrics calculated on training data, no evaluation set!")
                _display_metrics(logger, train_features, train_labels, to_save_data)
            _save_experiment(logger, output_directory, to_save_data)

        logger.info(f"Experiment {experiment_num} took {timer.duration:.2f} seconds")


def _eta_calculate(
    start_delta,
    processed_files_counter,
    number_of_files_to_process,
    avg_records_per_sec,
):
    elapsed_sec = start_delta.total_seconds()
    if processed_files_counter <= 0:
        # cannot calculate ETA if no files have been processed yet
        return float("nan"), 0

    new_avg_records_per_sec = processed_files_counter / elapsed_sec

    # average the two new averages
    avg_records_per_sec = (avg_records_per_sec + new_avg_records_per_sec) / 2
    num_remaining_records = number_of_files_to_process - processed_files_counter
    remaining_seconds_estimate = int(num_remaining_records / avg_records_per_sec)

    return timedelta(seconds=remaining_seconds_estimate), avg_records_per_sec


def _train_label_classifier(
    sc,
    idx_sc,
    all_weights,
    train_features,
    train_labels,
    eval_features,
    eval_labels,
    scored_codes,
    early_stopping_rounds,
    num_gpus,
):
    label_weights = all_weights[idx_sc]
    train_labels, train_weights = _determine_sample_weights(
        train_labels, scored_codes, label_weights
    )

    if eval_labels:
        eval_labels, eval_weights = _determine_sample_weights(
            eval_labels, scored_codes, label_weights
        )

    # try negative over positive https://machinelearningmastery.com/xgboost-for-imbalanced-classification/
    pos_count = len([e for e in train_labels if e])
    pos_count = max(pos_count, 1)
    scale_pos_weight = (len(train_labels) - pos_count) / pos_count

    tree_method = "auto"
    sampling_method = "uniform"
    if num_gpus > 0:
        tree_method = "gpu_hist"
        sampling_method = "gradient_based"

    model = XGBClassifier(
        booster="dart",  # gbtree, dart or gblinear
        verbosity=0,
        tree_method=tree_method,
        sampling_method=sampling_method,
        scale_pos_weight=scale_pos_weight,
    )

    eval_set = [
        (train_features, train_labels),
    ]
    sample_weight_eval_set = [
        train_weights,
    ]
    if eval_labels:
        eval_set.append((eval_features, eval_labels))
        sample_weight_eval_set.append(eval_weights)

    model = model.fit(
        train_features,
        train_labels,
        sample_weight=train_weights,
        eval_set=eval_set,
        sample_weight_eval_set=sample_weight_eval_set,
        early_stopping_rounds=early_stopping_rounds,
        verbose=False,
    )

    return sc, model


def _determine_sample_weights(
    data_set, scored_codes, label_weights, weight_threshold=0.5
):
    """Using the scoring labels weights to increase the dataset size of positive labels
    """
    data_labels = []
    sample_weights = []
    for dt in data_set:
        sample_weight = None
        for dx in dt:
            if str(dx) in scored_codes:
                _sample_weight = label_weights[scored_codes.index(str(dx))]
                if _sample_weight < weight_threshold:
                    continue
                if sample_weight is None or _sample_weight > sample_weight:
                    sample_weight = _sample_weight

        if sample_weight is None:
            # not a scored label, treat as a negative example (weight of 1)
            sample_weight = 1.0
            data_labels.append(False)
        else:
            data_labels.append(True)
        sample_weights.append(sample_weight)
    return data_labels, sample_weights


def _display_metrics(logger, features_df, ground_truth, to_save_data):
    classes = []
    labels = []
    scores = []

    for k, v in to_save_data.items():
        if not is_number(k):
            continue

        classes.append(str(k))
        labels.append(v.predict(features_df).tolist())
        scores.append(v.predict_proba(features_df)[:, 1].tolist())

    labels = np.array(labels).T
    scores = np.array(scores).T

    raw_ground_truth_labels = []
    for dx in ground_truth:
        raw_ground_truth_labels.append([str(dv) for dv in dx])

    (
        auroc,
        auprc,
        accuracy,
        f_measure,
        f_beta_measure,
        g_beta_measure,
        challenge_metric,
    ) = evaluate_score_batch(
        predicted_classes=classes,
        predicted_labels=labels,
        predicted_probabilities=scores,
        raw_ground_truth_labels=raw_ground_truth_labels,
    )

    logger.info(
        "AUROC | AUPRC | Accuracy | F-measure | Fbeta-measure | Gbeta-measure | Challenge metric"
    )
    logger.info(
        f"{auroc:>5.3f} | {auprc:>5.3f} | {accuracy:>8.3f} | {f_measure:>9.3f} |"
        f" {f_beta_measure:>13.3f} | {g_beta_measure:>13.3f} | {challenge_metric:>16.3f}"
    )

    to_save_data["auroc"] = auroc
    to_save_data["auprc"] = auprc
    to_save_data["accuracy"] = accuracy
    to_save_data["f_measure"] = f_measure
    to_save_data["f_beta_measure"] = f_beta_measure
    to_save_data["g_beta_measure"] = g_beta_measure
    to_save_data["challenge_metric"] = challenge_metric


def _save_experiment(logger, output_directory, to_save_data):
    logger.info("Saving model...")

    cur_sec = int(time())
    filename = os.path.join(output_directory, f"finalized_model_{cur_sec}.sav")
    joblib.dump(to_save_data, filename, protocol=0)

    logger.info(f"Saved to {filename}")
