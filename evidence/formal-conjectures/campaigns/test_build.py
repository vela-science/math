#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from unittest import TestCase, main, mock


SPEC = importlib.util.spec_from_file_location("campaign_build", Path(__file__).with_name("build.py"))
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class CampaignTests(TestCase):
    def test_frozen_record_preserves_domain_and_actor_truth(self):
        campaign, raw = BUILD.build()
        self.assertEqual(raw, BUILD.OUTPUT_PATH.read_bytes())
        self.assertEqual(campaign["authority_effect"], "none")
        self.assertEqual(campaign["state"], "closed_with_contract_gap")
        self.assertEqual(campaign["work_offer"]["presence"], "superseded")
        self.assertEqual(campaign["outcomes"]["process"]["completion_contract"], "not_satisfied")
        self.assertEqual(campaign["decision_domains"]["scientific"]["status"], "accepted")
        self.assertEqual(campaign["decision_domains"]["program"]["status"], "not_applicable")
        self.assertEqual(campaign["decision_domains"]["deployment"]["status"], "not_applicable")
        review = campaign["mechanism"]["review_requirements"]
        self.assertEqual(review["eligible_performer_classes"], ["agent", "human"])
        self.assertFalse(review["quality_rank_from_performer_class"])

    def test_no_resource_or_successor_authority_is_invented(self):
        campaign, _ = BUILD.build()
        self.assertEqual(campaign["resources"]["reward_commitment"], "none")
        self.assertEqual(campaign["resources"]["allocations"], [])
        self.assertEqual(campaign["remap"]["state"], "offered")
        self.assertEqual(campaign["remap"]["work_offer"]["presence"], "open")
        self.assertEqual(campaign["remap"]["next_obligation"]["authority_effect"], "none")
        self.assertIn("no payment", " ".join(campaign["nonclaims"]))

    def test_open_reissue_and_contract_rewrite_are_refused(self):
        original = BUILD._load
        index, raw = original(BUILD.INDEX_PATH)
        changed = copy.deepcopy(index)
        changed["targets"][0]["presence"] = "open"
        with mock.patch.object(BUILD, "_load", side_effect=lambda path: (changed, raw) if path == BUILD.INDEX_PATH else original(path)):
            with self.assertRaisesRegex(BUILD.CampaignError, "terminal Work Offer"):
                BUILD.build()

        lifecycle, raw = original(BUILD.LIFECYCLE_PATH)
        changed = copy.deepcopy(lifecycle)
        changed["completion"]["contract_status"] = "satisfied"
        with mock.patch.object(BUILD, "_load", side_effect=lambda path: (changed, raw) if path == BUILD.LIFECYCLE_PATH else original(path)):
            with self.assertRaisesRegex(BUILD.CampaignError, "Contract gap"):
                BUILD.build()


if __name__ == "__main__":
    main()
