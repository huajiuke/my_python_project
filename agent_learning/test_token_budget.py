"""Tests for token budget accounting and layered context assembly."""

import unittest

from agent_learning.token_budget import (
    ContextLayer,
    estimate_message_tokens,
    estimate_tokens,
    is_cjk,
    plan_context,
    split_for_summary,
    truncate_to_tokens,
)


class EstimateTokensTest(unittest.TestCase):
    def test_empty_text_costs_nothing(self) -> None:
        self.assertEqual(estimate_tokens(''), 0)

    def test_cjk_counts_one_token_per_character(self) -> None:
        self.assertEqual(estimate_tokens('你好世界'), 4)

    def test_ascii_counts_four_characters_per_token(self) -> None:
        self.assertEqual(estimate_tokens('abcd'), 1)
        self.assertEqual(estimate_tokens('abcde'), 2)

    def test_mixed_text_adds_both_buckets(self) -> None:
        self.assertEqual(estimate_tokens('你好abcd'), 3)

    def test_estimate_grows_with_longer_prefix(self) -> None:
        text = '上下文工程 abcdefg 摘要'
        self.assertLessEqual(estimate_tokens(text[:5]), estimate_tokens(text))

    def test_is_cjk_recognizes_fullwidth_punctuation(self) -> None:
        self.assertTrue(is_cjk('，'))
        self.assertFalse(is_cjk('a'))


class EstimateMessageTokensTest(unittest.TestCase):
    def test_includes_role_and_overhead(self) -> None:
        messages = [{'role': 'user', 'content': '你好'}]
        # 'user' 1 token + '你好' 2 tokens + 4 tokens overhead
        self.assertEqual(estimate_message_tokens(messages), 7)

    def test_counts_every_message(self) -> None:
        messages = [
            {'role': 'user', 'content': '你好'},
            {'role': 'assistant', 'content': 'abcd'},
        ]
        # 7 + ('assistant' 3 + 'abcd' 1 + overhead 4)
        self.assertEqual(estimate_message_tokens(messages), 15)


class TruncateToTokensTest(unittest.TestCase):
    def test_returns_original_when_within_limit(self) -> None:
        self.assertEqual(truncate_to_tokens('你好', 5), '你好')

    def test_result_never_exceeds_limit(self) -> None:
        text = '上下文工程' * 50
        for limit in (10, 47, 120):
            trimmed = truncate_to_tokens(text, limit)
            self.assertLessEqual(estimate_tokens(trimmed), limit)
            self.assertTrue(trimmed.startswith('上下文工程'))

    def test_appends_marker_when_truncated(self) -> None:
        trimmed = truncate_to_tokens('上下文工程' * 50, 30)
        self.assertIn('...[已截断]', trimmed)

    def test_returns_empty_when_limit_cannot_fit_marker(self) -> None:
        self.assertEqual(truncate_to_tokens('上下文工程' * 50, 2), '')

    def test_rejects_negative_limit(self) -> None:
        with self.assertRaises(ValueError):
            truncate_to_tokens('你好', -1)


