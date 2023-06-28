"""
This script and corresponding models are (partially) based on/copied from the fixMatchSeg-Muc repository of
Yasmin Elsharnoby: https://github.com/yasminhossam/fixMatchSeg-Muc
"""

import torch
from torch import nn

from .base import ResnetBase


class Classifier(ResnetBase):
    """A ResNet34 Model

    Attributes:
        imagenet_base: boolean, default: True
            Whether or not to load weights pretrained on imagenet
    """

    def __init__(self) -> None:
        super().__init__()

        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.classifier = nn.Sequential(
            nn.Linear(512, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.pretrained(x)
        x = self.avgpool(x)
        return self.classifier(x.view(x.size(0), -1))
