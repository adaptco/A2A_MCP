from __future__ import annotations

import unittest

from app import server


class PortalAssetResolutionTests(unittest.TestCase):
    def test_root_path_resolves_to_portal_entrypoint(self) -> None:
        asset = server.resolve_portal_asset("/")
        self.assertIsNotNone(asset)
        self.assertEqual(asset, server.PORTAL_ENTRYPOINT)
        self.assertTrue(asset.is_file())

    def test_directory_path_maps_to_index_html(self) -> None:
        asset = server.resolve_portal_asset("/hud/capsules/avatar")
        self.assertIsNotNone(asset)
        self.assertEqual(asset, server.PORTAL_ENTRYPOINT)

    def test_manifest_asset_is_served_from_public_directory(self) -> None:
        asset = server.resolve_portal_asset("/data/avatar_bindings.v1.json")
        self.assertIsNotNone(asset)
        self.assertTrue(asset.name.endswith("avatar_bindings.v1.json"))
        self.assertTrue(str(asset).endswith("public/data/avatar_bindings.v1.json"))
        self.assertTrue(asset.is_file())

    def test_path_traversal_attempt_is_blocked(self) -> None:
        asset = server.resolve_portal_asset("/../specs/branch-merge-model.v1.json")
        self.assertIsNone(asset)


if __name__ == "__main__":
    unittest.main()
