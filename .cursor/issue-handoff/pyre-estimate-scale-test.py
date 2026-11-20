"""Registration > Estimate Scale sets only the rigid transform's scale, and Ctrl+Z undoes it (James, 2026-11-20)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import nornir_imageregistration
import numpy as np

import pyre.common
from pyre.commands.transform_undo import save_rigid_undo
from pyre.state.managers.command_history import CommandHistory


def _similarity() -> nornir_imageregistration.transforms.CenteredSimilarity2DTransform:
    return nornir_imageregistration.transforms.CenteredSimilarity2DTransform(
        target_offset=(40.0, -25.0), source_rotation_center=(100.0, 150.0),
        angle=np.radians(12.0), scalar=1.0, flip_ud=False)


class TestApplyRigidScale(unittest.TestCase):

    def test_only_the_scale_changes_and_the_pivot_stays_put(self) -> None:
        transform = _similarity()
        pivot = np.array([[100.0, 150.0]])
        pivot_target = transform.Transform(pivot)
        angle = transform.angle

        pyre.common.apply_rigid_scale(transform, 1.05)

        self.assertAlmostEqual(1.05, transform.scalar, places=6)
        self.assertAlmostEqual(angle, transform.angle, places=6)
        np.testing.assert_allclose(pivot_target, transform.Transform(pivot), atol=1e-3)
        # A point 100 px from the pivot now lands 105 px from it.
        other = np.array([[200.0, 150.0]])
        self.assertAlmostEqual(105.0, float(np.linalg.norm(transform.Transform(other) - pivot_target)),
                               places=2)

    def test_ctrl_z_restores_the_previous_scale(self) -> None:
        transform = _similarity()
        controller = SimpleNamespace(TransformModel=transform)
        history = CommandHistory()
        before = transform.GetRigidState()
        mapped_before = transform.Transform(np.array([[10.0, 20.0]]))

        pyre.common.apply_rigid_scale(transform, 0.93)
        save_rigid_undo(history, controller, before)
        history.Undo()

        self.assertAlmostEqual(1.0, transform.scalar, places=6)
        np.testing.assert_allclose(mapped_before, transform.Transform(np.array([[10.0, 20.0]])), atol=1e-3)

    def test_a_non_rigid_transform_is_refused(self) -> None:
        with self.assertRaises(TypeError):
            pyre.common.apply_rigid_scale(mock.Mock(spec=[]), 1.1)


class TestEstimateRigidScale(unittest.TestCase):

    def test_it_returns_the_refined_scale_only(self) -> None:
        refined = _similarity()
        refined._scalar = 1.07
        with mock.patch.object(pyre.common, 'RefineRigidTransformLocal', return_value=refined) as refine:
            scale = pyre.common.EstimateRigidScale(_similarity(), source_image_key='S', target_image_key='T')
        self.assertAlmostEqual(1.07, scale)
        self.assertFalse(refine.call_args.kwargs['search_angle'])

    def test_missing_images_give_none(self) -> None:
        with mock.patch.object(pyre.common, 'RefineRigidTransformLocal', return_value=None):
            self.assertIsNone(pyre.common.EstimateRigidScale(_similarity()))


if __name__ == '__main__':
    unittest.main()
