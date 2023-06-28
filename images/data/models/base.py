"""
This script and corresponding models are (partially) based on/copied from the fixMatchSeg-Muc repository of
Yasmin Elsharnoby: https://github.com/yasminhossam/fixMatchSeg-Muc
"""

import torch
from torch import nn
from torchvision.models import resnet34, ResNet34_Weights


class ResnetBase(nn.Module):
    """ResNet pretrained on Imagenet. This serves as the
    base for the classifier, and subsequently the segmentation model

    Attributes:
        imagenet_base: boolean, default: True
            Whether or not to load weights pretrained on imagenet
    """

    def __init__(self) -> None:
        super().__init__()
        resnet = resnet34(weights=ResNet34_Weights.DEFAULT).float()
        self.pretrained = nn.Sequential(*list(resnet.children())[:-2])

    def forward(self, x):
        # Since this is just a base, forward() shouldn't directly
        # be called on it.
        raise NotImplementedError
