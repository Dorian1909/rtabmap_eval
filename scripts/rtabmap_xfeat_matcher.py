#! /usr/bin/env python3
"""
XFeat MNN matcher for RTAB-Map's PyMatcher interface.

Matches XFeat descriptors using the same logic as XFeat.match_xfeat():
1. Cosine similarity matrix (descriptors are L2-normalized)
2. Min cosine similarity threshold (0.82)
3. Mutual Nearest Neighbor (MNN) filtering

Reference: /home/dpx/xfeat_compare/xfate_guess_pnp.py → xfeat.match_xfeat()
           accelerated_features/modules/xfeat.py → XFeat.match()

Usage:
  --Vis/CorType 0
  --PyMatcher/Path "<rtabmap>/corelib/src/python/rtabmap_xfeat_matcher.py"
  --PyMatcher/Cuda false
"""

import os
import numpy as np


def init(descriptor_dim, match_threshold, iterations, cuda, model):
    """Initialize (called by RTAB-Map PyMatcher)."""
    pass


def match(keypoints1, keypoints2, scores1, scores2,
          descriptors1, descriptors2, width, height):
    """
    MNN matching on XFeat descriptors (cosine similarity + min threshold).

    Exact same logic as XFeat.match():
      cossim = feats1 @ feats2.T
      match12 = argmax(cossim, dim=1)
      match21 = argmax(cossim.T, dim=0)
      mutual = match21[match12] == idx0
      good = cossim_max > min_cossim (0.82)
      return idx0[mutual & good], idx1[mutual & good]

    Args:
        keypoints1: Nx2 float32 (x, y)
        keypoints2: Mx2 float32 (x, y)
        scores1: N float32
        scores2: M float32
        descriptors1: Nx64 float32 (L2-normalized)
        descriptors2: Mx64 float32 (L2-normalized)
        width, height: image size

    Returns:
        Kx2 int32 array of match indices (idx1, idx2)
    """
    desc1 = np.asarray(descriptors1, dtype=np.float32)
    desc2 = np.asarray(descriptors2, dtype=np.float32)

    N, M = desc1.shape[0], desc2.shape[0]
    if N == 0 or M == 0:
        return np.zeros((0, 2), dtype=np.int32)

    # Cosine similarity (descriptors already L2-normalized)
    # Same as XFeat.match(): cossim = feats1 @ feats2.t()
    cossim = desc1 @ desc2.T  # (N, M)
    cossim_t = cossim.T        # (M, N)

    # Forward: for each desc1, find best match in desc2
    # Same as: _, match12 = cossim.max(dim=1)
    match12 = np.argmax(cossim, axis=1)  # (N,)

    # Backward: for each desc2, find best match in desc1
    # Same as: _, match21 = cossim_t.max(dim=1)
    match21 = np.argmax(cossim_t, axis=1)  # (M,)

    # Mutual nearest neighbors
    # Same as: mutual = match21[match12] == idx0
    idx0 = np.arange(N)
    mutual = match21[match12] == idx0

    # Min cosine similarity threshold (from XFeat.match: min_cossim=0.82)
    # Same as: cossim_max, _ = cossim.max(dim=1); good = cossim_max > min_cossim
    cossim_max = np.max(cossim, axis=1)  # (N,)
    good = cossim_max > 0.82

    # Combined filter: mutual AND good
    keep = mutual & good
    idx0_out = idx0[keep]
    idx1_out = match12[keep]

    if len(idx0_out) == 0:
        return np.zeros((0, 2), dtype=np.int32)

    return np.stack([idx0_out, idx1_out], axis=1).astype(np.int32)
