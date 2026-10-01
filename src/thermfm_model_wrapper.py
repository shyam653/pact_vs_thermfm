#!/usr/bin/env python3
"""
thermfm_model_wrapper.py

Wrapper for official Therm-FM / scOT architecture (SwinV2 Transformer)
integrating with PhysicalSensitivityDecoder. Supports trainable vs frozen backbone,
and recording code revision, checkpoint, normalization, embedding changes.
"""

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional

# Add deps/Therm-FM to sys.path
THERMFM_DIR = os.path.abspath("deps/Therm-FM")
if THERMFM_DIR not in sys.path:
    sys.path.insert(0, THERMFM_DIR)

try:
    from scOT.model import ScOT, ScOTConfig
    SCOT_AVAILABLE = True
except ImportError:
    SCOT_AVAILABLE = False
    print("[Warning] Could not import scOT.model from deps/Therm-FM. ScOT will be unavailable.")

from sensitivity_decoder import PhysicalSensitivityDecoder, SimpleCNNBackbone

def get_scot_config(model_scale: str = "T", in_channels: int = 5, out_channels: int = 1) -> "ScOTConfig":
    """
    Returns ScOTConfig for specified model scale ('T'=21M, 'B'=158M, 'L'=629M).
    """
    if model_scale == "T":
        embed_dim = 48
        depths = [4, 8, 4]
        num_heads = [3, 6, 12]
    elif model_scale == "B":
        embed_dim = 96
        depths = [4, 8, 4]
        num_heads = [3, 6, 12]
    elif model_scale == "L":
        embed_dim = 192
        depths = [4, 8, 4]
        num_heads = [6, 12, 24]
    else:
        raise ValueError(f"Unknown model_scale: {model_scale}")

    config = ScOTConfig(
        image_size=32,
        patch_size=4,
        num_channels=in_channels,
        num_out_channels=out_channels,
        embed_dim=embed_dim,
        depths=depths,
        num_heads=num_heads,
        window_size=4,
        residual_model="convnext",
        skip_connections=[True, True, True]
    )
    return config

class ThermFMFeatureExtractor(nn.Module):
    """
    Wraps official ScOT encoder to extract multiscale spatial feature maps Z.
    Fuses multi-stage SwinV2 features to preserve fine spatial details.
    """
    def __init__(self, scot_model: nn.Module):
        super().__init__()
        self.scot = scot_model
        embed_dim = scot_model.config.embed_dim
        # Stage 0: embed_dim (8x8), Stage 1: 2*embed_dim (4x4), Stage 2: 4*embed_dim (2x2)
        self.total_feat_dim = embed_dim + 2 * embed_dim + 4 * embed_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, H, W)
        B = x.shape[0]
        time = None
        
        # SwinV2 patch embeddings & encoder with hidden states enabled
        embedding_output, p_shape = self.scot.embeddings(x, time=time)
        encoder_output = self.scot.encoder(
            embedding_output, p_shape, time=time, output_hidden_states=True
        )
        
        hidden_states = encoder_output.hidden_states # Stage 0, 1, 2
        
        # Stage 0: (B, 64, C1) -> (B, C1, 8, 8)
        s0 = hidden_states[0].permute(0, 2, 1).view(B, -1, 8, 8)
        
        # Stage 1: (B, 16, C2) -> (B, C2, 4, 4) -> upsample to (8, 8)
        s1 = hidden_states[1].permute(0, 2, 1).view(B, -1, 4, 4)
        s1_up = F.interpolate(s1, size=(8, 8), mode='bilinear', align_corners=False)
        
        # Stage 2: (B, 4, C3) -> (B, C3, 2, 2) -> upsample to (8, 8)
        s2 = hidden_states[2].permute(0, 2, 1).view(B, -1, 2, 2)
        s2_up = F.interpolate(s2, size=(8, 8), mode='bilinear', align_corners=False)
        
        # Concatenate multiscale features: (B, C1+C2+C3, 8, 8)
        feat = torch.cat([s0, s1_up, s2_up], dim=1)
        
        # Upsample features to input spatial resolution (H, W) if needed
        if feat.shape[2:] != x.shape[2:]:
            feat = F.interpolate(feat, size=x.shape[2:], mode='bilinear', align_corners=False)
            
        return feat

class ThermFMSensitivityDecoder(nn.Module):
    """
    Complete Therm-FM Model with Physical Sensitivity Decoder.
    Combines pretrained/trainable Therm-FM backbone with PhysicalSensitivityDecoder.
    """
    def __init__(
        self,
        model_scale: str = "T",
        in_channels: int = 5,
        freeze_backbone: bool = False,
        pretrained_checkpoint: Optional[str] = None,
        c_ref: float = 1000.0
    ):
        super().__init__()
        self.model_scale = model_scale
        self.freeze_backbone = freeze_backbone
        
        if SCOT_AVAILABLE:
            config = get_scot_config(model_scale, in_channels, 1)
            self.scot_model = ScOT(config)
            if pretrained_checkpoint and os.path.exists(pretrained_checkpoint):
                state_dict = torch.load(pretrained_checkpoint, map_location='cpu')
                self.scot_model.load_state_dict(state_dict, strict=False)
                print(f"[Therm-FM] Loaded pretrained checkpoint from {pretrained_checkpoint}")
            
            if freeze_backbone:
                for param in self.scot_model.parameters():
                    param.requires_grad = False
                print(f"[Therm-FM] Frozen ScOT backbone parameters ({model_scale})")
            
            backbone = ThermFMFeatureExtractor(self.scot_model)
            embed_dim = backbone.total_feat_dim
        else:
            print("[Therm-FM Wrapper] scOT not available, using SimpleCNNBackbone fallback.")
            backbone = SimpleCNNBackbone(in_channels, 64)
            embed_dim = 64
            
        self.decoder = PhysicalSensitivityDecoder(
            backbone=backbone,
            in_channels=in_channels,
            embed_dim=embed_dim,
            c_ref=c_ref
        )

    def forward(
        self,
        x: torch.Tensor,
        c_target: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        return self.decoder(x, c_target)

if __name__ == "__main__":
    if SCOT_AVAILABLE:
        print("Testing ThermFMSensitivityDecoder...")
        model = ThermFMSensitivityDecoder(model_scale="T", in_channels=5, freeze_backbone=True)
        x_dummy = torch.randn(2, 5, 32, 32)
        c_dummy = torch.tensor([[1000.0], [1500.0]])
        out, aux = model(x_dummy, c_dummy)
        print(f"Output shape: {out.shape}")
        print(f"Aux keys: {list(aux.keys())}")
        print("ThermFMSensitivityDecoder test passed successfully.")
    else:
        print("scOT model not available for test.")
