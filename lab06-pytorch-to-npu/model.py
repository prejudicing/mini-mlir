"""The complete model supported by this lab: two inputs, one matrix product."""
import torch


# 唯一支持的模型语义：两个输入、一个直接矩阵乘输出，不包含权重或 Bias。
class MatmulModel(torch.nn.Module):
    def forward(self, a, b):
        return a @ b