class PlanContextTest(unittest.TestCase):
    def test_returns_all_segments_when_budget_is_sufficient(self) -> None:
        layers = [
            ContextLayer(
                name='system', priority=0, segments=('系统提示',), mandatory=True
            ),
            ContextLayer(name='recent', priority=2, segments=('你好', '再见')),
        ]

        plan = plan_context(layers, budget_tokens=100)

        self.assertFalse(plan.report.trimmed)
        self.assertEqual(plan.report.total_tokens, plan.report.requested_tokens)
        self.assertEqual(plan.segments, (('系统提示',), ('你好', '再见')))

    def test_drops_lowest_priority_layer_first(self) -> None:
        layers = [
            ContextLayer(
                name='system', priority=0, segments=('系统提示词',), mandatory=True
            ),
            ContextLayer(name='retrieved', priority=3, segments=('检索片段',)),
            ContextLayer(name='recent', priority=2, segments=('最近对话',)),
        ]

        plan = plan_context(layers, budget_tokens=9)

        by_name = {layer.name: layer for layer in plan.report.layers}
        self.assertEqual(by_name['retrieved'].kept_segments, 0)
        self.assertEqual(by_name['recent'].kept_segments, 1)
        self.assertLessEqual(plan.report.total_tokens, 9)
        self.assertEqual(plan.segments[1], ())

    def test_drop_from_head_keeps_newest_segments(self) -> None:
        layers = [
            ContextLayer(
                name='recent',
                priority=2,
                segments=('旧的一轮', '中间一轮', '新的一轮'),
                drop_from='head',
            )
        ]

        plan = plan_context(layers, budget_tokens=5)

        self.assertEqual(plan.segments[0], ('新的一轮',))

    def test_mandatory_layer_is_never_trimmed_and_overflow_is_reported(self) -> None:
        layers = [
            ContextLayer(
                name='system', priority=0, segments=('很长的系统提示',), mandatory=True
            )
        ]

        plan = plan_context(layers, budget_tokens=3)

        self.assertEqual(plan.segments[0], ('很长的系统提示',))
        self.assertEqual(plan.report.overflow_tokens, 4)

    def test_reserve_output_tokens_shrinks_usable_budget(self) -> None:
        layers = [ContextLayer(name='retrieved', priority=3, segments=('检索片段',))]

        plan = plan_context(layers, budget_tokens=10, reserve_output_tokens=8)

        self.assertEqual(plan.report.usable_tokens, 2)
        self.assertEqual(plan.report.overflow_tokens, 0)
        self.assertEqual(plan.segments[0], ())

    def test_render_joins_kept_segments_and_skips_empty_layers(self) -> None:
        layers = [
            ContextLayer(name='system', priority=0, segments=('系统',), mandatory=True),
            ContextLayer(name='retrieved', priority=9, segments=('片段',)),
        ]

        plan = plan_context(layers, budget_tokens=2)

        self.assertEqual(plan.render(), '系统')

    def test_summary_lists_per_layer_usage(self) -> None:
        layers = [ContextLayer(name='system', priority=0, segments=('系统',))]

        plan = plan_context(layers, budget_tokens=10)

        self.assertIn('system=2/2', plan.report.summary())

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            plan_context([], budget_tokens=0)
        with self.assertRaises(ValueError):
            plan_context([], budget_tokens=10, reserve_output_tokens=20)
        with self.assertRaises(ValueError):
            ContextLayer(name='', priority=0, segments=())
        with self.assertRaises(ValueError):
            ContextLayer(name='recent', priority=0, segments=(), drop_from='middle')
        with self.assertRaises(TypeError):
            ContextLayer(name='recent', priority=0, segments='你好')
        with self.assertRaises(ValueError):
            plan_context(
                [
                    ContextLayer(name='a', priority=0, segments=()),
                    ContextLayer(name='a', priority=1, segments=()),
                ],
                budget_tokens=10,
            )


class SplitForSummaryTest(unittest.TestCase):
    def test_keeps_recent_messages_within_token_budget(self) -> None:
        messages = [
            {'role': 'user', 'content': f'第{index}轮'} for index in range(5)
        ]

        older, recent = split_for_summary(messages, keep_tokens=12)

        self.assertTrue(older)
        self.assertTrue(recent)
        self.assertLessEqual(estimate_message_tokens(recent), 12)
        self.assertEqual(older + recent, messages)

    def test_always_keeps_at_least_one_message(self) -> None:
        messages = [{'role': 'user', 'content': '你好'}]

        older, recent = split_for_summary(messages, keep_tokens=0)

        self.assertEqual(older, [])
        self.assertEqual(recent, messages)

    def test_keeps_everything_when_budget_is_large(self) -> None:
        messages = [{'role': 'user', 'content': '你好'}]

        older, recent = split_for_summary(messages, keep_tokens=1000)

        self.assertEqual(older, [])
        self.assertEqual(len(recent), 1)

    def test_returns_empty_split_for_empty_history(self) -> None:
        self.assertEqual(split_for_summary([], keep_tokens=10), ([], []))

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            split_for_summary([], keep_tokens=-1)
        with self.assertRaises(ValueError):
            split_for_summary([], keep_tokens=10, min_keep=0)


if __name__ == '__main__':
    unittest.main()