"""End-to-end tests use real torch.export graphs and the actual Lab5 simulator."""
import argparse
import json
import sys
import unittest
from pathlib import Path

import torch

LAB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB_DIR))
from frontend import analyze_exported, export_model
from model import MatmulModel
from run import compile_and_run, make_inputs, run_tool

parser = argparse.ArgumentParser()
parser.add_argument("--backend-dir", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
options, remaining = parser.parse_known_args()


class FrontendTests(unittest.TestCase):
    def test_export_matches_model_and_metadata(self):
        a, b = make_inputs()
        program, spec = export_model(MatmulModel(), a, b)
        self.assertEqual((spec.m, spec.n, spec.k), (5, 6, 7))
        torch.testing.assert_close(program.module()(a, b), a @ b)
        self.assertEqual(spec.manifest()["output_initialization"], "zero-before-each-call")

    def test_reject_unsupported_models(self):
        class Add(torch.nn.Module):
            def forward(self, a, b):
                return a + b

        class Relu(torch.nn.Module):
            def forward(self, a, b):
                return (a @ b).relu()

        class Swap(torch.nn.Module):
            def forward(self, a, b):
                return b @ a

        class ExtraOutput(torch.nn.Module):
            def forward(self, a, b):
                return a @ b, a

        class State(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.register_buffer("weight", torch.eye(2))

            def forward(self, a, b):
                return a @ self.weight

        for model in (Add(), Relu(), Swap(), ExtraOutput(), State()):
            with self.subTest(model=type(model).__name__), self.assertRaises(ValueError):
                export_model(model, torch.eye(2), torch.eye(2))

    def test_reject_bad_tensors(self):
        a, b = make_inputs()
        cases = [(a.double(), b.double()), (a.half(), b.half()),
                 (torch.ones(2, 2, 2), torch.ones(2, 2, 2)),
                 (torch.ones(2, 3), torch.ones(4, 2)),
                 (torch.ones(0, 3), torch.ones(3, 2)),
                 (torch.ones(3, 2).t(), torch.ones(3, 2)),
                 (torch.full((2, 3), float("nan")), torch.ones(3, 2)),
                 (torch.full((2, 3), float("inf")), torch.ones(3, 2))]
        for left, right in cases:
            with self.subTest(shape=left.shape, dtype=left.dtype), self.assertRaises(ValueError):
                export_model(MatmulModel(), left, right)

    def test_reject_dynamic_shapes(self):
        a, b = make_inputs()
        dynamic = torch.export.Dim("rows", min=2, max=16)
        program = torch.export.export(MatmulModel(), (a, b), dynamic_shapes=({0: dynamic}, None))
        with self.assertRaisesRegex(ValueError, "dynamic shapes"):
            analyze_exported(program)


class ExecutionTests(unittest.TestCase):
    def compile(self, a, b, label, mode="fp32", **kwargs):
        destination = options.output_dir / label
        report = compile_and_run(a, b, options.backend_dir, destination, mode=mode, **kwargs)
        self.assertTrue(report["passed"])
        self.assertEqual(report["output_initialization"], "zero-before-each-call")
        tensors = json.loads((destination / "tensors.json").read_text())
        self.assertTrue(all(x == 0 for x in tensors["initial_c"]))
        restored = torch.export.load(destination / "model.pt2")
        analyze_exported(restored)
        torch.testing.assert_close(restored.module()(a, b), a @ b)
        return report, tensors

    def test_fp32_and_int8_shapes_tiles_seeds(self):
        # Remainders on all axes, one element, rectangular and divisible cases.
        cases = [(1, 1, 1, 1), (2, 4, 3, 2), (5, 6, 7, 4), (8, 4, 8, 8)]
        for mode in ("fp32", "int8"):
            for seed in (0, 42):
                for m, n, k, tile in cases:
                    with self.subTest(mode=mode, m=m, n=n, k=k, tile=tile, seed=seed):
                        a, b = make_inputs(m, n, k, seed)
                        report, _ = self.compile(a, b, f"{mode}-{m}-{n}-{k}-{seed}", mode,
                                                 tile_size=tile)
                        if mode == "int8":
                            self.assertTrue(report["integer_reference_exact"])

    def test_known_answer(self):
        data = json.loads((LAB_DIR / "examples/inputs.json").read_text())
        a, b = (torch.tensor(data[key], dtype=torch.float32) for key in ("a", "b"))
        _, tensors = self.compile(a, b, "known")
        self.assertEqual(tensors["output"], [[58.0, 64.0], [139.0, 154.0]])

    def test_zero_inputs_and_identity(self):
        for mode in ("fp32", "int8"):
            _, tensors = self.compile(torch.zeros(2, 3), torch.ones(3, 4), f"zero-{mode}", mode)
            self.assertEqual(tensors["output"], [[0.0] * 4] * 2)
        a = torch.tensor([[-1.0, 2.0], [0.0, -4.0]])
        _, tensors = self.compile(a, torch.eye(2), "identity")
        self.assertEqual(tensors["output"], a.tolist())

    def test_stage_options_equal_combined_pipeline(self):
        a, b = make_inputs()
        self.compile(a, b, "pipeline", tile_size=2, sram_bytes=512)
        folder = options.output_dir / "pipeline"
        combined = run_tool([options.backend_dir / "npu-opt",
                             "--npu-compile=tile-size=2 sram-bytes=512", "--verify-each"],
                            (folder / "01-linalg.mlir").read_text())
        self.assertEqual(combined, (folder / "05-planned.mlir").read_text())

    def test_int8_pipeline_preserves_scales(self):
        a, b = make_inputs()
        report, _ = self.compile(a, b, "int8-pipeline", "int8", tile_size=2)
        folder = options.output_dir / "int8-pipeline"
        scales = report["quantization"]
        pipeline = ("--npu-compile=quantize-int8=true tile-size=2 "
                    f"a-scale={scales['a_scale']:.17g} b-scale={scales['b_scale']:.17g}")
        combined = run_tool([options.backend_dir / "npu-opt", pipeline, "--verify-each"],
                            (folder / "01-linalg.mlir").read_text())
        self.assertEqual(combined, (folder / "05-planned.mlir").read_text())

    def test_reject_small_sram_and_bad_options(self):
        a, b = make_inputs()
        with self.assertRaisesRegex(RuntimeError, "exceeds SRAM"):
            compile_and_run(a, b, options.backend_dir, options.output_dir / "small-sram",
                            sram_bytes=64)
        for kwargs in (dict(tile_size=0), dict(tile_size=65), dict(sram_bytes=0), dict(mode="fp16")):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                compile_and_run(a, b, options.backend_dir, options.output_dir / "bad", **kwargs)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
