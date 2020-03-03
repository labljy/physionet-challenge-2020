# -*- coding: utf-8 -*-
import json
import math
import os
import random
import re
from multiprocessing import Pool

import torch
import wfdb
from scipy import signal
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset

__all__ = ["PhysioNet2020Dataset"]


class PhysioNet2020Dataset(Dataset):
    """PhysioNet 2020 Challenge Dataset.
    """

    BASE_FS = 500
    LABELS = ("AF", "I-AVB", "LBBB", "Normal", "PAC", "PVC", "RBBB", "STD", "STE")
    SEX = ("Male", "Female")

    def __init__(
        self,
        data_dir,
        fs=BASE_FS,
        max_seq_len=None,
        ensure_equal_len=False,
        proc=None,
        records=None,
    ):
        """Initialize the PhysioNet 2020 Challenge Dataset
        data_dir: path to *.mat and *.hea files
        fs: Sampling frequency to return tensors as (default: 500 samples per second)
        max_seq_len: Maximum length of returned tensors (default: full signal length)
        ensure_equal_len: if True, set all signal lengths equal to ensure_equal_len
        proc: Number of processes for generating dataset length references (0: single threaded)
        records: only use provided record names (default: use all available records)
        """
        super(PhysioNet2020Dataset, self).__init__()

        if proc is None:
            try:
                proc = len(os.sched_getaffinity(0))
            except Exception:
                proc = 0

        self.data_dir = data_dir
        self.fs = fs
        self.max_seq_len = max_seq_len
        self.proc = proc
        self.ensure_equal_len = ensure_equal_len

        if ensure_equal_len:
            assert (
                self.max_seq_len is not None
            ), "Cannot ensure equal lengths on unbounded sequences"

        self.record_len_fs = {}  # length and fs of each record (sample size)
        self.record_samps = {}  # number of max_seq_len segments per record
        self.idx_to_key_rel = {}  # dataset index to record key

        record_names = []
        for f in os.listdir(self.data_dir):
            if (
                os.path.isfile(os.path.join(self.data_dir, f))
                and not f.lower().startswith(".")
                and f.lower().endswith(".hea")
            ):
                r_name = f[:-4]  # trim off .hea
                if records is not None and r_name not in records:
                    continue
                else:
                    record_names.append(r_name)
        self.record_names = tuple(sorted(record_names))

        self.initialize_length_references()

    def __len__(self):
        return sum(self.record_samps.values())

    def initialize_length_references(self):
        # construt the dataset length references
        if self.proc <= 0:
            self.record_len_fs = dict(
                PhysioNet2020Dataset._get_sig_len_fs(
                    os.path.join(self.data_dir, rn)
                )
                for rn in self.record_names
            )
        else:
            with Pool(self.proc) as p:
                self.record_len_fs = dict(
                    p.imap_unordered(
                        PhysioNet2020Dataset._get_sig_len_fs,
                        [os.path.join(self.data_dir, rn) for rn in self.record_names],
                    )
                )

        # store the lengths and sample counts for each of the records
        for rn in self.record_names:
            len_rn, fs_rn = self.record_len_fs[rn]
            if self.fs != fs_rn:
                len_resamp = int(len_rn / fs_rn * self.fs)
                self.record_len_fs[rn] = (len_resamp, self.fs)

            if self.max_seq_len is None:
                r_num_samples = 1
            else:
                r_num_samples = math.ceil(self.record_len_fs[rn][0] / self.max_seq_len)
            r_start_idx = sum(self.record_samps.values())
            r_end_idx = r_start_idx + max(r_num_samples, 0)
            for idx in range(r_start_idx, r_end_idx):
                self.idx_to_key_rel[idx] = (rn, idx - r_start_idx)
            self.record_samps[rn] = r_num_samples

    def __getitem__(self, idx):
        rn, rel_idx = self.idx_to_key_rel[idx]
        r = wfdb.rdrecord(os.path.join(self.data_dir, rn))
        raw_age, raw_sx, raw_dx, _rx, _hx, _sx = r.comments

        # resample the signal if necessary
        sig = r.p_signal  # shape SIGNAL, CHANNEL (e.g. 7500, 12)
        if self.fs != r.fs:
            sig = signal.resample(sig, self.record_len_fs[r_pth][0])

        # offset by the relative index if necessary
        if self.max_seq_len is None:
            start_idx = 0
            end_idx = len(sig)
        else:
            start_idx = self.max_seq_len * rel_idx
            end_idx = min(len(sig), start_idx + self.max_seq_len)

        # force shape matches ensure_equal_len if necessary
        if self.ensure_equal_len:
            # start to end must equal max_seq_len
            sig = torch.FloatTensor(sig[end_idx - self.max_seq_len : end_idx])
            if len(sig) < self.max_seq_len:
                pad = self.max_seq_len - len(sig)
                sig = torch.nn.functional.pad(sig, (0, 0, pad, 0), "constant", 0)
        else:
            sig = torch.FloatTensor(sig[start_idx:end_idx])

        dx_grp = re.search(r"^Dx: (?P<dx>.*)$", raw_dx)
        target = [0.0] * len(PhysioNet2020Dataset.LABELS)
        for dxi in dx_grp.group("dx").split(","):
            target[PhysioNet2020Dataset.LABELS.index(dxi)] = 1.0
        target = torch.FloatTensor(target)

        age_grp = re.search(r"^Age: (?P<age>.*)$", raw_age)
        age = float(age_grp.group("age"))
        if math.isnan(age):
            age = -1
        age = torch.ByteTensor((age,))

        sx_grp = re.search(r"^Sex: (?P<sx>.*)$", raw_sx)
        sex = [0.0, 0.0]
        sex[PhysioNet2020Dataset.SEX.index(sx_grp.group("sx"))] = 1.0
        sex = torch.ByteTensor(sex)

        return {
            "signal": sig,
            "target": target,
            "sex": sex,
            "age": age,
            "len": (len(sig),),
        }

    @staticmethod
    def split_names(data_dir, train_ratio):
        """Split all of the record names up into bins based on ratios
        """
        record_names = [f[:-4] for f in os.listdir(data_dir) if (
            os.path.isfile(os.path.join(data_dir, f))
            and not f.lower().startswith(".")
            and f.lower().endswith(".hea")
        )]

        total_records_len = len(record_names)
        train_records_len = int(total_records_len * train_ratio)
        val_records_len = total_records_len - train_records_len

        train_records = tuple(random.sample(record_names, train_records_len))
        val_records = tuple(t for t in record_names if t not in train_records)

        return train_records, val_records

    @staticmethod
    def _get_sig_len_fs(rn):
        r = wfdb.rdrecord(rn)
        return r.record_name, (r.sig_len, r.fs)

    @staticmethod
    def collate_fn(batch, pad=0):
        age = torch.stack(tuple(e["age"] for e in batch))
        sex = torch.stack(tuple(e["sex"] for e in batch))
        target = torch.stack(tuple(e["target"] for e in batch))
        signals = tuple(e["signal"] for e in batch)
        signal_lens = tuple(len(e) for e in signals)
        sig = pad_sequence(signals, padding_value=pad)

        return {
            "signal": sig,
            "target": target,
            "sex": sex,
            "age": age,
            "len": signal_lens,
        }