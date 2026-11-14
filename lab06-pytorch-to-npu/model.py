"""The complete model supported by this lab: two inputs, one matrix product."""
import torch


class MatmulModel(torch.nn.Module):
    def forward(self, a, b):
        return a @ b
